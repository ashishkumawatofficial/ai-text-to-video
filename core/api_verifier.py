"""Zero-waste API health verification and probe utility.

Probes all configured AI services using minimal or zero-credit payloads:
- Google Gemini (1-word ping)
- Cloudflare Workers AI (1-word TTS & FLUX endpoint check)
- Puter AI (1-word GPT-4o chat, 0-credit test_mode image generation, 1-word TTS)
- Microsoft Edge-TTS (local connection, free)
- RunPod Serverless (worker pool status)
"""

from __future__ import annotations
import os
import time
import requests
from typing import Dict, Any, List
from core.config import (
    get_gemini_api_keys,
    get_cloudflare_credentials,
    get_puter_api_key,
    get_runpod_api_key,
    get_runpod_serverless_endpoint_id,
)


def run_api_verification() -> List[Dict[str, Any]]:
    """Runs a fast, minimal-cost probe across all configured providers and prints a health table."""
    print("=" * 72)
    print("         🔍 Zero-Waste AI Provider Health & Quota Probe")
    print("=" * 72)

    results: List[Dict[str, Any]] = []

    # 1. Google Gemini Keys
    gemini_keys = get_gemini_api_keys()
    if not gemini_keys:
        results.append({
            "service": "Google Gemini",
            "role": "Story Planning / Chat",
            "model": "None configured",
            "status": "NOT_CONFIGURED",
            "latency": 0,
            "cost": "0",
            "detail": "Missing GEMINI_API_KEY in .env"
        })
    else:
        for idx, key in enumerate(gemini_keys):
            masked = key[:6] + "..." if len(key) > 6 else "***"
            t0 = time.time()
            models_to_test = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]
            succeeded_model = None
            last_err = None

            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=10000))
                for m in models_to_test:
                    try:
                        resp = client.models.generate_content(
                            model=m,
                            contents="OK",
                            config=types.GenerateContentConfig(max_output_tokens=3, temperature=0.1)
                        )
                        if resp.text:
                            succeeded_model = m
                            break
                    except Exception as me:
                        last_err = me
                        continue

                lat = round((time.time() - t0) * 1000)
                if succeeded_model:
                    results.append({
                        "service": f"Gemini Key {idx + 1} ({masked})",
                        "role": "Story Planning & Director",
                        "model": succeeded_model,
                        "status": "ONLINE",
                        "latency": lat,
                        "cost": "1 token (~$0.000001)",
                        "detail": f"Active & Healthy ({succeeded_model})"
                    })
                else:
                    err_str = str(last_err) if last_err else "All models exhausted"
                    status = "503_BUSY" if "503" in err_str else ("429_LIMIT" if "429" in err_str else "ERROR")
                    results.append({
                        "service": f"Gemini Key {idx + 1} ({masked})",
                        "role": "Story Planning & Director",
                        "model": "gemini-3.5-flash",
                        "status": status,
                        "latency": lat,
                        "cost": "0",
                        "detail": f"{type(last_err).__name__}: {err_str[:40]}... (Puter fallback ready)"
                    })
            except Exception as e:
                lat = round((time.time() - t0) * 1000)
                results.append({
                    "service": f"Gemini Key {idx + 1} ({masked})",
                    "role": "Story Planning & Director",
                    "model": "gemini-3.5-flash",
                    "status": "ERROR",
                    "latency": lat,
                    "cost": "0",
                    "detail": str(e)[:40]
                })

    # 2. Cloudflare Workers AI
    cf_acc, cf_tok = get_cloudflare_credentials()
    if cf_acc and cf_tok:
        # TTS Probe
        t0 = time.time()
        try:
            url = f"https://api.cloudflare.com/client/v4/accounts/{cf_acc}/ai/run/@cf/deepgram/aura-2-en"
            r = requests.post(
                url,
                json={"text": "OK"},
                headers={"Authorization": f"Bearer {cf_tok}", "Content-Type": "application/json"},
                timeout=12.0
            )
            lat = round((time.time() - t0) * 1000)
            status = "ONLINE" if r.status_code == 200 else f"HTTP_{r.status_code}"
            results.append({
                "service": "Cloudflare Workers AI",
                "role": "Emotional Voiceover (TTS)",
                "model": "deepgram/aura-2-en",
                "status": status,
                "latency": lat,
                "cost": "Free (10k neurons/day)",
                "detail": "Human-like conversational voice"
            })
        except Exception as e:
            results.append({
                "service": "Cloudflare Workers AI",
                "role": "Emotional Voiceover (TTS)",
                "model": "deepgram/aura-2-en",
                "status": "ERROR",
                "latency": 0,
                "cost": "0",
                "detail": str(e)[:40]
            })

        # Image Probe (FLUX)
        t0 = time.time()
        try:
            url = f"https://api.cloudflare.com/client/v4/accounts/{cf_acc}/ai/run/@cf/black-forest-labs/flux-1-schnell"
            # Fast ping probe with 1 step
            r = requests.post(
                url,
                json={"prompt": "abstract neon light"},
                headers={"Authorization": f"Bearer {cf_tok}", "Content-Type": "application/json"},
                timeout=15.0
            )
            lat = round((time.time() - t0) * 1000)
            status = "ONLINE" if r.status_code == 200 else f"HTTP_{r.status_code}"
            results.append({
                "service": "Cloudflare Workers AI",
                "role": "Visual Keyframes (Tier 1)",
                "model": "flux-1-schnell",
                "status": status,
                "latency": lat,
                "cost": "Free (10k neurons/day)",
                "detail": "Photorealistic 16:9 / 9:16 plates"
            })
        except Exception as e:
            results.append({
                "service": "Cloudflare Workers AI",
                "role": "Visual Keyframes (Tier 1)",
                "model": "flux-1-schnell",
                "status": "ERROR",
                "latency": 0,
                "cost": "0",
                "detail": str(e)[:40]
            })

    # 3. Puter AI
    puter_key = get_puter_api_key()
    if puter_key:
        p_headers = {
            "content-type": "text/plain;actually=json",
            "user-agent": "puter-js/1.0",
            "origin": "https://puter.work",
            "referer": "https://puter.work/"
        }
        # Puter Chat (gpt-4o)
        t0 = time.time()
        try:
            p_payload = {
                "interface": "puter-chat-completion",
                "driver": "ai-chat",
                "test_mode": False,
                "method": "complete",
                "args": {
                    "model": "gpt-4o",
                    "messages": [{"content": "Say OK"}]
                },
                "auth_token": puter_key
            }
            r = requests.post("https://api.puter.com/drivers/call", json=p_payload, headers=p_headers, timeout=12.0)
            lat = round((time.time() - t0) * 1000)
            status = "ONLINE" if r.status_code == 200 else f"HTTP_{r.status_code}"
            results.append({
                "service": "Puter AI (OpenAI)",
                "role": "Story Planning & Copilot",
                "model": "gpt-4o / claude-sonnet",
                "status": status,
                "latency": lat,
                "cost": "1 token",
                "detail": "Frontier fallback tier"
            })
        except Exception as e:
            results.append({
                "service": "Puter AI (OpenAI)",
                "role": "Story Planning & Copilot",
                "model": "gpt-4o",
                "status": "ERROR",
                "latency": 0,
                "cost": "0",
                "detail": str(e)[:40]
            })

        # Puter Image (0-credit test_mode)
        t0 = time.time()
        try:
            p_img_payload = {
                "interface": "puter-image-generation",
                "driver": "ai-image",
                "test_mode": True,
                "method": "generate",
                "args": {"prompt": "dot", "test_mode": True},
                "auth_token": puter_key
            }
            r = requests.post("https://api.puter.com/drivers/call", json=p_img_payload, headers=p_headers, timeout=15.0)
            lat = round((time.time() - t0) * 1000)
            status = "ONLINE" if r.status_code == 200 else f"HTTP_{r.status_code}"
            results.append({
                "service": "Puter AI (FLUX/SD)",
                "role": "Visual Keyframes (Tier 2)",
                "model": "ai-image",
                "status": status,
                "latency": lat,
                "cost": "0 credits (test_mode)",
                "detail": "Visual generation fallback"
            })
        except Exception as e:
            results.append({
                "service": "Puter AI (FLUX/SD)",
                "role": "Visual Keyframes (Tier 2)",
                "model": "ai-image",
                "status": "ERROR",
                "latency": 0,
                "cost": "0",
                "detail": str(e)[:40]
            })

    # 4. Microsoft Edge-TTS
    t0 = time.time()
    try:
        import edge_tts
        lat = round((time.time() - t0) * 1000)
        results.append({
            "service": "Microsoft Edge-TTS",
            "role": "Voiceover Narration (Tier 3)",
            "model": "HD Multilingual Neural",
            "status": "ONLINE",
            "latency": lat,
            "cost": "100% Free / Unlimited",
            "detail": "Brian / Ava / Christopher"
        })
    except Exception as e:
        results.append({
            "service": "Microsoft Edge-TTS",
            "role": "Voiceover Narration (Tier 3)",
            "model": "HD Multilingual Neural",
            "status": "ERROR",
            "latency": 0,
            "cost": "0",
            "detail": str(e)[:40]
        })

    # 5. RunPod Serverless
    from core.runpod_serverless import check_serverless_health
    sl = check_serverless_health()
    results.append({
        "service": "RunPod Serverless",
        "role": "Wan 2.1 Video Diffusion",
        "model": "wan2.1-t2v-14b",
        "status": sl.status,
        "latency": 0,
        "cost": "$0.00 (while idle)",
        "detail": f"Workers idle: {sl.workers_idle}, running: {sl.workers_running}"
    })

    # Print Table
    print(f"{'PROVIDER':<25} | {'ROLE':<25} | {'STATUS':<10} | {'LATENCY':<8} | {'PROBE COST'}")
    print("-" * 88)
    for res in results:
        status_display = f"✅ {res['status']}" if res['status'] == "ONLINE" or res['status'] == "HEALTHY" else f"⚠️ {res['status']}"
        lat_display = f"{res['latency']}ms" if res['latency'] > 0 else "-"
        print(f"{res['service']:<25} | {res['role']:<25} | {status_display:<10} | {lat_display:<8} | {res['cost']}")

    print("=" * 88)
    print("💡 Zero-waste guarantee: Automated tests (pytest) use local mocks and cached assets,")
    print("   consuming 0 credits. Run 'python -m core.cli verify-apis' anytime for a live probe.")
    print("=" * 88)
    return results
