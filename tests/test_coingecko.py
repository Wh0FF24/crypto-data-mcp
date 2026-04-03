"""
Tests for the CoinGecko client and token mapping.

These tests hit the live CoinGecko API (free tier). Run sparingly
to avoid rate limits. For CI, consider mocking httpx responses.
"""

import pytest
from crypto_data_mcp.token_map import resolve_symbol, SYMBOL_TO_ID
from crypto_data_mcp.coingecko import CoinGeckoClient, CoinGeckoError


# --- Token Map Tests (no network) ---

class TestTokenMap:
    def test_resolve_btc(self):
        assert resolve_symbol("BTC") == "bitcoin"

    def test_resolve_eth_lowercase(self):
        assert resolve_symbol("eth") == "ethereum"

    def test_resolve_sol_mixed_case(self):
        assert resolve_symbol("Sol") == "solana"

    def test_resolve_coingecko_id_directly(self):
        assert resolve_symbol("bitcoin") == "bitcoin"

    def test_resolve_unknown_returns_none(self):
        assert resolve_symbol("NOTAREALTOKEN123") is None

    def test_top_tokens_present(self):
        expected = ["BTC", "ETH", "SOL", "USDT", "USDC", "BNB", "XRP", "ADA", "DOGE", "AVAX"]
        for sym in expected:
            assert sym in SYMBOL_TO_ID, f"{sym} missing from SYMBOL_TO_ID"

    def test_mapping_has_at_least_50_entries(self):
        assert len(SYMBOL_TO_ID) >= 50


# --- CoinGecko Client Tests (live API) ---

class TestCoinGeckoClient:
    @pytest.fixture
    async def cg(self):
        client = CoinGeckoClient()
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_get_price_btc(self, cg):
        result = await cg.get_price("BTC")
        assert result["symbol"] == "BTC"
        assert result["currency"] == "usd"
        assert result["price"] is not None
        assert result["price"] > 0
        assert result["market_cap"] is not None
        assert result["volume_24h"] is not None

    @pytest.mark.asyncio
    async def test_get_price_eth_eur(self, cg):
        result = await cg.get_price("ETH", currency="eur")
        assert result["symbol"] == "ETH"
        assert result["currency"] == "eur"
        assert result["price"] > 0

    @pytest.mark.asyncio
    async def test_get_prices_multiple(self, cg):
        results = await cg.get_prices(["BTC", "ETH", "SOL"])
        assert len(results) == 3
        symbols = [r["symbol"] for r in results]
        assert "BTC" in symbols
        assert "ETH" in symbols
        assert "SOL" in symbols

    @pytest.mark.asyncio
    async def test_get_token_info(self, cg):
        result = await cg.get_token_info("ETH")
        assert result["symbol"] == "ETH"
        assert result["name"] == "Ethereum"
        assert result["market_cap_rank"] is not None
        assert result["ath_usd"] is not None
        assert result["circulating_supply"] is not None

    @pytest.mark.asyncio
    async def test_get_historical_prices(self, cg):
        result = await cg.get_historical_prices("BTC", days=7)
        assert result["symbol"] == "BTC"
        assert result["days"] == 7
        assert result["data_points"] > 0
        assert len(result["prices"]) > 0
        # Each entry is [timestamp_ms, price]
        assert len(result["prices"][0]) == 2

    @pytest.mark.asyncio
    async def test_get_market_overview(self, cg):
        result = await cg.get_market_overview()
        assert result["total_market_cap_usd"] is not None
        assert result["total_market_cap_usd"] > 0
        assert result["btc_dominance_pct"] is not None
        assert len(result["top_gainers_24h"]) > 0
        assert len(result["top_losers_24h"]) > 0

    @pytest.mark.asyncio
    async def test_resolve_id_search_fallback(self, cg):
        # "render-token" is in the map under RENDER and RNDR
        coin_id = await cg.resolve_id("RENDER")
        assert coin_id == "render-token"

    @pytest.mark.asyncio
    async def test_invalid_symbol_raises(self, cg):
        with pytest.raises(CoinGeckoError):
            await cg.get_price("THISISNOTAREALCOIN999")

    @pytest.mark.asyncio
    async def test_caching(self, cg):
        # First call populates cache
        r1 = await cg.get_price("BTC")
        # Second call should use cache (same data, no API call)
        r2 = await cg.get_price("BTC")
        assert r1["price"] == r2["price"]
        assert len(cg._cache) > 0
