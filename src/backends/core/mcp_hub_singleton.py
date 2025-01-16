from core.mcp_client import MCPHub
from core.config import mcp_config

_mcp_hub_instance = None

def get_mcp_hub():
    global _mcp_hub_instance
    if _mcp_hub_instance is None:
        _mcp_hub_instance = MCPHub()
    return _mcp_hub_instance

async def initialize_mcp_hub():
    hub = get_mcp_hub()
    for server_name, config in mcp_config.items():
        await hub.connect_to_server(server_name, config)
