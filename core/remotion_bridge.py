"""Bridge connecting Python VideoProject models to Remotion CLI rendering."""

from __future__ import annotations
import os
import json
import uuid
import shutil
import subprocess
from typing import Dict, Any, Optional
from core.models import VideoProject, VisualStrategyRoute, ImageRole


REMOTION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "remotion"))
PUBLIC_MEDIA_DIR = os.path.join(REMOTION_DIR, "public", "media")


def stage_asset_for_remotion(source_path: Optional[str]) -> str:
    """Copies/stages local media into remotion/public/media/ and returns relative path for staticFile()."""
    if not source_path or not os.path.exists(source_path):
        return ""

    if source_path.startswith("http://") or source_path.startswith("https://") or source_path.startswith("data:"):
        return source_path

    os.makedirs(PUBLIC_MEDIA_DIR, exist_ok=True)
    ext = os.path.splitext(source_path)[1]
    unique_name = f"{os.path.splitext(os.path.basename(source_path))[0]}_{uuid.uuid4().hex[:6]}{ext}"
    dest_path = os.path.join(PUBLIC_MEDIA_DIR, unique_name)

    shutil.copy2(source_path, dest_path)
    return f"media/{unique_name}"


def build_remotion_props(project: VideoProject) -> Dict[str, Any]:
    """Converts a VideoProject domain object into Remotion UniversalVideoProps JSON payload."""
    fps = project.fps
    current_frame = 0
    scenes_payload = []

    for beat in project.scenes:
        duration_frames = max(1, int(round(beat.duration_sec * fps)))
        
        media_src = ""
        scene_type = "video_clip"

        if beat.output_video_path and os.path.exists(beat.output_video_path):
            media_src = stage_asset_for_remotion(beat.output_video_path)
            scene_type = "video_clip"
        else:
            # Check for plate / start frame
            start_img = next((a.file_path for a in beat.image_assets if a.role in [ImageRole.START_FRAME, ImageRole.SCENE_IMAGE] and os.path.exists(a.file_path)), None)
            if not start_img:
                start_img = next((a.file_path for a in beat.image_assets if os.path.exists(a.file_path)), None)

            if start_img and os.path.exists(start_img):
                media_src = stage_asset_for_remotion(start_img)
                scene_type = "static_plate"
            elif beat.visual_strategy == VisualStrategyRoute.PROGRAMMATIC_HYBRID:
                scene_type = "static_plate"

        scenes_payload.append({
            "id": f"scene_{beat.beat_index}",
            "startFrame": current_frame,
            "durationInFrames": duration_frames,
            "type": scene_type,
            "mediaSrc": media_src
        })

        current_frame += duration_frames

    # Build subtitles payload
    subtitles_payload = {
        "stylePreset": project.subtitles.style_preset,
        "words": [
            {
                "word": w.word,
                "startMs": w.start_ms,
                "endMs": w.end_ms
            }
            for w in project.subtitles.words
        ]
    }

    # Stage audio assets
    staged_vo = stage_asset_for_remotion(project.audio.voiceover_path)
    staged_music = stage_asset_for_remotion(project.audio.music_path)

    sfx_cues = []
    for cue in project.audio.sfx_cues:
        staged_sfx = stage_asset_for_remotion(cue.sfx_name)
        if staged_sfx:
            sfx_cues.append({
                "src": staged_sfx,
                "startFrame": cue.start_frame if cue.start_frame is not None else int(round(cue.offset_sec * fps)),
                "volume": cue.volume
            })

    audio_payload = {
        "voiceoverSrc": staged_vo,
        "musicSrc": staged_music,
        "musicBaseVolume": project.audio.music_base_volume,
        "musicDuckedVolume": project.audio.music_ducked_volume,
        "sfxCues": sfx_cues
    }

    return {
        "genre": project.genre.value,
        "totalDurationFrames": max(current_frame, 30),
        "fps": fps,
        "width": project.width,
        "height": project.height,
        "scenes": scenes_payload,
        "subtitles": subtitles_payload,
        "audio": audio_payload
    }


import socket


def find_free_port() -> int:
    """Finds an available TCP port for ephemeral server execution."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def extract_terminal_frame(video_path: str, output_image_path: str) -> str:
    """Extracts the final frame of a completed video for continuous chaining."""
    os.makedirs(os.path.dirname(os.path.abspath(output_image_path)), exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-sseof", "-0.1",
        "-i", video_path,
        "-update", "1",
        "-q:v", "2",
        output_image_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_image_path


def render_project_to_video(
    project: VideoProject,
    output_mp4_path: str,
    composition_id: str = "UniversalComposition"
) -> str:
    """Invokes Remotion CLI to compile and render the master video file."""
    props = build_remotion_props(project)
    
    temp_dir = os.path.abspath(os.path.join(REMOTION_DIR, "..", "outputs", "temp"))
    os.makedirs(temp_dir, exist_ok=True)
    props_filename = f"props_{uuid.uuid4().hex[:8]}.json"
    props_filepath = os.path.join(temp_dir, props_filename)

    with open(props_filepath, "w", encoding="utf-8") as f:
        json.dump(props, f, indent=2)

    abs_output = os.path.abspath(output_mp4_path)
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)
    port = find_free_port()

    cmd = [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        composition_id,
        abs_output,
        f"--props={props_filepath}",
        f"--port={port}"
    ]

    result = subprocess.run(cmd, cwd=REMOTION_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Remotion render failed with exit code {result.returncode}:\n{result.stderr}\n{result.stdout}")

    return abs_output
