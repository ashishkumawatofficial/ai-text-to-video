"""RunPod Serverless Client and High-Throughput Parallel Dispatcher.

Enables concurrent execution of video diffusion workflows across independent on-demand
serverless GPU workers, with automatic output normalization (URLs vs base64) and instant cancellation.
"""

from __future__ import annotations

import os
import time
import base64
import signal
import asyncio
import logging


from typing import Dict, Any, List, Optional, Callable, Union
import requests

from core.config import (
    get_runpod_api_key,
    get_runpod_serverless_endpoint_id,
    get_max_serverless_concurrency,
    get_comfy_timeout_sec,
)
from core.models import (
    ServerlessConfig,
    ServerlessJob,
    ServerlessJobStatus,
    ServerlessCostReport,
    SceneBeat,
    StoryboardBeat,
    Wan3WorkflowConfig,
    ASPECT_RATIO_RESOLUTIONS,
    VideoAspectRatio,
)

logger = logging.getLogger(__name__)


class RunPodServerlessError(RuntimeError):
    """Base exception for RunPod Serverless operations."""
    pass


def calculate_safe_video_frames(duration_sec: float, fps: float = 16.0) -> int:
    """Calculates frame count satisfying Wan 2.1's 4k + 1 rule (17, 33, 49, 65, 81 frames).
    
    17 frames = 1.06s
    33 frames = 2.06s
    49 frames = 3.06s
    65 frames = 4.06s
    81 frames = 5.06s
    """
    ideal_frames = int(round(duration_sec * fps))
    valid_counts = [17, 33, 49, 65, 81]
    for count in valid_counts:
        if count >= ideal_frames:
            return count
    return 81


def ensure_video_duration_coverage(video_path: str, target_duration_sec: float, output_path: Optional[str] = None) -> str:
    """If video duration is shorter than target dialogue duration by >0.4s, extends the motion via ffmpeg PTS scaling."""
    if not video_path or not os.path.exists(video_path):
        return video_path
    import subprocess
    import re
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
        actual_dur = float(res.stdout.strip()) if res.stdout.strip() else 0.0
        if actual_dur > 0 and (target_duration_sec - actual_dur) > 0.4:
            dest = output_path or re.sub(r'(_extended)*\.mp4$', '_extended.mp4', video_path)
            scale_factor = target_duration_sec / actual_dur
            cmd_scale = [
                "ffmpeg", "-y", "-i", video_path,
                "-filter:v", f"setpts={scale_factor}*PTS",
                "-an", dest
            ]
            subprocess.run(cmd_scale, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                return dest
    except Exception as e:
        logger.warning(f"Could not extend video duration: {e}")
    return video_path


def create_looping_preview_clip(image_path: str, output_path: str, duration_sec: float = 5.0) -> str:
    """Generates an MP4 looping preview clip from a static keyframe image."""
    import subprocess
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-c:v", "libx264",
        "-t", str(duration_sec),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_path



class RunPodServerlessClient:
    """Client for RunPod Serverless API v2."""

    BASE_URL = "https://api.runpod.ai/v2"

    def __init__(
        self,
        endpoint_id: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[ServerlessConfig] = None,
    ):
        self.api_key = api_key or get_runpod_api_key() or ""
        self.endpoint_id = endpoint_id or get_runpod_serverless_endpoint_id() or ""
        self.timeout_sec = get_comfy_timeout_sec()
        self.max_concurrency = get_max_serverless_concurrency()
        self.gpu_rate_per_sec = 0.00021  # Default RTX 4090 ($0.75/hr)

        if config:
            self.endpoint_id = config.endpoint_id
            self.api_key = config.api_key
            self.timeout_sec = config.timeout_sec
            self.max_concurrency = config.max_concurrency
            self.gpu_rate_per_sec = config.gpu_tier_rate_per_sec

        self._active_jobs: List[str] = []

    def is_available(self) -> bool:
        """Checks if serverless credentials and endpoint are configured."""
        return bool(self.api_key and self.endpoint_id)

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @property
    def endpoint_url(self) -> str:
        return f"{self.BASE_URL}/{self.endpoint_id}"

    def check_health(self) -> Dict[str, Any]:
        """Checks the operational status and worker availability of this endpoint."""
        from dataclasses import asdict
        report = check_serverless_health(self.endpoint_id, self.api_key)
        return asdict(report)

    def run_job(self, workflow: Dict[str, Any], images: Optional[List[Dict[str, str]]] = None) -> str:
        """Asynchronously submits a ComfyUI workflow to the serverless worker queue."""
        if not self.is_available():
            raise RunPodServerlessError("RunPod Serverless not configured. Missing API key or Endpoint ID.")

        payload = {
            "input": {
                "workflow": workflow,
                "images": images or [],
            }
        }

        url = f"{self.endpoint_url}/run"
        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=15.0)
        except Exception as e:
            raise RunPodServerlessError(f"Failed to submit serverless job to {url}: {e}")

        if resp.status_code not in (200, 201):
            raise RunPodServerlessError(f"Serverless submission failed ({resp.status_code}): {resp.text}")

        data = resp.json()
        job_id = data.get("id")
        if not job_id:
            raise RunPodServerlessError(f"Malformed serverless response (missing job id): {data}")

        self._active_jobs.append(job_id)
        return job_id

    def poll_job(
        self,
        job_id: str,
        timeout_sec: Optional[int] = None,
        poll_interval: float = 2.5,
    ) -> Dict[str, Any]:
        """Polls serverless job status until completed, failed, or timed out."""
        timeout = timeout_sec or self.timeout_sec
        start_time = time.time()
        url = f"{self.endpoint_url}/status/{job_id}"

        while time.time() - start_time < timeout:
            try:
                resp = requests.get(url, headers=self.headers, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status")

                    if status == ServerlessJobStatus.COMPLETED.value:
                        if job_id in self._active_jobs:
                            try:
                                self._active_jobs.remove(job_id)
                            except ValueError:
                                pass
                        return data

                    if status in (
                        ServerlessJobStatus.FAILED.value,
                        ServerlessJobStatus.CANCELLED.value,
                        ServerlessJobStatus.TIMED_OUT.value,
                    ):
                        if job_id in self._active_jobs:
                            try:
                                self._active_jobs.remove(job_id)
                            except ValueError:
                                pass
                        err = data.get("error") or f"Job terminated with status: {status}"
                        raise RunPodServerlessError(f"Serverless job {job_id} {status}: {err}")

            except RunPodServerlessError:
                raise
            except Exception:
                pass

            time.sleep(poll_interval)

        raise TimeoutError(f"Serverless job {job_id} timed out after {timeout}s")

    def cancel_job(self, job_id: str) -> bool:
        """Sends cancellation request for an in-flight serverless job."""
        if not self.is_available():
            return False
        url = f"{self.endpoint_url}/cancel/{job_id}"
        try:
            resp = requests.post(url, headers=self.headers, timeout=5.0)
            if job_id in self._active_jobs:
                try:
                    self._active_jobs.remove(job_id)
                except ValueError:
                    pass
            return resp.status_code in (200, 204)
        except Exception:
            return False

    def cancel_batch(self, job_ids: Optional[List[str]] = None) -> List[str]:
        """Cancels all specified or active in-flight serverless jobs."""
        targets = list(job_ids) if job_ids is not None else list(self._active_jobs)
        cancelled = []
        for jid in targets:
            if self.cancel_job(jid):
                cancelled.append(jid)
        return cancelled

    def parse_and_download_output(self, output_payload: Any, dest_path: str) -> str:
        """Normalizes polymorphic serverless ComfyUI output (URL vs base64) to local file."""
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

        # 1. Direct string (base64 data URI or plain URL)
        if isinstance(output_payload, str):
            if output_payload.startswith("http://") or output_payload.startswith("https://"):
                return self._download_stream(output_payload, dest_path)
            elif "base64," in output_payload:
                b64_data = output_payload.split("base64,")[1]
                return self._write_base64(b64_data, dest_path)
            else:
                return self._write_base64(output_payload, dest_path)

        # 2. Dictionary output structure
        if isinstance(output_payload, dict):
            media_list = (
                output_payload.get("videos")
                or output_payload.get("images")
                or output_payload.get("output", {}).get("videos")
                or output_payload.get("output", {}).get("images")
            )
            if media_list and isinstance(media_list, list) and len(media_list) > 0:
                first_item = media_list[0]
                if isinstance(first_item, dict):
                    if "url" in first_item:
                        return self._download_stream(first_item["url"], dest_path)
                    if "data" in first_item:
                        return self._write_base64(first_item["data"], dest_path)
                elif isinstance(first_item, str):
                    if first_item.startswith("http"):
                        return self._download_stream(first_item, dest_path)
                    return self._write_base64(first_item, dest_path)

            for key in ("message", "result", "video"):
                val = output_payload.get(key)
                if isinstance(val, str):
                    if val.startswith("http"):
                        return self._download_stream(val, dest_path)
                    elif len(val) > 100:
                        return self._write_base64(val, dest_path)

        raise RunPodServerlessError(
            f"Unable to parse video artifact from serverless output. Keys found: "
            f"{list(output_payload.keys()) if isinstance(output_payload, dict) else type(output_payload)}"
        )

    def _download_stream(self, url: str, dest_path: str) -> str:
        resp = requests.get(url, stream=True, timeout=60.0)
        if resp.status_code != 200:
            raise RunPodServerlessError(f"Failed to stream video from {url} ({resp.status_code})")
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=16384):
                f.write(chunk)
        return dest_path

    def _write_base64(self, b64_str: str, dest_path: str) -> str:
        clean_b64 = b64_str.strip()
        if "base64," in clean_b64:
            clean_b64 = clean_b64.split("base64,")[1].strip()
        binary_data = base64.b64decode(clean_b64)
        with open(dest_path, "wb") as f:
            f.write(binary_data)
        return dest_path

    def execute_video_job(
        self,
        workflow: Dict[str, Any],
        dest_path: str,
        timeout_sec: Optional[int] = None,
    ) -> str:
        """Synchronously executes a single workflow on serverless and downloads the video."""
        job_id = self.run_job(workflow)
        poll_res = self.poll_job(job_id, timeout_sec=timeout_sec)
        output_payload = poll_res.get("output")
        if not output_payload:
            raise RunPodServerlessError(f"Serverless job {job_id} succeeded but returned empty output.")
        return self.parse_and_download_output(output_payload, dest_path)

    async def dispatch_parallel_beats(
        self,
        beats: List[Union[SceneBeat, StoryboardBeat]],
        output_dir: str,
        aspect_ratio: str = "16:9",
        progress_cb: Optional[Callable[[int, str, str], None]] = None,
    ) -> ServerlessCostReport:
        """Dispatches all storyboard beats concurrently across independent serverless GPU workers."""
        from core.runpod_client import build_wan3_workflow_payload
        from core.models import ImageRole

        start_time = time.time()
        semaphore = asyncio.Semaphore(self.max_concurrency)
        jobs: List[ServerlessJob] = []

        # Determine dimensions based on aspect ratio
        dim = ASPECT_RATIO_RESOLUTIONS.get(VideoAspectRatio(aspect_ratio), (1920, 1080))
        # Keep diffusion canvas at 832x480 / 480x832 / 640x640 for fast generation
        if dim[0] > dim[1]:
            render_w, render_h = 832, 480
        elif dim[0] < dim[1]:
            render_w, render_h = 480, 832
        else:
            render_w, render_h = 640, 640

        async def _execute_single_beat(idx: int, beat: Union[SceneBeat, StoryboardBeat]) -> str:
            async with semaphore:
                # Support both StoryboardBeat (image_assets) and SceneBeatPlan (keyframe_image_path / start_frame_path)
                image_assets = getattr(beat, "image_assets", None)
                init_image = None
                if image_assets:
                    init_image = next((a.file_path for a in image_assets if getattr(a, "role", None) == ImageRole.START_FRAME), None)
                    if not init_image:
                        init_image = next((a.file_path for a in image_assets if getattr(a, "role", None) == ImageRole.SCENE_IMAGE), None)
                if not init_image:
                    init_image = getattr(beat, "start_frame_path", None) or getattr(beat, "keyframe_image_path", None)

                safe_frames = calculate_safe_video_frames(beat.duration_sec, fps=16.0)
                
                wan_cfg = Wan3WorkflowConfig(
                    prompt=getattr(beat, "motion_prompt", None) or beat.visual_prompt,
                    negative_prompt="blurry, low quality, distorted anatomy, jitter, artifacts, realistic photography, inconsistent clothing, style drift",
                    width=render_w,
                    height=render_h,
                    duration_frames=safe_frames,
                    steps=12,
                    reference_images=[init_image] if init_image else [],
                )
                workflow = build_wan3_workflow_payload(wan_cfg)

                if progress_cb:
                    progress_cb(idx, beat.name, "SUBMITTING")
                
                job_id = await asyncio.to_thread(self.run_job, workflow)
                job_record = ServerlessJob(
                    job_id=job_id,
                    beat_index=idx,
                    beat_name=beat.name,
                    status=ServerlessJobStatus.IN_QUEUE,
                )
                jobs.append(job_record)

                if progress_cb:
                    progress_cb(idx, beat.name, f"IN_QUEUE (ID: {job_id[:8]})")

                dest_file = os.path.join(output_dir, f"serverless_beat_{idx}_{job_id[:8]}.mp4")

                # Poll status
                poll_res = await asyncio.to_thread(self.poll_job, job_id, self.timeout_sec)
                
                job_record.status = ServerlessJobStatus.COMPLETED
                job_record.execution_time_ms = float(poll_res.get("executionTime", 0.0))
                job_record.completed_at = time.time()

                if progress_cb:
                    progress_cb(idx, beat.name, "DOWNLOADING")

                output_path = await asyncio.to_thread(
                    self.parse_and_download_output,
                    poll_res.get("output"),
                    dest_file
                )
                output_path = ensure_video_duration_coverage(output_path, beat.duration_sec)
                job_record.output_video_path = output_path
                beat.output_video_path = output_path

                if progress_cb:
                    progress_cb(idx, beat.name, "COMPLETED")

                return output_path

        # Register SIGINT cancellation hook
        loop = asyncio.get_running_loop()
        def _handle_interrupt():
            print("\n🛑 Interrupt caught! Cancelling in-flight Serverless workers...")
            self.cancel_batch()
        
        try:
            loop.add_signal_handler(signal.SIGINT, _handle_interrupt)
        except (NotImplementedError, RuntimeError):
            # Not in main thread or on Windows
            pass

        try:
            tasks = [_execute_single_beat(i, beat) for i, beat in enumerate(beats)]
            await asyncio.gather(*tasks)
        finally:
            try:
                loop.remove_signal_handler(signal.SIGINT)
            except (NotImplementedError, RuntimeError):
                pass

        wall_clock = time.time() - start_time
        return self.generate_cost_report(jobs, wall_clock)

    def generate_cost_report(
        self,
        jobs: List[ServerlessJob],
        wall_clock_sec: float,
    ) -> ServerlessCostReport:
        """Calculates compute duration and USD billing totals across worker jobs."""
        cumulative_gpu_sec = sum(j.execution_time_ms for j in jobs) / 1000.0
        if cumulative_gpu_sec <= 0.0:
            cumulative_gpu_sec = wall_clock_sec * len(jobs)

        cost_usd = cumulative_gpu_sec * self.gpu_rate_per_sec

        return ServerlessCostReport(
            total_beats=len(jobs),
            successful_beats=sum(1 for j in jobs if j.status == ServerlessJobStatus.COMPLETED),
            wall_clock_duration_sec=round(wall_clock_sec, 2),
            cumulative_gpu_seconds=round(cumulative_gpu_sec, 2),
            estimated_cost_usd=round(cost_usd, 4),
            effective_concurrency=round(cumulative_gpu_sec / max(wall_clock_sec, 1.0), 2),
        )


def format_multi_worker_status(jobs: List[ServerlessJob]) -> str:
    """Formats a compact multi-worker status table for terminal logging."""
    lines = [
        "┌──────┬────────────────────────┬─────────────┬─────────────┐",
        "│ Beat │ Name                   │ Status      │ Time (s)    │",
        "├──────┼────────────────────────┼─────────────┼─────────────┤",
    ]
    for j in jobs:
        b_idx = f"#{j.beat_index + 1}".ljust(4)
        name = (j.beat_name[:22] + "..") if len(j.beat_name) > 22 else j.beat_name.ljust(22)
        status_val = j.status.value if hasattr(j.status, "value") else str(j.status)
        status = status_val[:11].ljust(11)
        dur = f"{round(j.execution_time_ms / 1000.0, 1)}s" if j.execution_time_ms > 0 else "-"
        dur = dur.ljust(11)
        lines.append(f"│ {b_idx} │ {name} │ {status} │ {dur} │")
    lines.append("└──────┴────────────────────────┴─────────────┴─────────────┘")
    return "\n".join(lines)


def format_cost_banner(report: ServerlessCostReport) -> str:
    """Formats a prominent billing transparency banner for CLI output."""
    banner = [
        "╔════════════════════════════════════════════════════════════════════╗",
        "║           ⚡ RUNPOD SERVERLESS COMPUTE & COST SUMMARY ⚡           ║",
        "╠════════════════════════════════════════════════════════════════════╣",
        f"║  • Total Narrative Beats:     {str(report.total_beats).ljust(35)}║",
        f"║  • Successfully Rendered:     {str(report.successful_beats).ljust(35)}║",
        f"║  • Wall-Clock Elapsed Time:   {f'{report.wall_clock_duration_sec}s'.ljust(35)}║",
        f"║  • Total Cumulative GPU Time: {f'{report.cumulative_gpu_seconds}s'.ljust(35)}║",
        f"║  • Effective Parallelism:     {f'{report.effective_concurrency}x concurrent workers'.ljust(35)}║",
        f"║  • Total Generation Cost:     {f'${report.estimated_cost_usd:.4f} USD'.ljust(35)}║",
        "╚════════════════════════════════════════════════════════════════════╝",
    ]
    return "\n".join(banner)


from dataclasses import dataclass

@dataclass
class ServerlessHealthReport:
    endpoint_id: str
    status: str
    workers_idle: int = 0
    workers_running: int = 0
    jobs_in_queue: int = 0
    jobs_in_progress: int = 0
    error: Optional[str] = None


def check_serverless_health(
    endpoint_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> ServerlessHealthReport:
    """Checks the operational status and worker availability of a RunPod Serverless endpoint."""
    ep_id = endpoint_id or get_runpod_serverless_endpoint_id()
    key = api_key or get_runpod_api_key()

    if not ep_id:
        return ServerlessHealthReport(
            endpoint_id="NOT_CONFIGURED",
            status="NOT_CONFIGURED",
            error="RUNPOD_SERVERLESS_ENDPOINT_ID is not configured in .env",
        )

    if not key:
        return ServerlessHealthReport(
            endpoint_id=ep_id,
            status="UNAUTHORIZED",
            error="RUNPOD_API_KEY is not configured in .env",
        )

    url = f"https://api.runpod.ai/v2/{ep_id}/health"
    headers = {"Authorization": f"Bearer {key}"}

    try:
        resp = requests.get(url, headers=headers, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            workers = data.get("workers", {})
            jobs = data.get("jobs", {})
            return ServerlessHealthReport(
                endpoint_id=ep_id,
                status="HEALTHY",
                workers_idle=workers.get("idle", 0),
                workers_running=workers.get("running", 0),
                jobs_in_queue=jobs.get("inQueue", 0),
                jobs_in_progress=jobs.get("inProgress", 0),
            )
        else:
            return ServerlessHealthReport(
                endpoint_id=ep_id,
                status=f"HTTP_{resp.status_code}",
                error=resp.text,
            )
    except Exception as e:
        return ServerlessHealthReport(
            endpoint_id=ep_id,
            status="UNREACHABLE",
            error=str(e),
        )


