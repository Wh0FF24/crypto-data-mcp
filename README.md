# crypto-data-mcp

[![CI](https://github.com/Wh0FF24/crypto-data-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/Wh0FF24/crypto-data-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/crypto-data-mcp)](https://pypi.org/project/crypto-data-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Real-time cryptocurrency data for AI coding tools. An MCP server that gives Claude Code, Cursor, and other MCP-compatible tools access to live prices, market data, token info, and historical charts -- powered by CoinGecko.

Built by [Whoff Agents](https://whoffagents.com).

## Installation

### Fastest: one-liner with uvx (no install needed)

```bash
uvx crypto-data-mcp
```

### Install from PyPI

```bash
pip install crypto-data-mcp
# or
uv add crypto-data-mcp
```

### From source

```bash
git clone https://github.com/Wh0FF24/crypto-data-mcp.git
cd crypto-data-mcp
uv sync
```

## Usage with Claude Code

Add to your Claude Code MCP config at `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "crypto-data": {
      "command": "uvx",
      "args": ["crypto-data-mcp"]
    }
  }
}
```

Or if installed via pip/uv:

```json
{
  "mcpServers": {
    "crypto-data": {
      "command": "crypto-data-mcp"
    }
  }
}
```

Then in Claude Code, you can ask things like:
- "What's the current price of Bitcoin?"
- "Compare ETH, SOL, and AVAX prices"
- "Show me the crypto market overview"
- "Get me 30 days of BTC price history"
- "What's Ethereum's all-time high?"

## Available Tools

### `get_price`

Get the current price for a single token.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | string | *required* | Token symbol (BTC, ETH, SOL) or CoinGecko ID |
| `currency` | string | `"usd"` | Quote currency (usd, eur, gbp, etc.) |

**Example response:**
```json
{
  "symbol": "BTC",
  "coingecko_id": "bitcoin",
  "currency": "usd",
  "price": 67250.00,
  "price_change_24h_pct": -1.82,
  "market_cap": 1325000000000,
  "volume_24h": 28500000000,
  "last_updated_at": 1712000000
}
```

### `get_prices`

Get prices for multiple tokens in one call. More efficient than calling `get_price` repeatedly.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `symbols` | list[string] | *required* | List of symbols (max 50) |
| `currency` | string | `"usd"` | Quote currency |

**Example response:**
```json
[
  { "symbol": "BTC", "price": 67250.00, "price_change_24h_pct": -1.82 },
  { "symbol": "ETH", "price": 2064.00, "price_change_24h_pct": -2.15 },
  { "symbol": "SOL", "price": 79.00, "price_change_24h_pct": -3.10 }
]
```

### `get_market_overview`

Get a crypto market overview with top movers, market cap, and sentiment.

**Parameters:** None required.

**Example response:**
```json
{
  "total_market_cap_usd": 2390000000000,
  "total_volume_24h_usd": 85000000000,
  "btc_dominance_pct": 55.95,
  "eth_dominance_pct": 11.20,
  "active_cryptocurrencies": 17887,
  "fear_greed_index": { "value": 35, "classification": "Fear" },
  "top_gainers_24h": [ "..." ],
  "top_losers_24h": [ "..." ]
}
```

### `get_token_info`

Get detailed information about a token including description, supply, ATH/ATL, and multi-timeframe price changes.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | string | *required* | Token symbol or CoinGecko ID |

**Example response:**
```json
{
  "symbol": "ETH",
  "name": "Ethereum",
  "description": "Ethereum is a decentralized...",
  "market_cap_rank": 2,
  "website": "https://www.ethereum.org/",
  "current_price_usd": 2064.00,
  "ath_usd": 4946.05,
  "ath_date": "2021-11-10T14:24:19.604Z",
  "atl_usd": 0.432979,
  "circulating_supply": 120500000,
  "total_supply": 120500000,
  "max_supply": null,
  "price_change_24h_pct": -2.15,
  "price_change_7d_pct": -5.30,
  "price_change_30d_pct": -12.40
}
```

### `get_historical_prices`

Get historical price data as timestamp/price pairs for charting and analysis.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `symbol` | string | *required* | Token symbol or CoinGecko ID |
| `days` | int | `7` | Days of history (1-365) |
| `currency` | string | `"usd"` | Quote currency |

**Granularity:** 5-minute for 1 day, hourly for 1-90 days, daily for 90+ days.

**Example response:**
```json
{
  "symbol": "BTC",
  "currency": "usd",
  "days": 7,
  "data_points": 168,
  "prices": [
    [1711900000000, 67100.00],
    [1711903600000, 67250.00]
  ]
}
```

## Supported Tokens

The server includes a built-in mapping for 70+ popular tokens (BTC, ETH, SOL, USDT, USDC, BNB, XRP, ADA, DOGE, AVAX, and many more). For tokens not in the built-in map, it automatically searches CoinGecko to resolve the symbol.

## Data Source

All data comes from the [CoinGecko API](https://www.coingecko.com/en/api) (free tier). The server includes:

- **60-second caching** to reduce API calls
- **Automatic retry** with backoff on rate limits
- **Graceful error handling** for network issues and invalid inputs

The free CoinGecko tier allows approximately 10-30 requests per minute.

## Development

```bash
# Install dependencies
uv sync

# Run tests (uses live CoinGecko API -- may hit rate limits)
uv run pytest tests/ -v

# Run the server directly
uv run crypto-data-mcp
```

## Pricing

**Free tier** -- This open-source MCP server with CoinGecko data is free.

**Pro tier** -- Coming soon at **$19/mo** with:
- Real-time WebSocket price feeds
- DEX data (Uniswap, Raydium, Jupiter)
- On-chain analytics
- Wallet and portfolio tracking
- Higher rate limits
- Priority support

Visit [whoffagents.com](https://whoffagents.com) for updates.

## License

MIT
