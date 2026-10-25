"""Sound effects resolver, audio ducking parameters, and mixer utilities."""

from __future__ import annotations
import os
from typing import List, Optional, Dict
from core.models import AudioAsset, AudioCue

SFX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "audio", "sfx"))
MUSIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "audio", "music"))

SFX_ALIASES: Dict[str, str] = {
    "tick": "clock_tick.wav",
    "clock_tick": "clock_tick.wav",
    "countdown_tick": "clock_tick.wav",
    "lift": "glass_lift.wav",
    "glass_lift": "glass_lift.wav",
    "putdown": "glass_putdown.wav",
    "glass_putdown": "glass_putdown.wav",
    "pour": "water_pour.wav",
    "water_pour": "water_pour.wav",
    "chime": "solved_chime.wav",
    "solved_chime": "solved_chime.wav",
    "whoosh": "whoosh.wav",
    "transition": "whoosh.wav",
}


def get_available_sfx() -> List[str]:
    """Returns a list of all available sound effects in the library."""
    if not os.path.exists(SFX_DIR):
        return []
    return [f for f in os.listdir(SFX_DIR) if f.endswith((".wav", ".mp3", ".ogg", ".m4a"))]


def resolve_sfx_file(sfx_name: str) -> Optional[str]:
    """Resolves an SFX name or alias to an absolute path."""
    clean_name = sfx_name.strip().lower()
    filename = SFX_ALIASES.get(clean_name, clean_name)
    if not (filename.endswith(".wav") or filename.endswith(".mp3")):
        filename += ".wav"

    direct_path = os.path.join(SFX_DIR, filename)
    if os.path.exists(direct_path):
        return direct_path

    # Check without extension
    base_target = os.path.splitext(filename)[0]
    for candidate in get_available_sfx():
        if os.path.splitext(candidate)[0].lower() == base_target:
            return os.path.join(SFX_DIR, candidate)

    return None


def resolve_music_file(music_name: Optional[str] = "bgm_ambient.wav") -> Optional[str]:
    """Resolves background music track."""
    if not music_name:
        return None
    direct_path = os.path.join(MUSIC_DIR, music_name)
    if os.path.exists(direct_path):
        return direct_path
    
    # Check default ambient
    default_ambient = os.path.join(MUSIC_DIR, "bgm_ambient.wav")
    if os.path.exists(default_ambient):
        return default_ambient

    return None


def build_audio_asset(
    voiceover_path: str,
    music_name: Optional[str] = "bgm_ambient.wav",
    sfx_requests: Optional[List[Dict[str, any]]] = None,
    fps: int = 30
) -> AudioAsset:
    """Builds a complete AudioAsset container with resolved file paths and start frames."""
    resolved_music = resolve_music_file(music_name)
    resolved_cues: List[AudioCue] = []

    if sfx_requests:
        for req in sfx_requests:
            name = req.get("sfx_name", "")
            resolved_path = resolve_sfx_file(name)
            if resolved_path:
                offset_sec = float(req.get("offset_sec", 0.0))
                volume = float(req.get("volume", 1.0))
                start_frame = int(round(offset_sec * fps))
                resolved_cues.append(
                    AudioCue(
                        sfx_name=resolved_path,
                        offset_sec=offset_sec,
                        start_frame=start_frame,
                        volume=volume
                    )
                )

    return AudioAsset(
        voiceover_path=voiceover_path,
        music_path=resolved_music,
        music_base_volume=0.35,
        music_ducked_volume=0.10,
        sfx_cues=resolved_cues
    )
