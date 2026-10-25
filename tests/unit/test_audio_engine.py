"""Unit tests for the Audio Engine."""

import pytest
import os
import asyncio
from core.audio_engine import synthesize_speech, extract_word_timestamps, generate_narration_with_subtitles


@pytest.mark.asyncio
async def test_audio_synthesis_and_timestamps(tmp_path):
    test_audio = str(tmp_path / "test_voice.mp3")
    sample_text = "Can you solve this puzzle?"

    audio_path, subtitles = await generate_narration_with_subtitles(
        text=sample_text,
        output_audio_path=test_audio,
        whisper_model_size="tiny"
    )

    assert os.path.exists(audio_path)
    assert os.path.getsize(audio_path) > 0
    assert len(subtitles.words) > 0
    assert subtitles.words[0].start_ms >= 0
    assert subtitles.words[-1].end_ms > subtitles.words[0].start_ms


def test_character_voice_persona_resolution():
    from core.audio_engine import resolve_voice_persona

    # Kid / Child
    kid_p = resolve_voice_persona("kid")
    assert kid_p["edge_voice"] == "en-US-AnaNeural"
    assert kid_p["puter_voice"] == "Ivy"
    assert kid_p["cloudflare_speaker"] == "thalia"

    # Animal / Cartoon
    animal_p = resolve_voice_persona(prompt_context="A cute little squirrel finding acorns in Pixar 3D")
    assert animal_p["edge_voice"] == "en-US-AnaNeural"
    assert animal_p["edge_pitch"] == "+20Hz"
    assert animal_p["cloudflare_speaker"] == "hermes"

    # Deep Villain / Monster
    villain_p = resolve_voice_persona("deep_villain")
    assert villain_p["edge_voice"] == "en-US-ChristopherNeural"
    assert villain_p["edge_pitch"] == "-12Hz"
    assert villain_p["cloudflare_speaker"] == "zeus"

    # Female
    female_p = resolve_voice_persona("female_narrator")
    assert "ava" in female_p["edge_voice"].lower() or "jenny" in female_p["edge_voice"].lower()
    assert female_p["cloudflare_speaker"] == "asteria"
    assert female_p["puter_voice"] == "Joanna"


def test_multilingual_language_detection_and_voice_routing():
    from core.audio_engine import detect_text_language, resolve_voice_persona

    # Unicode script checks
    assert detect_text_language("नमस्ते आप कैसे हैं?") == "hi"
    assert detect_text_language("こんにちは、世界！") == "ja"
    assert detect_text_language("안녕하세요") == "ko"
    assert detect_text_language("مرحبا بك") == "ar"
    assert detect_text_language("Привет мир") == "ru"
    assert detect_text_language("你好，世界") == "zh"
    assert detect_text_language("Hello brave traveler") == "en"

    # Contextual Latin multilingual checks
    assert detect_text_language("Bhai dekh, main bol raha hoon", "A Bollywood comedy story in Hindi") == "hi"
    assert detect_text_language("C'est la vie mon ami", "Story with French dialogue") == "fr"
    assert detect_text_language("Hola amigo como estas", "Dialogue in Spanish") == "es"

    # Multilingual Persona Resolution: Hindi
    hi_p = resolve_voice_persona("male_narrator", language="hi")
    assert hi_p["edge_voice"] == "hi-IN-MadhurNeural"
    assert hi_p["puter_voice"] == "Aditi"

    hi_female = resolve_voice_persona("female_narrator", language="hi")
    assert hi_female["edge_voice"] == "hi-IN-SwaraNeural"

    # Multilingual Persona Resolution: Japanese
    ja_p = resolve_voice_persona("cartoon_animal", language="ja")
    assert ja_p["edge_voice"] == "ja-JP-NanamiNeural"
    assert ja_p["edge_pitch"] == "+20Hz"

    # Multilingual Persona Resolution: Spanish
    es_p = resolve_voice_persona("deep_villain", language="es")
    assert es_p["edge_voice"] == "es-ES-AlvaroNeural"
    assert es_p["edge_pitch"] == "-12Hz"

