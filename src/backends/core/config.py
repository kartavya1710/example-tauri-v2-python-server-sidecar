"""Shared configuration for MCP servers"""

mcp_config = {
    # "mcp-gsuite": {
    #     "command": "uv",
    #     "args": [
    #         "--directory",
    #         "C:/Users/Vidhi/mcp-gsuite",
    #         "run",
    #         "mcp-gsuite",
    #     ],
    #     "env": {
    #         "GSUITE_USER": "vidhi@miraiminds.co"
    #     }
    # },
    # "mcp-telegram": {
    #     "command": "uv",
    #     "args": [
    #         "--directory",
    #         "C:/Users/Vidhi/mcp-telegram",
    #         "run",
    #         "mcp-telegram",
    #     ],
    #     "env": {
    #         "TELEGRAM_API_ID": "20259102",
    #         "TELEGRAM_API_HASH": "5331c756850f1b0315ee7dcaf489e65d",
    #     },
    # },
    # "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
    # # "cron-server": {
    # #     "command": "python",
    # #     "args": ["src/server/cron-server.py"],
    # #     "env": None
    # # },
    "tavily-search": {
            "command": "C:/Users/Vidhi/example-tauri-v2-python-server-sidecar/venv/Scripts/python.exe",
            "args": [
                "C:/Users/Vidhi/example-tauri-v2-python-server-sidecar/src/backends/server/mcp-server-tavily/src/server.py"
            ],
            "env": None,
    },
    "binance-server": {
            "command": "C:/Users/Vidhi/example-tauri-v2-python-server-sidecar/venv/Scripts/python.exe",
            "args": [
                "C:/Users/Vidhi/example-tauri-v2-python-server-sidecar/src/backends/server/binance-server.py"
            ],
            "env": None,
    },
}
