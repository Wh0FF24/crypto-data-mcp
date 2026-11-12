"""
Regression tests for the MCP server wiring.

These run offline. They guard the class of breakage where an MCP SDK upgrade
changes the server API and this module stops importing — a failure that
otherwise only surfaces when a user actually starts the server.
"""

import pytest

from crypto_data_mcp import server

EXPECTED_TOOLS = {
    "get_price",
    "get_prices",
    "get_market_overview",
    "get_token_info",
    "get_historical_prices",
}


class TestServerWiring:
    def test_server_object_exists(self):
        assert server.mcp is not None

    def test_entry_point_is_callable(self):
        assert callable(server.main)

    @pytest.mark.asyncio
    async def test_all_tools_registered(self):
        names = {tool.name for tool in await server.mcp.list_tools()}
        assert names == EXPECTED_TOOLS

    @pytest.mark.asyncio
    async def test_every_tool_has_a_description(self):
        for tool in await server.mcp.list_tools():
            assert tool.description, f"{tool.name} is missing a description"
