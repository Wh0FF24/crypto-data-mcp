"""
CoinGecko API client with built-in caching and rate limit handling.

Uses the free CoinGecko API (no key required). Implements a 60-second
TTL cache to minimize API calls and stay within the free tier rate limit
of ~10-30 requests/minute.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from .token_map import resolve_symbol, SYMBOL_TO_ID

logger = logging.getLogger(__name__)

BASE_URL = "https://api.coingecko.com/api/v3"
CACHE_TTL = 60  # seconds
REQUEST_TIMEOUT = 15  # seconds


@dataclass
class CacheEntry:
    data: Any
    timestamp: float


@dataclass
class CoinGeckoClient:
    """Async CoinGecko API client with caching."""

    _cache: dict[str, CacheEntry] = field(default_factory=dict)
    _client: httpx.AsyncClient | None = field(default=None, repr=False)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "crypto-data-mcp/0.1.0",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _cache_get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() - entry.timestamp > CACHE_TTL:
            del self._cache[key]
            return None
        return entry.data

    def _cache_set(self, key: str, data: Any) -> None:
        self._cache[key] = CacheEntry(data=data, timestamp=time.time())

    async def _request(
        self, path: str, params: dict | None = None, _retries: int = 2
    ) -> Any:
        """Make a GET request with caching, retry on rate limit, and error handling."""
        cache_key = f"{path}:{params}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        client = await self._get_client()
        try:
            resp = await client.get(path, params=params)
        except httpx.TimeoutException:
            raise CoinGeckoError("Request timed out. CoinGecko may be slow — try again.")
        except httpx.ConnectError:
            raise CoinGeckoError("Could not connect to CoinGecko. Check your network.")

        if resp.status_code == 429:
            if _retries > 0:
                logger.info("Rate limited by CoinGecko, backing off for 5s...")
                await asyncio.sleep(5)
                return await self._request(path, params, _retries=_retries - 1)
            raise CoinGeckoError(
                "CoinGecko rate limit hit. The free tier allows ~10-30 requests/minute. "
                "Wait a moment and try again."
            )
        if resp.status_code == 404:
            raise CoinGeckoError("Resource not found on CoinGecko. Check the token symbol.")
        if resp.status_code != 200:
            raise CoinGeckoError(
                f"CoinGecko API returned status {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        self._cache_set(cache_key, data)
        return data

    async def resolve_id(self, symbol: str) -> str:
        """
        Resolve a symbol to a CoinGecko ID.
        First checks the local map, then falls back to CoinGecko search.
        """
        local = resolve_symbol(symbol)
        if local:
            return local

        # Fallback: search CoinGecko
        data = await self._request("/search", params={"query": symbol})
        coins = data.get("coins", [])
        if not coins:
            raise CoinGeckoError(
                f"Could not find token '{symbol}'. Try the full name (e.g., 'bitcoin') "
                f"or check the symbol."
            )

        # Try exact symbol match first
        upper = symbol.upper().strip()
        for coin in coins:
            if coin.get("symbol", "").upper() == upper:
                return coin["id"]

        # Fall back to first result
        return coins[0]["id"]

    async def resolve_ids(self, symbols: list[str]) -> dict[str, str]:
        """Resolve multiple symbols, returning {original_symbol: coingecko_id}."""
        result = {}
        for s in symbols:
            result[s] = await self.resolve_id(s)
        return result

    async def get_price(self, symbol: str, currency: str = "usd") -> dict:
        """Get current price data for a single token."""
        coin_id = await self.resolve_id(symbol)
        cur = currency.lower()

        data = await self._request(
            "/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": cur,
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_last_updated_at": "true",
            },
        )

        if coin_id not in data:
            raise CoinGeckoError(f"No price data returned for '{symbol}'.")

        coin_data = data[coin_id]
        return {
            "symbol": symbol.upper(),
            "coingecko_id": coin_id,
            "currency": cur,
            "price": coin_data.get(cur),
            "price_change_24h_pct": coin_data.get(f"{cur}_24h_change"),
            "market_cap": coin_data.get(f"{cur}_market_cap"),
            "volume_24h": coin_data.get(f"{cur}_24h_vol"),
            "last_updated_at": coin_data.get("last_updated_at"),
        }

    async def get_prices(self, symbols: list[str], currency: str = "usd") -> list[dict]:
        """Get current price data for multiple tokens in a single API call."""
        id_map = await self.resolve_ids(symbols)
        coin_ids = list(id_map.values())
        cur = currency.lower()

        data = await self._request(
            "/simple/price",
            params={
                "ids": ",".join(coin_ids),
                "vs_currencies": cur,
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_last_updated_at": "true",
            },
        )

        results = []
        for original_symbol, coin_id in id_map.items():
            coin_data = data.get(coin_id, {})
            results.append({
                "symbol": original_symbol.upper(),
                "coingecko_id": coin_id,
                "currency": cur,
                "price": coin_data.get(cur),
                "price_change_24h_pct": coin_data.get(f"{cur}_24h_change"),
                "market_cap": coin_data.get(f"{cur}_market_cap"),
                "volume_24h": coin_data.get(f"{cur}_24h_vol"),
                "last_updated_at": coin_data.get("last_updated_at"),
            })

        return results

    async def get_market_overview(self) -> dict:
        """Get market overview: top movers, BTC dominance, total market cap."""
        # Global data
        global_data = await self._request("/global")
        gd = global_data.get("data", {})

        # Top gainers and losers from market data
        markets = await self._request(
            "/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": "100",
                "page": "1",
                "sparkline": "false",
                "price_change_percentage": "24h",
            },
        )

        # Sort by 24h change to find gainers/losers
        with_change = [
            m for m in markets
            if m.get("price_change_percentage_24h") is not None
        ]
        sorted_by_change = sorted(
            with_change,
            key=lambda x: x["price_change_percentage_24h"],
            reverse=True,
        )

        def format_mover(m: dict) -> dict:
            return {
                "symbol": (m.get("symbol") or "").upper(),
                "name": m.get("name"),
                "price": m.get("current_price"),
                "change_24h_pct": round(m.get("price_change_percentage_24h", 0), 2),
            }

        top_gainers = [format_mover(m) for m in sorted_by_change[:5]]
        top_losers = [format_mover(m) for m in sorted_by_change[-5:]]
        top_losers.reverse()

        total_market_cap = gd.get("total_market_cap", {}).get("usd")
        total_volume = gd.get("total_volume", {}).get("usd")
        btc_dominance = gd.get("market_cap_percentage", {}).get("btc")
        eth_dominance = gd.get("market_cap_percentage", {}).get("eth")
        active_cryptos = gd.get("active_cryptocurrencies")

        # Fear & Greed index (separate free API)
        fear_greed = await self._get_fear_greed()

        return {
            "total_market_cap_usd": total_market_cap,
            "total_volume_24h_usd": total_volume,
            "btc_dominance_pct": round(btc_dominance, 2) if btc_dominance else None,
            "eth_dominance_pct": round(eth_dominance, 2) if eth_dominance else None,
            "active_cryptocurrencies": active_cryptos,
            "fear_greed_index": fear_greed,
            "top_gainers_24h": top_gainers,
            "top_losers_24h": top_losers,
        }

    async def _get_fear_greed(self) -> dict | None:
        """Fetch the Fear & Greed index from alternative.me."""
        try:
            client = await self._get_client()
            resp = await client.get(
                "https://api.alternative.me/fng/",
                params={"limit": "1"},
            )
            if resp.status_code == 200:
                data = resp.json()
                entry = data.get("data", [{}])[0]
                return {
                    "value": int(entry.get("value", 0)),
                    "classification": entry.get("value_classification", "Unknown"),
                }
        except Exception:
            logger.debug("Failed to fetch Fear & Greed index", exc_info=True)
        return None

    async def get_token_info(self, symbol: str) -> dict:
        """Get detailed information about a token."""
        coin_id = await self.resolve_id(symbol)

        data = await self._request(
            f"/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            },
        )

        market = data.get("market_data", {})
        desc_raw = data.get("description", {}).get("en", "")
        # Truncate long descriptions
        description = desc_raw[:500] + "..." if len(desc_raw) > 500 else desc_raw

        return {
            "symbol": (data.get("symbol") or symbol).upper(),
            "name": data.get("name"),
            "coingecko_id": coin_id,
            "description": description,
            "market_cap_rank": data.get("market_cap_rank"),
            "website": (data.get("links", {}).get("homepage", [None]) or [None])[0],
            "categories": data.get("categories", []),
            "current_price_usd": market.get("current_price", {}).get("usd"),
            "market_cap_usd": market.get("market_cap", {}).get("usd"),
            "fully_diluted_valuation_usd": market.get("fully_diluted_valuation", {}).get("usd"),
            "total_volume_usd": market.get("total_volume", {}).get("usd"),
            "ath_usd": market.get("ath", {}).get("usd"),
            "ath_date": market.get("ath_date", {}).get("usd"),
            "ath_change_pct": market.get("ath_change_percentage", {}).get("usd"),
            "atl_usd": market.get("atl", {}).get("usd"),
            "atl_date": market.get("atl_date", {}).get("usd"),
            "atl_change_pct": market.get("atl_change_percentage", {}).get("usd"),
            "circulating_supply": market.get("circulating_supply"),
            "total_supply": market.get("total_supply"),
            "max_supply": market.get("max_supply"),
            "price_change_24h_pct": market.get("price_change_percentage_24h"),
            "price_change_7d_pct": market.get("price_change_percentage_7d"),
            "price_change_30d_pct": market.get("price_change_percentage_30d"),
        }

    async def get_historical_prices(
        self, symbol: str, days: int = 7, currency: str = "usd"
    ) -> dict:
        """Get historical price data as [timestamp, price] pairs."""
        coin_id = await self.resolve_id(symbol)
        cur = currency.lower()

        data = await self._request(
            f"/coins/{coin_id}/market_chart",
            params={
                "vs_currency": cur,
                "days": str(days),
            },
        )

        prices = data.get("prices", [])

        return {
            "symbol": symbol.upper(),
            "coingecko_id": coin_id,
            "currency": cur,
            "days": days,
            "data_points": len(prices),
            "prices": prices,  # [[timestamp_ms, price], ...]
        }


class CoinGeckoError(Exception):
    """Raised when a CoinGecko API call fails."""
    pass
