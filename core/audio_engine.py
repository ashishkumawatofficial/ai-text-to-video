"""Audio synthesis and word-level alignment engine with multi-tier neural fallback.

Tiers:
1. Cloudflare Deepgram Aura-2 (@cf/deepgram/aura-2-en) - High conversational emotion & natural breath
2. Puter AI Generative Speech (AWS Polly Generative engine via Puter token)
3. Microsoft Edge-TTS (HD Multilingual Neural voices, 100% free unlimited fallback)
"""

from __future__ import annotations
import os
import asyncio
import logging
from typing import Tuple, List, Optional
import requests
import edge_tts
from faster_whisper import WhisperModel
from core.config import get_cloudflare_credentials, get_puter_api_key
from core.models import SubtitleTrack, SubtitleWordToken

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "en-US-BrianMultilingualNeural"
FALLBACK_VOICE = "en-US-ChristopherNeural"


# Character Voice Persona Mapping
VOICE_PERSONA_MAP = {
    "kid": {
        "cloudflare_speaker": "thalia",
        "puter_voice": "Ivy",
        "puter_engine": "neural",
        "edge_voice": "en-US-AnaNeural",
        "edge_pitch": "+12Hz",
        "edge_rate": "+8%",
    },
    "cartoon_animal": {
        "cloudflare_speaker": "hermes",
        "puter_voice": "Kevin",
        "puter_engine": "neural",
        "edge_voice": "en-US-AnaNeural",
        "edge_pitch": "+20Hz",
        "edge_rate": "+15%",
    },
    "deep_villain": {
        "cloudflare_speaker": "zeus",
        "puter_voice": "Matthew",
        "puter_engine": "generative",
        "edge_voice": "en-US-ChristopherNeural",
        "edge_pitch": "-12Hz",
        "edge_rate": "-6%",
    },
    "female_narrator": {
        "cloudflare_speaker": "asteria",
        "puter_voice": "Joanna",
        "puter_engine": "generative",
        "edge_voice": "en-US-AvaMultilingualNeural",
        "edge_pitch": "+0Hz",
        "edge_rate": "+0%",
    },
    "male_narrator": {
        "cloudflare_speaker": "orion",
        "puter_voice": "Matthew",
        "puter_engine": "generative",
        "edge_voice": "en-US-BrianMultilingualNeural",
        "edge_pitch": "+0Hz",
        "edge_rate": "+0%",
    },
    "energetic_action": {
        "cloudflare_speaker": "apollo",
        "puter_voice": "Stephen",
        "puter_engine": "generative",
        "edge_voice": "en-US-GuyNeural",
        "edge_pitch": "+4Hz",
        "edge_rate": "+10%",
    },
}

# Multilingual native neural voice mapping for international dialogue
LANGUAGE_VOICE_MAP = {
    "hi": {  # Hindi
        "male": "hi-IN-MadhurNeural",
        "female": "hi-IN-SwaraNeural",
        "kid": "hi-IN-SwaraNeural",
        "cartoon_animal": "hi-IN-SwaraNeural",
        "deep_villain": "hi-IN-MadhurNeural",
        "puter_voice": "Aditi",
    },
    "ja": {  # Japanese
        "male": "ja-JP-KeitaNeural",
        "female": "ja-JP-NanamiNeural",
        "kid": "ja-JP-NanamiNeural",
        "cartoon_animal": "ja-JP-NanamiNeural",
        "deep_villain": "ja-JP-KeitaNeural",
        "puter_voice": "Takumi",
    },
    "es": {  # Spanish
        "male": "es-ES-AlvaroNeural",
        "female": "es-ES-ElviraNeural",
        "kid": "es-ES-ElviraNeural",
        "cartoon_animal": "es-ES-ElviraNeural",
        "deep_villain": "es-ES-AlvaroNeural",
        "puter_voice": "Conchita",
    },
    "fr": {  # French
        "male": "fr-FR-HenriNeural",
        "female": "fr-FR-DeniseNeural",
        "kid": "fr-FR-DeniseNeural",
        "cartoon_animal": "fr-FR-DeniseNeural",
        "deep_villain": "fr-FR-HenriNeural",
        "puter_voice": "Celine",
    },
    "de": {  # German
        "male": "de-DE-KillianNeural",
        "female": "de-DE-KatjaNeural",
        "kid": "de-DE-KatjaNeural",
        "cartoon_animal": "de-DE-KatjaNeural",
        "deep_villain": "de-DE-KillianNeural",
        "puter_voice": "Marlene",
    },
    "zh": {  # Chinese (Mandarin)
        "male": "zh-CN-YunjianNeural",
        "female": "zh-CN-XiaoxiaoNeural",
        "kid": "zh-CN-XiaoxiaoNeural",
        "cartoon_animal": "zh-CN-XiaoyiNeural",
        "deep_villain": "zh-CN-YunjianNeural",
        "puter_voice": "Zhiyu",
    },
    "ar": {  # Arabic
        "male": "ar-SA-HamedNeural",
        "female": "ar-SA-ZariyahNeural",
        "kid": "ar-SA-ZariyahNeural",
        "cartoon_animal": "ar-SA-ZariyahNeural",
        "deep_villain": "ar-SA-HamedNeural",
        "puter_voice": "Zeina",
    },
    "ko": {  # Korean
        "male": "ko-KR-InJoonNeural",
        "female": "ko-KR-SunHiNeural",
        "kid": "ko-KR-SunHiNeural",
        "cartoon_animal": "ko-KR-SunHiNeural",
        "deep_villain": "ko-KR-InJoonNeural",
        "puter_voice": "Seoyeon",
    },
    "it": {  # Italian
        "male": "it-IT-DiegoNeural",
        "female": "it-IT-ElsaNeural",
        "kid": "it-IT-ElsaNeural",
        "cartoon_animal": "it-IT-ElsaNeural",
        "deep_villain": "it-IT-DiegoNeural",
        "puter_voice": "Carla",
    },
    "pt": {  # Portuguese
        "male": "pt-BR-AntonioNeural",
        "female": "pt-BR-FranciscaNeural",
        "kid": "pt-BR-FranciscaNeural",
        "cartoon_animal": "pt-BR-FranciscaNeural",
        "deep_villain": "pt-BR-AntonioNeural",
        "puter_voice": "Camila",
    },
    "ru": {  # Russian
        "male": "ru-RU-DmitryNeural",
        "female": "ru-RU-SvetlanaNeural",
        "kid": "ru-RU-SvetlanaNeural",
        "cartoon_animal": "ru-RU-SvetlanaNeural",
        "deep_villain": "ru-RU-DmitryNeural",
        "puter_voice": "Tatyana",
    },
}


def detect_text_language(text: str, context: str = "") -> str:
    """Detects primary language code (e.g. 'hi', 'ja', 'es', 'fr', 'en') from text and context."""
    if not text:
        return "en"

    # 1. Unicode script detection on dialogue text (deterministic, 0ms latency)
    for char in text:
        cp = ord(char)
        if 0x0900 <= cp <= 0x097F:
            return "hi"  # Devanagari (Hindi)
        if (0x3040 <= cp <= 0x309F) or (0x30A0 <= cp <= 0x30FF):
            return "ja"  # Japanese Hiragana / Katakana
        if (0xAC00 <= cp <= 0xD7AF) or (0x1100 <= cp <= 0x11FF):
            return "ko"  # Korean Hangul
        if 0x0600 <= cp <= 0x06FF:
            return "ar"  # Arabic
        if 0x0400 <= cp <= 0x04FF:
            return "ru"  # Cyrillic
        if 0x4E00 <= cp <= 0x9FFF:
            return "zh"  # CJK Ideographs (Chinese)

    # 2. Check context/prompt for explicit language requests (e.g. "Spanish dialogue", "Hindi story")
    ctx_lower = (context + " " + text).lower()
    if any(k in ctx_lower for k in ["spanish", "español", "in spanish"]):
        return "es"
    if any(k in ctx_lower for k in ["french", "français", "in french"]):
        return "fr"
    if any(k in ctx_lower for k in ["german", "deutsch", "in german"]):
        return "de"
    if any(k in ctx_lower for k in ["italian", "italiano", "in italian"]):
        return "it"
    if any(k in ctx_lower for k in ["portuguese", "português", "in portuguese"]):
        return "pt"
    if any(k in ctx_lower for k in ["hindi", "bollywood", "in hindi", "hinglish"]):
        return "hi"
    if any(k in ctx_lower for k in ["japanese", "anime", "in japanese"]):
        return "ja"

    return "en"


def resolve_voice_persona(voice_hint: Optional[str] = None, prompt_context: str = "", language: Optional[str] = None) -> dict:
    """Resolves an abstract character archetype or voice name into tier-specific TTS settings."""
    hint = (voice_hint or "").lower().strip()
    ctx = prompt_context.lower()

    # Determine base profile & persona key
    persona_key = "male"
    if hint in VOICE_PERSONA_MAP:
        base_profile = dict(VOICE_PERSONA_MAP[hint])
        persona_key = hint
    elif any(k in hint or k in ctx for k in ["kid", "child", "boy", "girl", "toddler", "baby"]):
        base_profile = dict(VOICE_PERSONA_MAP["kid"])
        persona_key = "kid"
    elif any(k in hint or k in ctx for k in ["animal", "cartoon", "mouse", "squirrel", "rabbit", "cat", "dog", "cow", "duck", "animated", "pixar"]):
        base_profile = dict(VOICE_PERSONA_MAP["cartoon_animal"])
        persona_key = "cartoon_animal"
    elif any(k in hint or k in ctx for k in ["villain", "monster", "demon", "dragon", "beast", "deep voice", "dark lord"]):
        base_profile = dict(VOICE_PERSONA_MAP["deep_villain"])
        persona_key = "deep_villain"
    elif any(k in hint for k in ["female", "woman", "ava", "jenny", "emma", "queen", "mother", "lady"]) or (not hint and any(k in ctx for k in ["princess", "queen", "she ", "her "])):
        base_profile = dict(VOICE_PERSONA_MAP["female_narrator"])
        persona_key = "female"
    elif any(k in hint or k in ctx for k in ["action", "combat", "fight", "sports", "hype", "fast"]):
        base_profile = dict(VOICE_PERSONA_MAP["energetic_action"])
        persona_key = "male"
    elif "neural" in hint:
        base_profile = {
            "cloudflare_speaker": "orion",
            "puter_voice": "Matthew",
            "puter_engine": "generative",
            "edge_voice": voice_hint or DEFAULT_VOICE,
            "edge_pitch": "+0Hz",
            "edge_rate": "+0%",
        }
        persona_key = "male"
    else:
        base_profile = dict(VOICE_PERSONA_MAP["male_narrator"])
        persona_key = "male"

    # Multilingual adaptation: If dialogue is in non-English, swap to native locale neural voice
    if language and language != "en" and language in LANGUAGE_VOICE_MAP:
        lang_voices = LANGUAGE_VOICE_MAP[language]
        target_voice = lang_voices.get(persona_key, lang_voices.get("female" if "female" in persona_key else "male"))
        if target_voice:
            base_profile["edge_voice"] = target_voice
        if "puter_voice" in lang_voices:
            base_profile["puter_voice"] = lang_voices["puter_voice"]

    return base_profile


def _synthesize_cloudflare_aura(text: str, output_path: str, speaker: str = "asteria") -> bool:
    """Tier 1: High emotional realism via Cloudflare Deepgram Aura-2."""
    acc, tok = get_cloudflare_credentials()
    if not (acc and tok and not tok.startswith("your_") and len(tok) > 10):
        return False
    try:
        url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/deepgram/aura-2-en"
        headers = {
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json"
        }
        res = requests.post(url, json={"text": text, "speaker": speaker}, headers=headers, timeout=20.0)
        if res.status_code == 200 and len(res.content) > 1000:
            with open(output_path, "wb") as f:
                f.write(res.content)
            logger.info(f"Synthesized voiceover via Tier 1: Cloudflare Deepgram Aura-2 (speaker: {speaker})")
            return True
    except Exception as e:
        logger.warning(f"Tier 1 Cloudflare TTS failed: {e}")
    return False


def _synthesize_puter_generative(
    text: str,
    output_path: str,
    voice: str = "Joanna",
    engine: str = "generative"
) -> bool:
    """Tier 2: AWS Polly Generative & Neural Speech via Puter AI."""
    puter_key = get_puter_api_key()
    if not (puter_key and len(puter_key) > 10):
        return False
    try:
        url = "https://api.puter.com/drivers/call"
        headers = {
            "content-type": "text/plain;actually=json",
            "user-agent": "puter-js/1.0",
            "origin": "https://puter.work",
            "referer": "https://puter.work/"
        }
        payload = {
            "interface": "puter-tts",
            "driver": "ai-tts",
            "test_mode": False,
            "method": "synthesize",
            "args": {
                "text": text,
                "voice": voice,
                "engine": engine
            },
            "auth_token": puter_key
        }
        res = requests.post(url, json=payload, headers=headers, timeout=20.0)
        if res.status_code == 200 and len(res.content) > 1000:
            with open(output_path, "wb") as f:
                f.write(res.content)
            logger.info(f"Synthesized voiceover via Tier 2: Puter AI ({voice}, {engine})")
            return True
    except Exception as e:
        logger.warning(f"Tier 2 Puter Generative TTS failed: {e}")
    return False


async def _synthesize_edge_tts(
    text: str,
    output_path: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> bool:
    """Tier 3: Rock-solid, zero-cost Edge-TTS HD Multilingual Neural synthesis with pitch modulation."""
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await communicate.save(output_path)
        logger.info(f"Synthesized voiceover via Tier 3: Edge-TTS ({voice}, pitch={pitch}, rate={rate})")
        return True
    except Exception as e:
        logger.warning(f"Tier 3 Edge-TTS failed with {voice}: {e}, trying fallback {FALLBACK_VOICE}")
        try:
            communicate = edge_tts.Communicate(text, FALLBACK_VOICE, rate=rate, volume=volume, pitch=pitch)
            await communicate.save(output_path)
            return True
        except Exception as e2:
            logger.error(f"Tier 3 Edge-TTS fallback also failed: {e2}")
            return False


async def synthesize_speech(
    text: str,
    output_audio_path: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    prompt_context: str = "",
    force_refresh: bool = False,
) -> str:
    """Synthesizes text into natural neural speech using a character-aware multi-tier cascade.
    Reuses existing cached audio if available to preserve tokens and eliminate wasted API requests.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_audio_path)), exist_ok=True)

    # Cache check: if audio exists and not force-refresh, reuse it without burning tokens
    if not force_refresh and os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
        return output_audio_path

    # Detect language from dialogue text and prompt context
    lang = detect_text_language(text, prompt_context)

    # Resolve character persona and multilingual native voice
    profile = resolve_voice_persona(voice, prompt_context=prompt_context, language=lang)
    cf_speaker = profile.get("cloudflare_speaker", "asteria")
    puter_v = profile.get("puter_voice", "Joanna")
    puter_eng = profile.get("puter_engine", "generative")
    edge_v = profile.get("edge_voice", voice if "neural" in voice.lower() else DEFAULT_VOICE)
    edge_p = pitch if pitch != "+0Hz" else profile.get("edge_pitch", "+0Hz")
    edge_r = rate if rate != "+0%" else profile.get("edge_rate", "+0%")

    # Zero-waste test mode: preserve Cloudflare neurons & Puter credits by using free Edge-TTS
    if os.environ.get("TEST_MODE") == "1":
        if await _synthesize_edge_tts(text, output_audio_path, voice=edge_v, rate=edge_r, volume=volume, pitch=edge_p):
            return output_audio_path

    # Tier 1: Cloudflare Deepgram Aura-2 (High conversational emotion, English only)
    if lang == "en" and _synthesize_cloudflare_aura(text, output_audio_path, speaker=cf_speaker):
        return output_audio_path

    # Tier 2: Puter AI (AWS Polly Generative & Neural Multilingual)
    if _synthesize_puter_generative(text, output_audio_path, voice=puter_v, engine=puter_eng):
        return output_audio_path

    # Tier 3: Edge-TTS HD Multilingual (Free unlimited fallback with 300+ native voices for 75+ languages)
    if await _synthesize_edge_tts(text, output_audio_path, voice=edge_v, rate=edge_r, volume=volume, pitch=edge_p):
        return output_audio_path

    raise RuntimeError(f"All TTS synthesis tiers failed for text: {text[:50]}...")


def extract_word_timestamps(
    audio_path: str,
    model_size: str = "tiny",
    device: str = "cpu",
    compute_type: str = "int8"
) -> SubtitleTrack:
    """Transcribes audio using Faster-Whisper and extracts millisecond-accurate word tokens."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(audio_path, word_timestamps=True)

    words_list: List[SubtitleWordToken] = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                clean_word = w.word.strip()
                if clean_word:
                    start_ms = int(round(w.start * 1000))
                    end_ms = int(round(w.end * 1000))
                    confidence = float(w.probability) if hasattr(w, "probability") else 1.0
                    words_list.append(
                        SubtitleWordToken(
                            word=clean_word,
                            start_ms=start_ms,
                            end_ms=end_ms,
                            confidence=confidence
                        )
                    )

    return SubtitleTrack(
        style_preset="bold_yellow_glow",
        words=words_list
    )


async def generate_narration_with_subtitles(
    text: str,
    output_audio_path: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
    prompt_context: str = "",
    whisper_model_size: str = "tiny",
    force_refresh: bool = False,
) -> Tuple[str, SubtitleTrack]:
    """Complete audio pipeline: synthesizes character-aware speech and extracts kinetic word-level timestamps."""
    audio_file = await synthesize_speech(
        text,
        output_audio_path,
        voice=voice,
        rate=rate,
        pitch=pitch,
        prompt_context=prompt_context,
        force_refresh=force_refresh
    )
    subtitles = extract_word_timestamps(audio_file, model_size=whisper_model_size)
    return audio_file, subtitles


def get_audio_duration_seconds(audio_path: str) -> float:
    """Accurately returns the duration of an audio file in seconds."""
    if not audio_path or not os.path.exists(audio_path):
        return 0.0
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(audio_path)
        return round(len(seg) / 1000.0, 3)
    except Exception:
        import subprocess
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
            return round(float(res.stdout.strip()), 3)
        except Exception:
            return 3.0


async def synthesize_scene_dialogue(
    text: str,
    output_audio_path: str,
    speaker: str = "Narrator",
    voice_persona: Optional[str] = None,
    prompt_context: str = "",
    whisper_model_size: str = "tiny",
    force_refresh: bool = False,
) -> Tuple[str, float, SubtitleTrack]:
    """Synthesizes dialogue for an individual character beat and extracts word-level subtitles.
    
    Returns:
        (audio_path, duration_seconds, subtitle_track)
    """
    target_voice = voice_persona or DEFAULT_VOICE
    audio_path = await synthesize_speech(
        text=text,
        output_audio_path=output_audio_path,
        voice=target_voice,
        prompt_context=f"{prompt_context} Character speaker: {speaker}",
        force_refresh=force_refresh,
    )
    duration_sec = get_audio_duration_seconds(audio_path)
    try:
        subtitles = extract_word_timestamps(audio_path, model_size=whisper_model_size)
    except Exception as e:
        logger.warning(f"Whisper extraction failed for scene audio: {e}. Generating estimated word timing.")
        words = text.split()
        tokens = []
        if words and duration_sec > 0:
            step_ms = int((duration_sec * 1000) / len(words))
            for i, w in enumerate(words):
                tokens.append(SubtitleWordToken(
                    word=w,
                    start_ms=i * step_ms,
                    end_ms=(i + 1) * step_ms,
                    confidence=1.0
                ))
        subtitles = SubtitleTrack(style_preset="bold_yellow_glow", words=tokens)

    return audio_path, duration_sec, subtitles


def stitch_beat_audio_tracks(
    beat_tracks: List[Tuple[str, float]],  # List of (audio_path, start_offset_sec)
    total_duration_sec: float,
    output_master_audio_path: str,
) -> str:
    """Stitches individual character audio clips with precise silence gaps into a single master voiceover track."""
    from pydub import AudioSegment
    master = AudioSegment.silent(duration=int(round(max(total_duration_sec, 1.0) * 1000)))
    for audio_path, offset_sec in beat_tracks:
        if audio_path and os.path.exists(audio_path):
            try:
                clip = AudioSegment.from_file(audio_path)
                offset_ms = int(round(offset_sec * 1000))
                master = master.overlay(clip, position=offset_ms)
            except Exception as e:
                logger.warning(f"Failed to overlay beat audio {audio_path}: {e}")
    os.makedirs(os.path.dirname(os.path.abspath(output_master_audio_path)), exist_ok=True)
    master.export(output_master_audio_path, format="mp3")
    return output_master_audio_path

