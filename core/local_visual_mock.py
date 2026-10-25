"""Local Visual Mock Keyframe Engine (Zero-GPU Fallback).

Generates high-definition keyframe artwork for storyboard beats when cloud GPU
diffusion (ComfyUI) is unavailable or unconfigured, ensuring 100% visual uptime.
"""

from __future__ import annotations
import os
import re
import hashlib
import urllib.parse
import requests
from typing import Optional
from PIL import Image, ImageDraw, ImageFont


DEFAULT_TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs", "temp"))


def get_cached_keyframe_path(prompt: str, cache_dir: str = DEFAULT_TEMP_DIR) -> str:
    """Returns a deterministic cache file path based on prompt hash."""
    os.makedirs(cache_dir, exist_ok=True)
    prompt_hash = hashlib.sha256(prompt.strip().lower().encode("utf-8")).hexdigest()[:12]
    return os.path.join(cache_dir, f"keyframe_{prompt_hash}.jpg")


def create_procedural_cinematic_plate(
    prompt: str,
    scene_id: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920
) -> str:
    """Creates a high-aesthetic procedural 9:16 vertical keyframe using PIL."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    image = Image.new("RGB", (width, height), (15, 23, 42)) # Deep slate background
    draw = ImageDraw.Draw(image)

    # Deterministic palette based on prompt content
    lower = prompt.lower()
    if any(k in lower for k in ["rain", "cyber", "neon", "detective"]):
        top_color = (10, 15, 30)
        bot_color = (2, 6, 23)
        accent_color = (56, 189, 248) # Cyan/electric blue
        secondary_accent = (168, 85, 247) # Purple neon
    elif any(k in lower for k in ["fight", "action", "combat", "strike"]):
        top_color = (30, 10, 15)
        bot_color = (15, 3, 5)
        accent_color = (239, 68, 68) # Red
        secondary_accent = (245, 158, 11) # Amber
    else:
        top_color = (18, 18, 28)
        bot_color = (5, 5, 12)
        accent_color = (234, 179, 8) # Warm gold
        secondary_accent = (59, 130, 246) # Blue

    # 1. Smooth Vertical Gradient
    for y in range(height):
        r = int(top_color[0] + (bot_color[0] - top_color[0]) * (y / height))
        g = int(top_color[1] + (bot_color[1] - top_color[1]) * (y / height))
        b = int(top_color[2] + (bot_color[2] - top_color[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 2. Atmospheric Depth & Perspective Lines
    center_x = width // 2
    horizon_y = height // 2
    for x in range(0, width + 1, 120):
        alpha_val = int(25 + 20 * (x / width))
        line_color = (accent_color[0] // 3, accent_color[1] // 3, accent_color[2] // 3)
        draw.line([(center_x, horizon_y), (x, height)], fill=line_color, width=2)
        draw.line([(center_x, horizon_y), (x, 0)], fill=(20, 25, 40), width=1)

    # 3. Horizon Glow Line
    draw.line([(0, horizon_y), (width, horizon_y)], fill=accent_color, width=3)

    # 4. Central Aesthetic Pill / Badge
    pill_w = 700
    pill_h = 160
    pill_x0 = center_x - pill_w // 2
    pill_y0 = horizon_y - pill_h // 2
    draw.rounded_rectangle(
        [pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h],
        radius=24,
        fill=(15, 23, 42),
        outline=accent_color,
        width=3
    )

    # 5. Scene Label and Summary Text
    badge_text = f"SCENE: {scene_id.upper()}"
    draw.text((center_x, horizon_y - 25), badge_text, fill=accent_color, anchor="mm")

    # Short excerpt from prompt
    clean_prompt = prompt.replace("\n", " ")
    if len(clean_prompt) > 45:
        clean_prompt = clean_prompt[:42] + "..."
    draw.text((center_x, horizon_y + 25), clean_prompt, fill=(241, 245, 249), anchor="mm")

    # 6. Save image
    image.save(output_path, "JPEG", quality=90)
    return output_path


def generate_local_keyframe(
    prompt: str,
    scene_id: str,
    output_path: Optional[str] = None,
    width: int = 1080,
    height: int = 1920,
    use_online_synthesis: bool = True,
    force_refresh: bool = False,
) -> str:
    """Generates or retrieves a high-definition 9:16 keyframe image for a scene beat."""
    dest = output_path or get_cached_keyframe_path(prompt)
    if force_refresh and os.path.exists(dest):
        try:
            os.remove(dest)
        except Exception:
            pass

    if not force_refresh and os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return dest

    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)

    # Attempt high-quality online synthesis (skipped in TEST_MODE to preserve credits/quotas)
    if use_online_synthesis and os.environ.get("TEST_MODE") != "1":
        # Tier 1: Cloudflare Workers AI FLUX.1-schnell (Frontier speed & photorealism)
        from core.config import get_cloudflare_credentials
        cf_acc, cf_tok = get_cloudflare_credentials()
        if cf_acc and cf_tok and not cf_tok.startswith("your_") and len(cf_tok.strip()) > 10:
            try:
                import base64, io
                cf_url = f"https://api.cloudflare.com/client/v4/accounts/{cf_acc}/ai/run/@cf/black-forest-labs/flux-1-schnell"
                cf_headers = {
                    "Authorization": f"Bearer {cf_tok}",
                    "Content-Type": "application/json"
                }
                cf_resp = requests.post(cf_url, headers=cf_headers, json={"prompt": prompt}, timeout=30.0)
                if cf_resp.status_code == 200:
                    cf_data = cf_resp.json()
                    b64 = cf_data.get("result", {}).get("image")
                    if b64:
                        raw_bytes = base64.b64decode(b64)
                        with Image.open(io.BytesIO(raw_bytes)) as img:
                            target_ratio = width / height
                            img_ratio = img.width / img.height
                            if img_ratio > target_ratio:
                                new_w = int(img.height * target_ratio)
                                left = (img.width - new_w) // 2
                                img = img.crop((left, 0, left + new_w, img.height))
                            else:
                                new_h = int(img.width / target_ratio)
                                top = (img.height - new_h) // 2
                                img = img.crop((0, top, img.width, top + new_h))
                            resized = img.resize((width, height), Image.Resampling.LANCZOS)
                            resized.save(dest, "JPEG", quality=92)
                        return dest
            except Exception:
                pass

        # Tier 2: Puter AI FLUX Image Generation (High-resolution, free starter quota)
        from core.config import get_puter_api_key
        puter_key = get_puter_api_key()
        if puter_key and len(puter_key) > 10:
            try:
                import base64, io
                p_url = "https://api.puter.com/drivers/call"
                p_headers = {
                    "content-type": "text/plain;actually=json",
                    "user-agent": "puter-js/1.0",
                    "origin": "https://puter.work",
                    "referer": "https://puter.work/",
                }
                p_payload = {
                    "interface": "puter-image-generation",
                    "driver": "ai-image",
                    "test_mode": False,
                    "method": "generate",
                    "args": {"prompt": prompt},
                    "auth_token": puter_key,
                }
                p_resp = requests.post(p_url, json=p_payload, headers=p_headers, timeout=35.0)
                if p_resp.status_code == 200:
                    p_data = p_resp.json()
                    res_str = p_data.get("result")
                    if res_str and "base64," in res_str:
                        raw_bytes = base64.b64decode(res_str.split("base64,")[-1])
                        with Image.open(io.BytesIO(raw_bytes)) as img:
                            target_ratio = width / height
                            img_ratio = img.width / img.height
                            if img_ratio > target_ratio:
                                new_w = int(img.height * target_ratio)
                                left = (img.width - new_w) // 2
                                img = img.crop((left, 0, left + new_w, img.height))
                            else:
                                new_h = int(img.width / target_ratio)
                                top = (img.height - new_h) // 2
                                img = img.crop((0, top, img.width, top + new_h))
                            resized = img.resize((width, height), Image.Resampling.LANCZOS)
                            resized.save(dest, "JPEG", quality=92)
                        return dest
            except Exception:
                pass

        # Tier 3: Together AI FLUX.1-schnell
        from core.config import get_together_api_key
        together_key = get_together_api_key()
        if together_key and not together_key.startswith("your_") and len(together_key.strip()) > 10:
            try:
                import base64
                w = (width // 32) * 32
                h = (height // 32) * 32
                t_url = "https://api.together.xyz/v1/images/generations"
                t_headers = {
                    "Authorization": f"Bearer {together_key.strip()}",
                    "Content-Type": "application/json"
                }
                t_payload = {
                    "model": "black-forest-labs/FLUX.1-schnell",
                    "prompt": prompt,
                    "width": max(256, min(w, 1440)),
                    "height": max(256, min(h, 1440)),
                    "steps": 4,
                    "n": 1,
                    "response_format": "b64_json"
                }
                t_resp = requests.post(t_url, headers=t_headers, json=t_payload, timeout=25.0)
                if t_resp.status_code == 200:
                    data = t_resp.json()
                    b64 = data["data"][0]["b64_json"]
                    img_bytes = base64.b64decode(b64)
                    with open(dest, "wb") as f:
                        f.write(img_bytes)
                    return dest
            except Exception:
                pass

        # 2. Tier 2: Public zero-cost synthesis gateway (Pollinations)
        try:
            # Clean prompt to focus on visual subject and avoid URL routing conflicts
            clean = re.sub(r"\b(?:vertical|horizontal|widescreen|\d+:\d+|portrait|framing|perspective|blocking)\b", "", prompt, flags=re.IGNORECASE)
            clean = re.sub(r"[:/,\.\n]+", " ", clean).strip()
            clean_words = clean.split()[:28]
            clean_text = " ".join(clean_words) if clean_words else prompt[:120]
            
            aspect_tag = "vertical portrait 9:16" if height > width else "widescreen landscape 16:9"
            query_prompt = f"cinematic shot, {aspect_tag}, {clean_text}"
            encoded_prompt = urllib.parse.quote(query_prompt)

            # Clean URL without query params (seed/nologo trigger 402 FREE_LIMIT on public gateway)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Referer": "https://pollinations.ai/",
            }
            
            resp = requests.get(url, headers=headers, timeout=25.0)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(dest, "wb") as f:
                    f.write(resp.content)
                try:
                    with Image.open(dest) as img:
                        if img.size != (width, height):
                            target_ratio = width / height
                            img_ratio = img.width / img.height
                            if img_ratio > target_ratio:
                                new_w = int(img.height * target_ratio)
                                left = (img.width - new_w) // 2
                                img = img.crop((left, 0, left + new_w, img.height))
                            else:
                                new_h = int(img.width / target_ratio)
                                top = (img.height - new_h) // 2
                                img = img.crop((0, top, img.width, top + new_h))

                            resized = img.resize((width, height), Image.Resampling.LANCZOS)
                            resized.save(dest, "JPEG", quality=92)
                except Exception:
                    pass
                return dest
        except Exception:
            # Fall back to procedural generation gracefully on timeout/offline
            pass

    # Save procedural fallback to a separate preview path so it doesn't corrupt canonical cache
    fallback_dest = dest.replace(".jpg", f"_{scene_id}_fallback.jpg") if dest.endswith(".jpg") else f"{dest}_{scene_id}_fallback.jpg"
    return create_procedural_cinematic_plate(
        prompt=prompt,
        scene_id=scene_id,
        output_path=fallback_dest,
        width=width,
        height=height
    )

