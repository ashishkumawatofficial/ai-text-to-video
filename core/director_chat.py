"""Conversational AI Director Copilot engine powered by Gemini.

Translates natural language director notes into surgical JSON delta actions
applied in real-time to active StoryboardCards.
"""

from __future__ import annotations

import os
import json
import re
from typing import Tuple, Optional, Dict, Any

from core.models import StudioSession, StoryboardCard
from core.config import get_gemini_api_keys, get_puter_api_key

_DIRECTOR_SYSTEM_INSTRUCTION = """You are an expert AI Film Director and Storyboard Copilot for an AI video generation studio.
The user will give you instructions to modify, polish, or direct the storyboard of a short cinematic video.

You have access to the current list of storyboard scenes (beats).
Your task is to:
1. Provide a professional, encouraging director's response explaining what you did.
2. Output a structured JSON delta describing the exact surgical modification.

Allowed delta actions:
- UPDATE_BEAT:
  {"action": "UPDATE_BEAT", "target_beat": <0-indexed beat number>, "field": "visual_prompt"|"dialogue"|"camera_motion", "new_value": "<new text>"}
- CHANGE_ASPECT_RATIO:
  {"action": "CHANGE_ASPECT_RATIO", "new_value": "16:9"|"9:16"|"1:1"}
- REROLL_KEYFRAME:
  {"action": "REROLL_KEYFRAME", "target_beat": <0-indexed beat number>}

Respond strictly in the following JSON format:
{
  "reply": "Your brief conversational response to the creator",
  "delta": { ... action object or null if general conversation ... }
}
"""


async def process_co_director_message(
    user_message: str,
    session: StudioSession
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Processes a user message and extracts conversational reply and storyboard delta action."""
    keys = get_gemini_api_keys()

    # Build context summary of current beats
    beats_summary = []
    for card in session.beats:
        beats_summary.append(
            f"Beat {card.beat_index}: Prompt: '{card.visual_prompt}' | Dialogue: '{card.dialogue_text}' | Camera: {card.camera_motion}"
        )
    beats_context = "\n".join(beats_summary)

    prompt_payload = f"""Current Storyboard Context:
Aspect Ratio: {session.aspect_ratio}
{beats_context}

Creator Instruction:
"{user_message}"

Generate your response in the required JSON format:
"""

    if os.environ.get("TEST_MODE") != "1":
        if keys:
            from google import genai
            from google.genai import types

            for api_key in keys:
                for model_name in ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]:
                    try:
                        client = genai.Client(api_key=api_key)
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt_payload,
                            config=types.GenerateContentConfig(
                                system_instruction=_DIRECTOR_SYSTEM_INSTRUCTION,
                                response_mime_type="application/json",
                                temperature=0.3,
                            )
                        )

                        raw_text = response.text or "{}"
                        parsed = json.loads(raw_text)
                        reply = parsed.get("reply", "Updated the storyboard according to your notes.")
                        delta = parsed.get("delta")
                        return reply, delta
                    except Exception as e:
                        print(f"Gemini director chat key ({api_key[:6]}...) model {model_name} error: {e}")

        # Fallback Tier 2: Puter AI Chat driver (gpt-4o / claude-sonnet)
        puter_key = get_puter_api_key()
        if puter_key:
            for puter_model in ["gpt-4o", "claude-sonnet"]:
                try:
                    import requests
                    p_url = "https://api.puter.com/drivers/call"
                    p_headers = {
                        "content-type": "text/plain;actually=json",
                        "user-agent": "puter-js/1.0",
                        "origin": "https://puter.work",
                        "referer": "https://puter.work/",
                    }
                    p_payload = {
                        "interface": "puter-chat-completion",
                        "driver": "ai-chat",
                        "test_mode": False,
                        "method": "complete",
                        "args": {
                            "model": puter_model,
                            "messages": [
                                {"role": "system", "content": _DIRECTOR_SYSTEM_INSTRUCTION + "\nOutput MUST be valid JSON with 'reply' and 'delta' keys without markdown wrap."},
                                {"role": "user", "content": prompt_payload}
                            ]
                        },
                        "auth_token": puter_key
                    }
                    p_resp = requests.post(p_url, json=p_payload, headers=p_headers, timeout=20.0)
                    if p_resp.status_code == 200:
                        p_data = p_resp.json()
                        msg_content = p_data.get("result", {}).get("message", {}).get("content", "")
                        if msg_content:
                            clean_json = msg_content.strip()
                            if clean_json.startswith("```"):
                                clean_json = clean_json.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                            parsed = json.loads(clean_json)
                            reply = parsed.get("reply", "Updated the storyboard according to your notes.")
                            delta = parsed.get("delta")
                            return reply, delta
                except Exception as e:
                    print(f"Puter director chat model ({puter_model}) error: {e}")

    # Rule-based fallback if offline or API error
    lower_msg = user_message.lower()

    # Aspect ratio detection
    if "9:16" in user_message or "vertical" in lower_msg or "short" in lower_msg or "reel" in lower_msg:
        return "Switched the studio canvas to 9:16 vertical shorts format.", {
            "action": "CHANGE_ASPECT_RATIO",
            "new_value": "9:16"
        }
    elif "16:9" in user_message or "widescreen" in lower_msg or "horizontal" in lower_msg or "youtube" in lower_msg:
        return "Switched the studio canvas to 16:9 widescreen format.", {
            "action": "CHANGE_ASPECT_RATIO",
            "new_value": "16:9"
        }

    # Beat number detection
    match_beat = re.search(r"beat\s*#?(\d+)|scene\s*#?(\d+)|shot\s*#?(\d+)", lower_msg)
    target_idx = 0
    if match_beat:
        num = next(g for g in match_beat.groups() if g is not None)
        target_idx = max(0, int(num) - 1)  # 1-indexed in human speech -> 0-indexed

    # Check for image re-roll or generation request
    if any(k in lower_msg for k in ["reroll", "re-roll", "actual image", "regenerate", "new image", "render image"]):
        return f"Re-generating keyframe artwork for Shot {target_idx + 1}.", {
            "action": "REROLL_KEYFRAME",
            "target_beat": target_idx
        }

    # Voice persona detection in Director Chat
    if any(k in lower_msg for k in ["kid voice", "child voice", "kids voice"]):
        return "Switched narration persona to Kid / Child voice.", {
            "action": "CHANGE_VOICE_PERSONA",
            "new_value": "kid"
        }
    elif any(k in lower_msg for k in ["cartoon voice", "animal voice", "cartoon animal"]):
        return "Switched narration persona to Cartoon / Animal character voice.", {
            "action": "CHANGE_VOICE_PERSONA",
            "new_value": "cartoon_animal"
        }
    elif any(k in lower_msg for k in ["villain voice", "monster voice", "deep voice"]):
        return "Switched narration persona to Deep Villain / Monster voice.", {
            "action": "CHANGE_VOICE_PERSONA",
            "new_value": "deep_villain"
        }
    elif any(k in lower_msg for k in ["female voice", "woman voice"]):
        return "Switched narration persona to Female Narrator.", {
            "action": "CHANGE_VOICE_PERSONA",
            "new_value": "female_narrator"
        }

    # Background music adjustments
    if any(k in lower_msg for k in ["mute music", "remove music", "no music", "disable music"]):
        return "Disabled background music score for the project.", {
            "action": "CHANGE_MUSIC",
            "new_value": "none"
        }
    elif any(k in lower_msg for k in ["action music", "fast music", "fast-paced"]):
        return "Updated background soundtrack to Fast-Paced Action Pulse.", {
            "action": "CHANGE_MUSIC",
            "new_value": "fast_paced_action_pulse"
        }
    elif any(k in lower_msg for k in ["ambient music", "cinematic music", "slow music"]):
        return "Updated background soundtrack to Ambient Cinematic Score.", {
            "action": "CHANGE_MUSIC",
            "new_value": "ambient_cinematic_score"
        }

    if "dialogue" in lower_msg or "say" in lower_msg:
        return f"Updated the dialogue for Scene {target_idx + 1}.", {
            "action": "UPDATE_BEAT",
            "target_beat": target_idx,
            "field": "dialogue",
            "new_value": user_message
        }

    # Clean meta text from visual prompt update
    clean_clause = re.sub(r"\b(?:for\s+)?(?:shot|scene|beat)\s*#?\d+\b", "", user_message, flags=re.IGNORECASE)
    clean_clause = re.sub(r"\b(?:i\s+want|make|change|set|update)\b", "", clean_clause, flags=re.IGNORECASE).strip(" ,.:;")
    existing_prompt = session.beats[target_idx].visual_prompt if target_idx < len(session.beats) else ""
    updated_prompt = f"{existing_prompt}, {clean_clause}" if clean_clause else existing_prompt

    return f"Applied your directorial vision to Scene {target_idx + 1}.", {
        "action": "UPDATE_BEAT",
        "target_beat": target_idx,
        "field": "visual_prompt",
        "new_value": updated_prompt
    }
