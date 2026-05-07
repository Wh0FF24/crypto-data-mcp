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
        "Real-time cryptocurrency data powered by CoinGecko (free, no API key). "
        "Use get_price for a single token, get_prices for a batch. "
        "Use get_market_overview for broad market context (BTC dominance, fear/greed, top movers). "
        "Use get_token_info for fundamentals (ATH, supply, description). "
        "Use get_historical_prices for charting or trend analysis. "
        "All tools accept common symbols (BTC, ETH, SOL) or CoinGecko IDs."
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
        "Get the current price, 24-hour change, market cap, and trading volume for a "
        "single cryptocurrency token. Use this when you need live market data for one "
        "token. For multiple tokens, prefer get_prices to avoid redundant API calls. "
        "Accepts common symbols (BTC, ETH, SOL, DOGE) or full CoinGecko IDs "
        "(bitcoin, ethereum). Prices update approximately every 60 seconds due to "
        "server-side caching. Returns an error JSON if the token is not found or the "
        "CoinGecko API is temporarily unavailable."
    )
)
async def get_price(symbol: str, currency: str = "usd") -> str:
    """
    Get current price for a single cryptocurrency token.

    Args:
        symbol: Token symbol such as BTC, ETH, SOL, or a CoinGecko coin ID
            such as bitcoin or ethereum. Case-insensitive. If the symbol is
            ambiguous, the highest market-cap match is used.
        currency: Fiat or crypto quote currency as an ISO 4217 code or CoinGecko
            currency ID such as usd, eur, gbp, jpy, btc, or eth. Defaults to usd.

    Returns:
        JSON object with fields: symbol (uppercased), coingecko_id, currency,
        price (float or null), price_change_24h_pct, market_cap,
        volume_24h, last_updated_at (Unix timestamp).
        Returns an error object if the token is not found or the API fails.
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
        "Get current prices for up to 50 cryptocurrency tokens in a single request. "
        "Always prefer this over multiple get_price calls when you need data for two "
        "or more tokens. It batches them into one CoinGecko API call and is "
        "significantly more efficient. Returns the same fields as get_price for each "
        "token. Symbols that cannot be resolved are omitted from the result without "
        "failing the entire batch. Accepts common symbols (BTC, ETH, SOL) or "
        "CoinGecko IDs. Returns an error if the list is empty or exceeds 50 tokens."
    )
)
async def get_prices(symbols: list[str], currency: str = "usd") -> str:
    """
    Get current prices for multiple cryptocurrency tokens in a single API call.

    Args:
        symbols: List of token symbols or CoinGecko IDs such as BTC, ETH, SOL.
            Maximum 50 items. Unresolvable symbols are omitted without error.
        currency: Fiat or crypto quote currency such as usd, eur, gbp, jpy, btc,
            or eth. Defaults to usd.

    Returns:
        JSON array where each element has symbol, coingecko_id, currency, price,
        price_change_24h_pct, market_cap, volume_24h, last_updated_at.
        Returns an error object if the list is empty or exceeds 50 items.
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
        "Get a broad snapshot of the entire cryptocurrency market. Returns total market "
        "capitalisation, 24-hour trading volume, Bitcoin dominance percentage, Ethereum "
        "dominance percentage, total number of active cryptocurrencies, the Fear and Greed "
        "index (0-100, where 0 is Extreme Fear and 100 is Extreme Greed), the top 5 "
        "gainers and top 5 losers by 24-hour price change. Use this tool when you want "
        "macro context before analysing individual tokens, or when the user asks about "
        "overall market sentiment, bull/bear conditions, or which tokens are moving most. "
        "Takes no parameters. Data is sourced from CoinGecko global endpoints and the "
        "Alternative.me Fear and Greed index."
    )
)
async def get_market_overview() -> str:
    """
    Get a comprehensive snapshot of the cryptocurrency market.

    Returns:
        JSON object with fields: total_market_cap_usd, total_volume_24h_usd,
        btc_dominance_pct, eth_dominance_pct, active_cryptocurrencies,
        fear_greed_index (object with value 0-100 and classification string, or null),
        top_gainers_24h (list of up to 5 tokens with symbol/name/price/change_24h_pct),
        top_losers_24h (list of up to 5 tokens with symbol/name/price/change_24h_pct).
        Returns an error object if the CoinGecko API is unavailable.
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
        "Get detailed fundamental information about a cryptocurrency token, including "
        "its project description, official website, market cap rank, all-time high and "
        "all-time low prices with dates, circulating and total supply, fully diluted "
        "valuation, and price change percentages over 24 hours, 7 days, and 30 days. "
        "Use this when you need more than just a current price, for example for "
        "fundamental analysis, understanding a token history, or answering questions "
        "about supply dynamics. For just the current price or market cap, use "
        "get_price instead. Accepts common symbols (BTC, ETH) or CoinGecko IDs. "
        "Project descriptions are truncated to 500 characters."
    )
)
async def get_token_info(symbol: str) -> str:
    """
    Get detailed fundamental information about a cryptocurrency token.

    Args:
        symbol: Token symbol such as BTC, ETH, SOL, or a CoinGecko coin ID
            such as bitcoin or ethereum. Case-insensitive.

    Returns:
        JSON object with fields: symbol, name, coingecko_id, description (truncated
        to 500 chars), market_cap_rank, website, categories, current_price_usd,
        market_cap_usd, total_volume_usd, fully_diluted_valuation_usd, ath_usd,
        ath_date, ath_change_pct, atl_usd, atl_date, atl_change_pct,
        circulating_supply, total_supply, max_supply, price_change_24h_pct,
        price_change_7d_pct, price_change_30d_pct.
        Returns an error object if the token is not found or the API fails.
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
        "Get historical price data for a cryptocurrency over a specified number of days. "
        "Returns an ordered array of [timestamp_ms, price] pairs suitable for charting, "
        "trend analysis, backtesting, or computing metrics like volatility and drawdown. "
        "Data granularity varies automatically: 5-minute intervals for 1 day, hourly "
        "for 2-90 days, and daily for 91-365 days. Use this when you need a price "
        "series rather than a single current price. For just the current price, use "
        "get_price instead. Valid range: 1 to 365 days. Accepts common symbols or "
        "CoinGecko IDs. The server retries once with a 5-second backoff on rate limits."
    )
)
async def get_historical_prices(
    symbol: str, days: int = 7, currency: str = "usd"
) -> str:
    """
    Get historical price data as a time series for charting or analysis.

    Args:
        symbol: Token symbol such as BTC, ETH, SOL, or a CoinGecko coin ID.
            Case-insensitive.
        days: Number of days of price history. Must be between 1 and 365. Default
            is 7. Granularity: 1 day gives ~288 five-minute points; 2-90 days give
            hourly points; 91-365 days give one point per day.
        currency: Quote currency such as usd, eur, gbp, or btc. Defaults to usd.

    Returns:
        JSON object with fields: symbol, coingecko_id, currency, days, data_points
        (count of returned price entries), prices (list of [timestamp_ms, price]
        pairs in ascending chronological order where timestamp_ms is a Unix timestamp
        in milliseconds and price is a float in the requested currency).
        Returns an error object if days is out of range, the token is not found,
        or the CoinGecko API is unavailable.
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
