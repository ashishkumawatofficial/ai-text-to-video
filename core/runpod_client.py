"""RunPod ComfyUI REST/WebSocket client for remote GPU diffusion inference."""

from __future__ import annotations
import os
import json
import uuid
import time
import requests
from typing import Dict, Any, Optional
from core.models import RunPodHealthReport, Wan3WorkflowConfig
import core.config

DEFAULT_COMFY_URL = os.environ.get("RUNPOD_COMFY_URL", "http://127.0.0.1:8188")


class ComfyUIClient:
    """Client for interacting with ComfyUI running on RunPod or local GPU."""

    def __init__(self, base_url: str = DEFAULT_COMFY_URL):
        raw_urls = [u.strip().rstrip("/") for u in base_url.split(",") if u.strip()]
        self.candidate_urls = raw_urls if raw_urls else ["http://127.0.0.1:8188"]
        self.base_url = self.candidate_urls[0]
        self.client_id = str(uuid.uuid4())

    def is_available(self) -> bool:
        """Checks if any candidate ComfyUI server in the pool is reachable."""
        for url in self.candidate_urls:
            try:
                resp = requests.get(f"{url}/system_stats", timeout=3.0)
                if resp.status_code == 200:
                    self.base_url = url
                    return True
            except Exception:
                continue
        return False

    def queue_prompt(self, workflow_prompt: Dict[str, Any]) -> str:
        """Queues a prompt workflow and returns the prompt_id."""
        payload = {
            "prompt": workflow_prompt,
            "client_id": self.client_id
        }
        resp = requests.post(
            f"{self.base_url}/prompt",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10.0
        )
        if resp.status_code != 200:
            raise RuntimeError(f"ComfyUI queue error ({resp.status_code}): {resp.text}")

        data = resp.json()
        return data.get("prompt_id", "")

    def poll_history(self, prompt_id: str, timeout_sec: int = 900, poll_interval: float = 2.0) -> Dict[str, Any]:
        """Polls execution history until the prompt completes or times out."""
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            try:
                resp = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if prompt_id in data:
                        item = data[prompt_id]
                        status = item.get("status", {})
                        if status.get("completed"):
                            return item
                        if status.get("status_str") == "error":
                            err_msg = "Unknown execution error"
                            for m in status.get("messages", []):
                                if m[0] == "execution_error":
                                    err_msg = m[1].get("exception_message", str(m[1]))
                                    break
                            raise RuntimeError(f"ComfyUI execution failed: {err_msg}")
            except RuntimeError:
                raise
            except Exception:
                pass
            time.sleep(poll_interval)

        raise TimeoutError(f"ComfyUI prompt {prompt_id} timed out after {timeout_sec}s")

    def download_image_or_video(
        self,
        filename: str,
        dest_path: str,
        subfolder: str = "",
        folder_type: str = "output"
    ) -> str:
        """Downloads an output file from ComfyUI to local disk."""
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        resp = requests.get(f"{self.base_url}/view", params=params, stream=True, timeout=30.0)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download {filename} from ComfyUI ({resp.status_code})")

        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return dest_path

    def execute_video_workflow(
        self,
        workflow: Dict[str, Any],
        output_path: str,
        timeout_sec: int = 900
    ) -> str:
        """Executes a video diffusion workflow and saves the resulting MP4."""
        prompt_id = self.queue_prompt(workflow)
        history = self.poll_history(prompt_id, timeout_sec=timeout_sec)
        
        outputs = history.get("outputs", {})
        # Find video output node
        for node_id, node_output in outputs.items():
            if "videos" in node_output:
                video_info = node_output["videos"][0]
                return self.download_image_or_video(
                    filename=video_info["filename"],
                    subfolder=video_info.get("subfolder", ""),
                    folder_type=video_info.get("type", "output"),
                    dest_path=output_path
                )
            if "gifs" in node_output:
                gif_info = node_output["gifs"][0]
                return self.download_image_or_video(
                    filename=gif_info["filename"],
                    subfolder=gif_info.get("subfolder", ""),
                    dest_path=output_path
                )
            if "images" in node_output:
                img_info = node_output["images"][0]
                return self.download_image_or_video(
                    filename=img_info["filename"],
                    subfolder=img_info.get("subfolder", ""),
                    folder_type=img_info.get("type", "output"),
                    dest_path=output_path
                )

        raise RuntimeError(f"No video/gif output found in ComfyUI prompt history: {outputs}")


# --- Feature 002: Wan 3.0 & Endpoint Health Diagnostics ---

WAN3_WORKFLOW_TEMPLATE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "workflows", "wan3_omni_reference.json")
)


def build_wan3_workflow_payload(config: Wan3WorkflowConfig) -> Dict[str, Any]:
    """Populates the Wan 3.0 Omni-Reference ComfyUI workflow JSON with scene parameters."""
    if not os.path.exists(WAN3_WORKFLOW_TEMPLATE):
        raise FileNotFoundError(f"Wan 3.0 workflow template not found at {WAN3_WORKFLOW_TEMPLATE}")

    with open(WAN3_WORKFLOW_TEMPLATE, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    # 1. Inject Prompts
    if "4" in workflow and "inputs" in workflow["4"]:
        workflow["4"]["inputs"]["text"] = config.prompt
    elif "2" in workflow and "inputs" in workflow["2"]:
        workflow["2"]["inputs"]["text"] = config.prompt

    if "5" in workflow and "inputs" in workflow["5"]:
        workflow["5"]["inputs"]["text"] = config.negative_prompt
    elif "3" in workflow and "inputs" in workflow["3"]:
        workflow["3"]["inputs"]["text"] = config.negative_prompt

    # 2. Inject Latent Video Dimensions & Duration (Safe 3D Temporal Latents, batch_size=1)
    frames = config.duration_frames
    if "6" in workflow and "inputs" in workflow["6"]:
        workflow["6"]["inputs"]["width"] = config.width
        workflow["6"]["inputs"]["height"] = config.height
        workflow["6"]["inputs"]["length"] = frames
        workflow["6"]["inputs"]["batch_size"] = 1
        workflow["6"]["inputs"]["duration_frames"] = frames
    elif "4" in workflow and "inputs" in workflow["4"]:
        workflow["4"]["inputs"]["length"] = frames
        workflow["4"]["inputs"]["duration_frames"] = frames
        workflow["4"]["inputs"]["width"] = config.width
        workflow["4"]["inputs"]["height"] = config.height

    # 3. Inject Approved Storyboard Keyframe Image (Node 11 LoadImage)
    ref_img = config.reference_images[0] if config.reference_images else ""
    if "11" in workflow and "inputs" in workflow["11"]:
        workflow["11"]["inputs"]["image"] = ref_img
    elif "10" in workflow and "inputs" in workflow["10"] and "image_1" in workflow["10"]["inputs"]:
        ref_inputs = workflow["10"]["inputs"]
        for i in range(1, 11):
            slot_key = f"image_{i}"
            if i - 1 < len(config.reference_images):
                ref_inputs[slot_key] = config.reference_images[i - 1]
            else:
                ref_inputs[slot_key] = ""

    # 4. Inject Sampling Parameters
    if "7" in workflow and "inputs" in workflow["7"]:
        workflow["7"]["inputs"]["steps"] = config.steps
        workflow["7"]["inputs"]["cfg"] = config.cfg
        workflow["7"]["inputs"]["seed"] = config.seed
    elif "15" in workflow and "inputs" in workflow["15"]:
        workflow["15"]["inputs"]["steps"] = config.steps
        workflow["15"]["inputs"]["cfg"] = config.cfg
        workflow["15"]["inputs"]["seed"] = config.seed

    # 5. Checkpoint override if provided
    if "1" in workflow and "inputs" in workflow["1"] and config.model_checkpoint:
        ckpt = config.model_checkpoint
        if ckpt not in ["wan3.0_i2v_14b_fp8.safetensors", ""]:
            if "unet_name" in workflow["1"]["inputs"]:
                workflow["1"]["inputs"]["unet_name"] = ckpt
            else:
                workflow["1"]["inputs"]["ckpt_name"] = ckpt

    return workflow


def check_endpoint_health(url: Optional[str] = None) -> RunPodHealthReport:
    """Probes a ComfyUI / RunPod endpoint and returns a detailed diagnostic report."""
    raw_setting = url or os.environ.get("RUNPOD_COMFY_URL", DEFAULT_COMFY_URL)
    candidates = [u.strip().rstrip("/") for u in raw_setting.split(",") if u.strip()]
    if not candidates:
        candidates = ["http://127.0.0.1:8188"]

    # Try all candidates and pick first reachable
    last_report = None
    for target_url in candidates:
        start_time = time.time()
        try:
            resp = requests.get(f"{target_url}/system_stats", timeout=4.0)
            latency_ms = round((time.time() - start_time) * 1000, 1)

            if resp.status_code != 200:
                last_report = RunPodHealthReport(
                    url=target_url,
                    is_reachable=False,
                    latency_ms=latency_ms,
                    status_summary=f"HTTP Error {resp.status_code}"
                )
                continue

            data = resp.json()
            system_info = data.get("system", {})
            comfy_ver = system_info.get("comfyui_version", "unknown")

            devices = data.get("devices", [])
            gpu_name = None
            vram_total = None
            vram_free = None
            if devices:
                d0 = devices[0]
                gpu_name = d0.get("name")
                vram_total = round(d0.get("vram_total", 0) / (1024**3), 2)
                vram_free = round(d0.get("vram_free", 0) / (1024**3), 2)

            # Check loaded checkpoints (checkpoints, diffusion models / UNETs)
            checkpoints = []
            try:
                for loader_node, param in [
                    ("CheckpointLoaderSimple", "ckpt_name"),
                    ("UNETLoader", "unet_name"),
                    ("DiffusionModelLoader", "unet_name"),
                ]:
                    obj_resp = requests.get(f"{target_url}/object_info/{loader_node}", timeout=3.0)
                    if obj_resp.status_code == 200:
                        obj_data = obj_resp.json()
                        input_field = obj_data.get(loader_node, {}).get("input", {}).get("required", {}).get(param, [])
                        if input_field and isinstance(input_field[0], list):
                            for item in input_field[0]:
                                if item and item not in checkpoints:
                                    checkpoints.append(item)
            except Exception:
                pass

            has_wan3 = any("wan3" in c.lower() for c in checkpoints)
            has_wan2 = any("wan2" in c.lower() for c in checkpoints)
            has_ipadapter = any("ip-adapter" in c.lower() for c in checkpoints)

            return RunPodHealthReport(
                url=target_url,
                is_reachable=True,
                latency_ms=latency_ms,
                gpu_name=gpu_name,
                vram_total_gb=vram_total,
                vram_free_gb=vram_free,
                comfyui_version=comfy_ver,
                available_checkpoints=checkpoints,
                has_wan3=has_wan3,
                has_wan2=has_wan2,
                has_ipadapter=has_ipadapter,
                status_summary="Healthy (Online)"
            )

        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            last_report = RunPodHealthReport(
                url=target_url,
                is_reachable=False,
                latency_ms=latency_ms,
                status_summary=f"Unreachable ({type(e).__name__})"
            )

    return last_report or RunPodHealthReport(
        url=candidates[0],
        is_reachable=False,
        latency_ms=0.0,
        status_summary="No valid candidates"
    )

