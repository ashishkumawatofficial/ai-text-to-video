"""Tail-to-Head Frame Extractor and Shot Continuity Manager."""

from __future__ import annotations
import os
import cv2
from typing import Optional
from core.models import StoryboardBeat, ImageAsset, ImageRole, ContinuityLink


def extract_terminal_frame(video_path: str, output_frame_path: str) -> str:
    """Extracts the exact final frame (Frame -1) of a video file using OpenCV."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found for frame extraction: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        raise ValueError(f"Video has 0 frames: {video_path}")

    # Seek to last frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError(f"Failed to read final frame {total_frames - 1} from {video_path}")

    os.makedirs(os.path.dirname(os.path.abspath(output_frame_path)), exist_ok=True)
    success = cv2.imwrite(output_frame_path, frame)
    if not success:
        raise RuntimeError(f"Failed to write extracted frame to {output_frame_path}")

    return output_frame_path


def chain_shots(
    previous_clip_path: str,
    next_beat: StoryboardBeat,
    temp_dir: str = "outputs/temp"
) -> StoryboardBeat:
    """Extracts Frame -1 from previous clip and injects it as Frame 0 (START_FRAME) of next_beat."""
    os.makedirs(temp_dir, exist_ok=True)
    tail_frame_filename = f"beat_{next_beat.beat_index - 1}_tail_frame.png"
    tail_frame_path = os.path.abspath(os.path.join(temp_dir, tail_frame_filename))

    extract_terminal_frame(previous_clip_path, tail_frame_path)

    # Inject as START_FRAME asset
    start_asset = ImageAsset(
        file_path=tail_frame_path,
        role=ImageRole.START_FRAME,
        source="extracted_tail_frame"
    )
    
    # Remove any existing start frames
    next_beat.image_assets = [a for a in next_beat.image_assets if a.role != ImageRole.START_FRAME]
    next_beat.image_assets.append(start_asset)

    # Configure continuity link
    next_beat.continuity.chain_from_previous = True
    next_beat.continuity.extracted_tail_frame_path = tail_frame_path

    return next_beat
