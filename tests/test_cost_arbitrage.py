"""Unit tests for real-time cost arbitrage and lowest-cost provider ranking."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from core.models import (
    ProviderId,
    ProviderPriceQuote,
    VideoGenerationModality,
)
from core.cost_arbitrage import CostArbitrageEngine


@pytest.fixture
def arbitrage_engine():
    return CostArbitrageEngine()


@pytest.mark.asyncio
async def test_cost_arbitrage_selects_cheapest_provider(arbitrage_engine):
    """Verifies that quotes from candidate providers are ranked and the lowest is selected."""
    # Mock candidate quotes
    mock_quotes = [
        ProviderPriceQuote(
            provider_id=ProviderId.FAL_AI,
            model_id="kling-v1.5",
            duration_sec=5.0,
            resolution="720p",
            rate_per_sec_usd=0.09,
            estimated_total_usd=0.45,
            is_available=True,
        ),
        ProviderPriceQuote(
            provider_id=ProviderId.APIDOT_AI,
            model_id="kling-v1.5",
            duration_sec=5.0,
            resolution="720p",
            rate_per_sec_usd=0.08,
            estimated_total_usd=0.40,
            is_available=True,
        ),
        ProviderPriceQuote(
            provider_id=ProviderId.KIE_AI,
            model_id="kling-v1.5",
            duration_sec=5.0,
            resolution="720p",
            rate_per_sec_usd=0.10,
            estimated_total_usd=0.50,
            is_available=True,
        ),
    ]

    with patch.object(arbitrage_engine, "fetch_all_quotes", new=AsyncMock(return_value=mock_quotes)):
        ranked_quotes = await arbitrage_engine.get_ranked_quotes("kling-v1.5", duration_sec=5.0)
        assert len(ranked_quotes) == 3
        # Lowest price should be APIDOT_AI ($0.40)
        assert ranked_quotes[0].provider_id == ProviderId.APIDOT_AI
        assert ranked_quotes[0].estimated_total_usd == 0.40
        assert ranked_quotes[0].is_cheapest is True
        # Second lowest should be FAL_AI ($0.45)
        assert ranked_quotes[1].provider_id == ProviderId.FAL_AI
        assert ranked_quotes[1].is_cheapest is False


@pytest.mark.asyncio
async def test_cost_arbitrage_respects_manual_override(arbitrage_engine):
    """Verifies that user manual provider override bypasses auto-cheapest selection."""
    mock_quotes = [
        ProviderPriceQuote(
            provider_id=ProviderId.APIDOT_AI,
            model_id="kling-v1.5",
            duration_sec=5.0,
            resolution="720p",
            rate_per_sec_usd=0.08,
            estimated_total_usd=0.40,
            is_available=True,
        ),
        ProviderPriceQuote(
            provider_id=ProviderId.FAL_AI,
            model_id="kling-v1.5",
            duration_sec=5.0,
            resolution="720p",
            rate_per_sec_usd=0.09,
            estimated_total_usd=0.45,
            is_available=True,
        ),
    ]

    with patch.object(arbitrage_engine, "fetch_all_quotes", new=AsyncMock(return_value=mock_quotes)):
        # User explicitly chooses FAL_AI
        chosen_quote = await arbitrage_engine.resolve_target_provider(
            "kling-v1.5",
            duration_sec=5.0,
            provider_override=ProviderId.FAL_AI
        )
        assert chosen_quote.provider_id == ProviderId.FAL_AI
        assert chosen_quote.estimated_total_usd == 0.45


@pytest.mark.asyncio
async def test_quote_caching_ttl(arbitrage_engine):
    """Verifies that quotes are cached in-memory and not refetched within TTL window."""
    arbitrage_engine.clear_cache()
    
    # Mock adapter's get_price_quote method
    sample_quote = ProviderPriceQuote(
        provider_id=ProviderId.FAL_AI,
        model_id="kling-v1.5",
        duration_sec=5.0,
        resolution="720p",
        rate_per_sec_usd=0.09,
        estimated_total_usd=0.45,
        is_available=True,
    )
    
    mock_adapter = AsyncMock()
    mock_adapter.get_price_quote.return_value = sample_quote
    
    with patch.object(arbitrage_engine, "get_adapter", return_value=mock_adapter):
        # First call: populates cache for 3 candidate providers
        await arbitrage_engine.get_ranked_quotes("kling-v1.5", duration_sec=5.0)
        initial_calls = mock_adapter.get_price_quote.call_count
        assert initial_calls > 0

        # Second call in rapid succession: should read from cache, no new adapter calls
        await arbitrage_engine.get_ranked_quotes("kling-v1.5", duration_sec=5.0)
        assert mock_adapter.get_price_quote.call_count == initial_calls


@pytest.mark.asyncio
async def test_pricing_reflects_model_versions():
    """Verifies that quotes reflect differences across model versions and generations."""
    from core.providers.fal_provider import FalProvider
    from core.providers.apidot_provider import ApidotProvider
    from core.providers.kie_provider import KieProvider

    fal = FalProvider(api_key="mock_key")
    apidot = ApidotProvider(api_key="mock_key")
    kie = KieProvider(api_key="mock_key")

    # 1. Kling 1.0 vs 1.5 vs 2.0 vs 2.5 vs 3.0
    q_kling_10 = await fal.get_price_quote("kling-v1.0", duration_sec=5.0)
    q_kling_15 = await fal.get_price_quote("kling-v1.5", duration_sec=5.0)
    q_kling_20 = await fal.get_price_quote("kling-v2.0", duration_sec=5.0)
    q_kling_25 = await fal.get_price_quote("kling-v2.5", duration_sec=5.0)
    q_kling_30 = await fal.get_price_quote("kling-v3.0", duration_sec=5.0)

    assert q_kling_10.estimated_total_usd < q_kling_15.estimated_total_usd
    assert q_kling_15.estimated_total_usd < q_kling_20.estimated_total_usd
    assert q_kling_20.estimated_total_usd < q_kling_25.estimated_total_usd
    assert q_kling_25.estimated_total_usd < q_kling_30.estimated_total_usd

    # 2. Runway Gen-2 vs Gen-3 Turbo vs Gen-3 Alpha
    q_rw_g2 = await kie.get_price_quote("runway-gen2", duration_sec=5.0)
    q_rw_turbo = await kie.get_price_quote("runway-gen3-turbo", duration_sec=5.0)
    q_rw_alpha = await kie.get_price_quote("runway-gen3-alpha", duration_sec=5.0)

    assert q_rw_g2.estimated_total_usd < q_rw_turbo.estimated_total_usd
    assert q_rw_turbo.estimated_total_usd < q_rw_alpha.estimated_total_usd

    # 3. Wan 2.1 1.3B (Fast) vs Wan 2.1 14B (HQ)
    q_wan_fast = await apidot.get_price_quote("wan-2.1-t2v-1.3b", duration_sec=5.0)
    q_wan_hq = await apidot.get_price_quote("wan-2.1", duration_sec=5.0)

    assert q_wan_fast.estimated_total_usd < q_wan_hq.estimated_total_usd

    # 4. Audio add-on pricing test
    q_kling_no_audio = await fal.get_price_quote("kling-v1.5", duration_sec=5.0, has_native_audio=False)
    q_kling_audio = await fal.get_price_quote("kling-v1.5", duration_sec=5.0, has_native_audio=True)
    assert q_kling_audio.estimated_total_usd > q_kling_no_audio.estimated_total_usd


@pytest.mark.asyncio
async def test_wan_3_and_new_model_profiles():
    """Verifies Wan 3.0, Kling 4.0, Veo 3.1, and Grok 1.5 registry profiles and native audio support."""
    from core.provider_registry import get_model_profile, get_providers_for_model
    from core.models import ProviderId

    # Wan 3.0 checks
    wan3 = get_model_profile("wan-3.0")
    assert wan3 is not None
    assert wan3.supports_native_audio is True
    assert wan3.hard_char_limit == 5000
    providers = get_providers_for_model("wan-3.0")
    assert ProviderId.FAL_AI in providers
    assert ProviderId.APIDOT_AI in providers
    assert ProviderId.KIE_AI in providers

    # Kling 4.0 checks
    kling4 = get_model_profile("kling-v4.0")
    assert kling4 is not None
    assert kling4.supports_native_audio is True

    # Veo 3.1 checks
    veo31 = get_model_profile("veo-3.1")
    assert veo31 is not None
    assert veo31.supports_native_audio is True

    # Grok Video 1.5 checks
    grok = get_model_profile("grok-video-1.5")
    assert grok is not None
    assert grok.supports_native_audio is True


@pytest.mark.asyncio
async def test_resolution_scaling_pricing():
    """Verifies that 480p, 720p, 1080p, and 4k resolutions dynamically scale rates across all providers."""
    from core.providers.fal_provider import FalProvider
    from core.providers.apidot_provider import ApidotProvider
    from core.providers.kie_provider import KieProvider

    providers = [FalProvider(), ApidotProvider(), KieProvider()]

    for p in providers:
        q_480p = await p.get_price_quote("kling-v1.5", duration_sec=5.0, resolution="480p")
        q_720p = await p.get_price_quote("kling-v1.5", duration_sec=5.0, resolution="720p")
        q_1080p = await p.get_price_quote("kling-v1.5", duration_sec=5.0, resolution="1080p")
        q_4k = await p.get_price_quote("kling-v1.5", duration_sec=5.0, resolution="4k")

        # 480p should be cheaper than 720p
        assert q_480p.rate_per_sec_usd < q_720p.rate_per_sec_usd
        # 1080p should be higher than 720p
        assert q_1080p.rate_per_sec_usd > q_720p.rate_per_sec_usd
        # 4k should be higher than 1080p
        assert q_4k.rate_per_sec_usd > q_1080p.rate_per_sec_usd
        # Estimated total should reflect the duration scaling
        assert q_4k.estimated_total_usd > q_1080p.estimated_total_usd > q_720p.estimated_total_usd > q_480p.estimated_total_usd


