"""Conversational AI Director Copilot engine powered by Gemini.

Translates natural language director notes into surgical JSON delta actions
applied in real-time to active StoryboardCards.
"""

from __future__ import annotations

import os
import json
import re
import asyncio
from typing import Tuple, Optional, Dict, Any

from core.models import StudioSession, StoryboardCard
from core.config import get_gemini_api_keys, get_puter_api_key

_DIRECTOR_SYSTEM_INSTRUCTION = """You are an expert AI Film Director and Storyboard Copilot for an AI video generation studio.
The user will give you instructions to modify, polish, or direct the storyboard of a short cinematic video.

You have access to the current list of storyboard scenes (beats) and the recent conversation history.
Your task is to:
1. Provide a professional, encouraging director's response explaining what you did.
2. Output a structured JSON delta describing the exact surgical modification.

SCENE vs BEAT INDEXING (CRITICAL):
- In the UI, cards are displayed to the user as "Scene 1", "Scene 2", "Scene 3" (1-indexed).
- The internal "target_beat" index MUST be 0-indexed:
  * "Scene 1" or "Beat 1" refers to target_beat: 0
  * "Scene 2" or "Beat 2" refers to target_beat: 1
  * "Scene 3" or "Beat 3" refers to target_beat: 2
- When the creator says "Beat 1", look at the context and current dialogue to determine if they mean the first card (target_beat: 0) or Beat 1 (target_beat: 1).
- When the creator says "for beat 2 and 3" or "for scene 2 and 3", they mean target_beat: 1 AND target_beat: 2!

DIALOGUE CLEARING & SILENT SCENES:
- If the creator says "no dialogue", "remove narrator", "don't want narrator", "silent scene", "clear dialogue", "i don't want that too", or "remove dialogue", set "field": "dialogue" and "new_value": "" (empty string).
- NEVER use REROLL_KEYFRAME for dialogue requests! REROLL_KEYFRAME is strictly for generating a new image artwork take.

CHARACTER MODIFICATIONS (ADD, REPLACE, UPDATE, REMOVE):
- To REPLACE a character: Update the scene's "visual_prompt" replacing the old character with the new character's detailed visual description, attire, and style. If applied to multiple scenes (e.g. "across all scenes"), emit an array of UPDATE_BEAT deltas for all affected beats.
- To ADD a character: Update "visual_prompt" to incorporate the new character into the scene's composition, framing, and action.
- To REMOVE a character: Update "visual_prompt" to remove that character while maintaining the cinematic background and remaining elements.
- To CHANGE SPEAKER: Set "field": "speaker" with "new_value": "<New Character Name>".

MULTI-BEAT UPDATES:
- If an instruction applies to multiple scenes (e.g. "remove narrator from all clips", "replace the hero with a ninja in all scenes", "clear dialogue for scene 2 and 3"), "delta" MUST be a JSON array containing an action object for EACH affected beat.

Allowed delta actions:
- UPDATE_BEAT:
  {"action": "UPDATE_BEAT", "target_beat": <0-indexed integer>, "field": "visual_prompt"|"dialogue"|"camera_motion"|"speaker", "new_value": "<new text or empty string>"}
- CHANGE_ASPECT_RATIO:
  {"action": "CHANGE_ASPECT_RATIO", "new_value": "16:9"|"9:16"|"1:1"}
- REROLL_KEYFRAME:
  {"action": "REROLL_KEYFRAME", "target_beat": <0-indexed integer>}
- CHANGE_VOICE_PERSONA:
  {"action": "CHANGE_VOICE_PERSONA", "new_value": "en-US-ChristopherNeural"|"female_narrator"|"kid"|"cartoon_animal"|"deep_villain"}
- CHANGE_MUSIC:
  {"action": "CHANGE_MUSIC", "new_value": "none"|"ambient_cinematic_score"|"fast_paced_action_pulse"}
- SET_BEAT_DURATION:
  {"action": "SET_BEAT_DURATION", "target_beat": <0-indexed integer>, "duration_seconds": <number>}
- DELETE_BEAT:
  {"action": "DELETE_BEAT", "target_beat": <0-indexed integer>}
- RESTRUCTURE_STORYBOARD:
  Used when creator wants to re-partition, extend, or rewrite the overall story into a new number of clips or durations (e.g. "rewrite into 2 clips of 15s each", "change to 2 scenes of 15 seconds").
  {"action": "RESTRUCTURE_STORYBOARD", "num_beats": <integer>, "duration_per_beat": <number>, "beats": [ {"beat_index": 0, "visual_prompt": "<detailed prompt>", "dialogue": "", "duration_seconds": <sec>, "camera_motion": "slow_push_in"}, ... ]}

CONVERSATIONAL VS ACTION:
If the creator is asking a general film/story question, discussing artistic vision, or seeking advice without requesting a direct edit, answer comprehensively and professionally with "delta": null.

Respond strictly in the following JSON format:
{
  "reply": "Your brief conversational response to the creator",
  "delta": { ... single action object ... } OR [ { ... action 1 ... }, { ... action 2 ... } ] OR null if conversational only
}
"""


async def process_co_director_message(
    user_message: str,
    session: StudioSession
) -> Tuple[str, Optional[Any]]:
    """Processes a user message and extracts conversational reply and storyboard delta action."""
    keys = get_gemini_api_keys()

    # Build context summary of current beats with explicit 1-indexed and 0-indexed labels
    beats_summary = []
    for card in session.beats:
        idx_1 = card.beat_index + 1
        idx_0 = card.beat_index
        dialogue_status = f'"{card.dialogue_text}"' if card.dialogue_text and card.dialogue_text.strip() else "None (Silent scene)"
        beats_summary.append(
            f"Scene {idx_1} (target_beat={idx_0}, duration={card.duration_seconds}s): Current Dialogue: {dialogue_status} | Camera: {card.camera_motion} | Visual: '{card.visual_prompt[:120]}...'"
        )
    beats_context = "\n".join(beats_summary)

    # Build recent conversation history context
    recent_history = []
    if getattr(session, "chat_history", None):
        for msg in session.chat_history[-6:]:
            role = "Creator" if msg.sender == "user" else "Copilot"
            recent_history.append(f"{role}: {msg.text}")
    history_context = "\n".join(recent_history) if recent_history else "None (start of session)"

    prompt_payload = f"""Current Storyboard Context:
Canvas Aspect Ratio: {session.aspect_ratio}
{beats_context}

Recent Conversation History:
{history_context}

Creator Instruction:
"{user_message}"

Generate your response in the required JSON format:
"""

    if os.environ.get("TEST_MODE") != "1":
        if keys:
            from google import genai
            from google.genai import types
            from core.models import resolve_llm_model

            primary_model = resolve_llm_model("gemini-3.8-flash")
            for api_key in keys:
                try:
                    client = genai.Client(api_key=api_key)
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            client.models.generate_content,
                            model=primary_model,
                            contents=prompt_payload,
                            config=types.GenerateContentConfig(
                                system_instruction=_DIRECTOR_SYSTEM_INSTRUCTION,
                                response_mime_type="application/json",
                                temperature=0.2,
                            ),
                        ),
                        timeout=10.0,
                    )

                    raw_text = response.text or "{}"
                    parsed = json.loads(raw_text)
                    reply = parsed.get("reply", "Updated the storyboard according to your notes.")
                    delta = parsed.get("delta")
                    return reply, delta
                except Exception as e:
                    masked = api_key[:6] + "..." if len(api_key) > 6 else "***"
                    print(f"Gemini director chat key ({masked}) model {primary_model} error: {e}. Cascading...")

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
                    p_resp = await asyncio.wait_for(
                        asyncio.to_thread(requests.post, p_url, json=p_payload, headers=p_headers, timeout=10.0),
                        timeout=10.0
                    )
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
    norm_msg = re.sub(r"['’`]", "", lower_msg)

    # Aspect ratio detection
    if "9:16" in user_message or "vertical" in norm_msg or "short" in norm_msg or "reel" in norm_msg:
        return "Switched the studio canvas to 9:16 vertical shorts format.", {
            "action": "CHANGE_ASPECT_RATIO",
            "new_value": "9:16"
        }
    elif "16:9" in user_message or "widescreen" in norm_msg or "horizontal" in norm_msg or "youtube" in norm_msg:
        return "Switched the studio canvas to 16:9 widescreen format.", {
            "action": "CHANGE_ASPECT_RATIO",
            "new_value": "16:9"
        }

    # Detect dialogue removal / clearing intent
    is_dialogue_removal = any(k in norm_msg for k in [
        "dont want narrator", "no narrator", "remove narrator",
        "without narrator", "no dialogue", "remove dialogue", "clear dialogue",
        "silent", "mute dialogue", "dont want dialogue",
        "dont want that", "dont want"
    ])

    # Extract target beat indices (supports multiple scenes e.g. "beat 2 and 3", "scene 1, 2, 3")
    target_indices = []
    # Check for "all"
    if any(k in norm_msg for k in ["all clips", "these clips", "all beats", "all scenes", "every scene"]):
        target_indices = list(range(len(session.beats)))
    else:
        # Search for explicit mentions like "beat 2 and 3", "scene 2 and 3", "2 and 3"
        pair_match = re.search(r"(?:beat|scene|shot)?\s*#?(\d+)\s*(?:and|&|,)\s*(?:beat|scene|shot)?\s*#?(\d+)", lower_msg)
        if pair_match:
            n1, n2 = int(pair_match.group(1)), int(pair_match.group(2))
            for n in (n1, n2):
                idx = max(0, n - 1) if n > 0 else 0
                if idx < len(session.beats) and idx not in target_indices:
                    target_indices.append(idx)
        else:
            matches = re.findall(r"(?:beat|scene|shot)\s*#?(\d+)", lower_msg)
            if matches:
                for m in matches:
                    n = int(m)
                    idx = max(0, n - 1) if n > 0 else 0
                    if idx < len(session.beats) and idx not in target_indices:
                        target_indices.append(idx)

    # If no explicit indices were found, check single number
    if not target_indices:
        match_single = re.search(r"\b(\d+)\b", lower_msg)
        if match_single:
            n = int(match_single.group(1))
            idx = max(0, n - 1) if n > 0 else 0
            if idx < len(session.beats):
                target_indices.append(idx)

    if is_dialogue_removal:
        if not target_indices:
            # Default to all beats if user says "i don't want narrator in these clips"
            target_indices = list(range(len(session.beats)))

        deltas = [
            {"action": "UPDATE_BEAT", "target_beat": idx, "field": "dialogue", "new_value": ""}
            for idx in target_indices
        ]
        scene_names = ", ".join([f"Scene {i + 1}" for i in target_indices])
        return f"Removed narration dialogue from {scene_names} (set to silent atmospheric audio).", deltas

    target_idx = target_indices[0] if target_indices else 0

    # Check for image re-roll or generation request (strictly for image creation)
    if any(k in lower_msg for k in ["reroll", "re-roll", "regenerate image", "new image", "render image", "generate artwork", "redraw"]):
        return f"Re-generating keyframe artwork for Scene {target_idx + 1}.", {
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

    # Dialogue update with quoted or explicit text
    if "dialogue" in lower_msg or "say" in lower_msg or "line" in lower_msg:
        quoted = re.search(r'["\u201c]([^"\u201d]+)["\u201d]', user_message)
        new_dialogue = quoted.group(1).strip() if quoted else user_message
        return f"Updated the dialogue for Scene {target_idx + 1}.", {
            "action": "UPDATE_BEAT",
            "target_beat": target_idx,
            "field": "dialogue",
            "new_value": new_dialogue
        }

    # Storyboard Restructuring / Rewrite detection (e.g. "rewrite whole story in 2 clips of 15s", "change to 2 clips of 15s")
    if any(k in norm_msg for k in ["rewrite", "restructure", "recreate", "extend story in", "2 clips", "2 scenes", "3 clips", "4 clips"]):
        target_clip_match = re.search(r"(?:in|into|to|with)\s*(\d+)\s*(?:clips|scenes|beats|shots)", norm_msg)
        if target_clip_match:
            target_num = int(target_clip_match.group(1))
        else:
            all_clip_matches = re.findall(r"(\d+)\s*(?:clips|scenes|beats|shots)", norm_msg)
            target_num = int(all_clip_matches[-1]) if all_clip_matches else 2

        dur_match = re.search(r"(\d+)\s*(?:s|sec|seconds)", norm_msg)
        target_dur = float(dur_match.group(1)) if dur_match else 15.0

        base_prompt = session.concept_prompt or (session.beats[0].visual_prompt if session.beats else "Cinematic film scene")
        new_beats = []
        for i in range(target_num):
            act_name = "Opening Hook & High-Action Climax" if i == 0 else "Kinetic Resolution & Dramatic Close" if i == target_num - 1 else f"Act {i + 1}"
            new_beats.append({
                "beat_index": i,
                "visual_prompt": f"{base_prompt}. Scene {i + 1} - {act_name}. Ultra-detailed cinematic composition.",
                "dialogue": "",
                "duration_seconds": target_dur,
                "camera_motion": "slow_push_in" if i == 0 else "pan_right"
            })
        return f"Restructured your story into {target_num} extended scenes ({target_dur}s each, total {int(target_num * target_dur)}s runtime).", {
            "action": "RESTRUCTURE_STORYBOARD",
            "num_beats": target_num,
            "duration_per_beat": target_dur,
            "beats": new_beats
        }

    # Conversational intent without direct visual edit request
    if any(k in norm_msg for k in ["how", "why", "what", "can you", "think", "is it", "opinion", "idea", "vision", "hello", "hi", "hey"]) and not any(k in norm_msg for k in ["darker", "lighter", "rain", "sun", "color", "camera", "angle", "make", "change", "set"]):
        return "I understand your vision. We can shape the story pacing, mood, and shots to match your style. What specific adjustment or scene flow would you like to explore next?", None

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
