"""
Mapping of common cryptocurrency ticker symbols to CoinGecko API IDs.

Includes the top 50 tokens by market cap plus commonly searched tokens.
CoinGecko uses slug-style IDs (e.g., "bitcoin") rather than ticker symbols
(e.g., "BTC"), so this mapping is necessary for user-friendly lookups.
"""

# Symbol (uppercase) -> CoinGecko ID
SYMBOL_TO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "USDC": "usd-coin",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "TRX": "tron",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "POL": "matic-network",
    "SHIB": "shiba-inu",
    "TON": "the-open-network",
    "DAI": "dai",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "XLM": "stellar",
    "LEO": "leo-token",
    "OKB": "okb",
    "ETC": "ethereum-classic",
    "XMR": "monero",
    "FIL": "filecoin",
    "HBAR": "hedera-hashgraph",
    "APT": "aptos",
    "ARB": "arbitrum",
    "MNT": "mantle",
    "CRO": "crypto-com-chain",
    "VET": "vechain",
    "MKR": "maker",
    "OP": "optimism",
    "NEAR": "near",
    "AAVE": "aave",
    "GRT": "the-graph",
    "ALGO": "algorand",
    "QNT": "quant-network",
    "FTM": "fantom",
    "SAND": "the-sandbox",
    "MANA": "decentraland",
    "THETA": "theta-token",
    "AXS": "axie-infinity",
    "ICP": "internet-computer",
    "RENDER": "render-token",
    "INJ": "injective-protocol",
    "IMX": "immutable-x",
    "SUI": "sui",
    "SEI": "sei-network",
    "STX": "blockstack",
    "PEPE": "pepe",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "FLOKI": "floki",
    "FET": "fetch-ai",
    "RNDR": "render-token",
    "TIA": "celestia",
    "JUP": "jupiter-exchange-solana",
    "WLD": "worldcoin-wld",
    "PYTH": "pyth-network",
    "JTO": "jito-governance-token",
    "STRK": "starknet",
    "W": "wormhole",
    "ENA": "ethena",
    "PENDLE": "pendle",
    "EIGEN": "eigenlayer",
    "TRUMP": "official-trump",
}

# Reverse lookup: CoinGecko ID -> symbol
ID_TO_SYMBOL: dict[str, str] = {v: k for k, v in SYMBOL_TO_ID.items()}


def resolve_symbol(symbol: str) -> str | None:
    """
    Resolve a ticker symbol to a CoinGecko ID.

    Tries exact match first, then case-insensitive match.
    Returns None if the symbol is not in the local mapping.
    """
    upper = symbol.upper().strip()
    if upper in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[upper]

    # Maybe the user passed a CoinGecko ID directly (e.g., "bitcoin")
    lower = symbol.lower().strip()
    if lower in ID_TO_SYMBOL:
        return lower

    return None
