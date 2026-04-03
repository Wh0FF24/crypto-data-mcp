"""
Crypto Data MCP Server

A Model Context Protocol server that provides real-time cryptocurrency
data from CoinGecko. Designed for use with Claude Code, Cursor, and
other MCP-compatible AI tools.

Built by Whoff Agents — https://whoffagents.com
"""

import json
import logging

from mcp.server import FastMCP

from .coingecko import CoinGeckoClient, CoinGeckoError

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "crypto-data-mcp",
    instructions=(
        "Real-time cryptocurrency data for AI coding tools. "
        "Prices, market data, token info, and historical charts "
        "powered by CoinGecko. Built by Whoff Agents (whoffagents.com)."
    ),
)

client = CoinGeckoClient()


def _format_result(data: dict | list) -> str:
    """Format result as indented JSON for readability."""
    return json.dumps(data, indent=2, default=str)


def _error_result(message: str) -> str:
    """Format an error message as JSON."""
    return json.dumps({"error": message})


@mcp.tool(
    description=(
        "Get the current price for a cryptocurrency token. "
        "Returns price, 24h change %, market cap, and 24h volume. "
        "Accepts common symbols (BTC, ETH, SOL) or CoinGecko IDs (bitcoin, ethereum)."
    )
)
async def get_price(symbol: str, currency: str = "usd") -> str:
    """
    Get current price for a cryptocurrency.

    Args:
        symbol: Token symbol (e.g., "BTC", "ETH", "SOL") or CoinGecko ID
        currency: Quote currency (default: "usd"). Supports usd, eur, gbp, etc.

    Returns:
        JSON with price, 24h change %, market cap, and volume.
    """
    try:
        result = await client.get_price(symbol, currency)
        return _format_result(result)
    except CoinGeckoError as e:
        return _error_result(str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_price")
        return _error_result(f"Unexpected error: {e}")


@mcp.tool(
    description=(
        "Get current prices for multiple cryptocurrency tokens in a single call. "
        "More efficient than calling get_price multiple times. "
        "Returns price, 24h change %, market cap, and volume for each token."
    )
)
async def get_prices(symbols: list[str], currency: str = "usd") -> str:
    """
    Get current prices for multiple tokens at once.

    Args:
        symbols: List of token symbols (e.g., ["BTC", "ETH", "SOL"])
        currency: Quote currency (default: "usd")

    Returns:
        JSON array of price data for each token.
    """
    if not symbols:
        return _error_result("No symbols provided. Pass a list like ['BTC', 'ETH'].")
    if len(symbols) > 50:
        return _error_result("Maximum 50 symbols per request.")

    try:
        result = await client.get_prices(symbols, currency)
        return _format_result(result)
    except CoinGeckoError as e:
        return _error_result(str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_prices")
        return _error_result(f"Unexpected error: {e}")


@mcp.tool(
    description=(
        "Get a market overview: top gainers and losers (24h), total crypto market cap, "
        "BTC dominance %, ETH dominance %, and the Fear & Greed index. "
        "No parameters required."
    )
)
async def get_market_overview() -> str:
    """
    Get crypto market overview.

    Returns:
        JSON with total market cap, BTC/ETH dominance, fear/greed index,
        top 5 gainers and top 5 losers by 24h price change.
    """
    try:
        result = await client.get_market_overview()
        return _format_result(result)
    except CoinGeckoError as e:
        return _error_result(str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_market_overview")
        return _error_result(f"Unexpected error: {e}")


@mcp.tool(
    description=(
        "Get detailed information about a cryptocurrency token. "
        "Returns name, description, website, market cap rank, ATH/ATL, "
        "supply info, and price changes over multiple timeframes."
    )
)
async def get_token_info(symbol: str) -> str:
    """
    Get detailed token information.

    Args:
        symbol: Token symbol (e.g., "BTC", "ETH") or CoinGecko ID

    Returns:
        JSON with name, description, website, rank, ATH, ATL, supply, and price changes.
    """
    try:
        result = await client.get_token_info(symbol)
        return _format_result(result)
    except CoinGeckoError as e:
        return _error_result(str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_token_info")
        return _error_result(f"Unexpected error: {e}")


@mcp.tool(
    description=(
        "Get historical price data for a cryptocurrency. "
        "Returns an array of [timestamp_ms, price] pairs. "
        "Useful for charting, analysis, and identifying trends."
    )
)
async def get_historical_prices(
    symbol: str, days: int = 7, currency: str = "usd"
) -> str:
    """
    Get historical price data.

    Args:
        symbol: Token symbol (e.g., "BTC", "ETH") or CoinGecko ID
        days: Number of days of history (1, 7, 14, 30, 90, 180, 365, max). Default: 7
        currency: Quote currency (default: "usd")

    Returns:
        JSON with array of [timestamp_ms, price] data points.
        Granularity: 5-min for 1 day, hourly for 1-90 days, daily for 90+ days.
    """
    if days < 1:
        return _error_result("Days must be at least 1.")
    if days > 365:
        return _error_result("Maximum 365 days. Use days=365 for a full year.")

    try:
        result = await client.get_historical_prices(symbol, days, currency)
        return _format_result(result)
    except CoinGeckoError as e:
        return _error_result(str(e))
    except Exception as e:
        logger.exception("Unexpected error in get_historical_prices")
        return _error_result(f"Unexpected error: {e}")


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
