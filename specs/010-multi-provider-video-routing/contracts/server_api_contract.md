# Web Studio & Backend Server API Contract

**Feature Branch**: `010-multi-provider-video-routing`
**Date**: 2026-10-25
**Interface**: `core/server.py` FastAPI REST Endpoints

This document specifies the REST API endpoints exposed to the Web Studio frontend for provider registry lookup, live quotes, rendering execution, extending, and upscaling.

---

## 1. Provider Registry & Link Bank

### `GET /api/providers/registry`
Returns the complete list of supported providers, official links bank, failure refund policies, and health statuses.

#### Response (200 OK):
```json
{
  "providers": [
    {
      "provider_id": "fal_ai",
      "name": "fal.ai",
      "official_docs_url": "https://fal.ai/docs",
      "pricing_docs_url": "https://fal.ai/pricing",
      "failure_billing_policy": "Zero-cost guarantee: 5xx server errors and queue time are strictly $0.00. Only 200 outputs are billed.",
      "zero_cost_on_failure": true,
      "is_configured": true,
      "supported_models_count": 8
    },
    {
      "provider_id": "apidot_ai",
      "name": "APIDot",
      "official_docs_url": "https://apidot.ai/docs",
      "pricing_docs_url": "https://apidot.ai/pricing",
      "failure_billing_policy": "Credit protection: Failed generation tasks are automatically spared from deduction or refunded.",
      "zero_cost_on_failure": true,
      "is_configured": true,
      "supported_models_count": 6
    },
    {
      "provider_id": "kie_ai",
      "name": "Kie.ai",
      "official_docs_url": "https://docs.kie.ai",
      "pricing_docs_url": "https://kie.ai",
      "failure_billing_policy": "Non-expiring credit pool; failed tasks are flagged and refunded via task monitor.",
      "zero_cost_on_failure": true,
      "is_configured": true,
      "supported_models_count": 5
    }
  ]
}
```

---

## 2. Models Catalog & Version Limits

### `GET /api/providers/models`
Returns the catalog of all supported models, version-specific character/token limits, and audio capabilities.

#### Response (200 OK):
```json
{
  "models": [
    {
      "model_id": "kling-v1.5",
      "display_name": "Kling 1.5 Pro",
      "family": "kling",
      "version": "1.5",
      "hard_char_limit": 3072,
      "safe_char_limit": 2500,
      "supports_native_audio": true,
      "supports_i2v": true,
      "supports_dual_frame": true,
      "supports_extend": true,
      "supported_providers": ["fal_ai", "apidot_ai", "kie_ai"]
    },
    {
      "model_id": "seedance-2.5",
      "display_name": "ByteDance Seedance 2.5",
      "family": "seedance",
      "version": "2.5",
      "hard_char_limit": 5000,
      "safe_char_limit": 1500,
      "supports_native_audio": true,
      "supports_i2v": true,
      "supports_dual_frame": true,
      "supports_extend": true,
      "supported_providers": ["kie_ai", "apidot_ai"]
    },
    {
      "model_id": "runway-gen3-turbo",
      "display_name": "Runway Gen-3 Alpha Turbo",
      "family": "runway",
      "version": "gen3-turbo",
      "hard_char_limit": 1000,
      "safe_char_limit": 800,
      "supports_native_audio": false,
      "supports_i2v": true,
      "supports_dual_frame": false,
      "supports_extend": true,
      "supported_providers": ["fal_ai", "kie_ai"]
    }
  ]
}
```

---

## 3. Real-Time Price Quotation & Arbitrage

### `POST /api/providers/quotes`
Calculates or fetches real-time quotes across all candidate providers for a given specification.

#### Request Body:
```json
{
  "model_id": "kling-v1.5",
  "duration_sec": 5.0,
  "resolution": "720p",
  "has_native_audio": true
}
```

#### Response (200 OK):
```json
{
  "model_id": "kling-v1.5",
  "recommended_provider": "apidot_ai",
  "quotes": [
    {
      "provider_id": "apidot_ai",
      "rate_per_sec_usd": 0.08,
      "estimated_total_usd": 0.40,
      "billing_unit": "per_second",
      "is_available": true,
      "is_cheapest": true
    },
    {
      "provider_id": "fal_ai",
      "rate_per_sec_usd": 0.09,
      "estimated_total_usd": 0.45,
      "billing_unit": "per_second",
      "is_available": true,
      "is_cheapest": false
    },
    {
      "provider_id": "kie_ai",
      "rate_per_sec_usd": 0.10,
      "estimated_total_usd": 0.50,
      "billing_unit": "per_second",
      "is_available": true,
      "is_cheapest": false
    }
  ]
}
```

---

## 4. Prompt Adaptation & Budget Compression

### `POST /api/providers/adapt-prompt`
Transforms a prompt to fit within target model character/token limits and injects audio tags if Audio is ON.

#### Request Body:
```json
{
  "raw_prompt": "A solitary cyberpunk detective in a trenchcoat walks cautiously through a neon-lit rain-slicked alleyway in Neo-Tokyo while gazing at hologram billboards.",
  "target_model_id": "runway-gen3-turbo",
  "modality": "i2v",
  "has_native_audio": true,
  "dialogue_text": "The signal was coming from here."
}
```

#### Response (200 OK):
```json
{
  "adapted_prompt": "Slow dolly-in. Detective walks through rainy alleyway, whispers: 'The signal was coming from here.' Rain patters on puddles, neon reflections flicker.",
  "original_length": 164,
  "adapted_length": 149,
  "target_limit": 1000,
  "is_within_limit": true
}
```

---

## 5. Render, Extend & Upscale Actions

### `POST /api/render/provider-job`
Submits a video rendering task to the selected or cheapest provider.

### `POST /api/render/extend-job`
Lengthens an existing video clip by +4s/+5s.

### `POST /api/render/upscale-job`
Triggers Topaz Video AI or Real-ESRGAN super-resolution upscaling up to 4K.
