from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from binance.client import Client
from binance.exceptions import BinanceAPIException
import asyncio
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Binance client setup
# BINANCE_API_KEY = "0otYys2DEQNWxEfTtOBalDge4mMZziK6tFU4w9SEltiXs4EqxCB7886iT0Az7MJM"
# BINANCE_API_SECRET = "OkmWop5BvOFjzb3pSZ1PT8llLGoUVm2xsatiywK5V227BBKe14H6ikkgPavLOgoc"
BINANCE_API_KEY="P8YiNgFBw5LSdb5uADEMkJQnekAaTaasXGwG84AhNuZQ8SNu6nAbbPRYXygE57sw"
BINANCE_API_SECRET="ixMC9NtK2It7SS91pdHVCvj8G4lbll6112Q0EFnmcLlWEKsgAnRWZdD2bjg9laqc"

if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    raise ValueError("Binance API key and secret must be set in environment variables")

binance_client = Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)

# Create a server instance
server = Server("binance-server")
binance_client.API_URL = 'https://testnet.binance.vision/api'


# Supported trading pairs
SUPPORTED_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"]


# Add tools
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List tools for interacting with the Binance API."""
    return [
        types.Tool(
            name="get_price",
            description="Get the current price of a trading pair",
            inputSchema={
                "type": "object",
                "required": ["symbol"],
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair symbol (e.g., BTCUSDT)",
                    }
                },
            },
        ),
        types.Tool(
            name="get_balance",
            description="Get your Binance account balances",
            inputSchema={"type": "object", "properties": {}},  # No input required
        ),
        types.Tool(
            name="place_market_order",
            description="Place a market order",
            inputSchema={
                "type": "object",
                "required": ["symbol", "side", "quantity"],
                "properties": {
                    "symbol": {"type": "string", "description": "Trading pair symbol (e.g., BTCUSDT)"},
                    "side": {"type": "string", "enum": ["BUY", "SELL"], "description": "Order side (BUY or SELL)"},
                    "quantity": {"type": "number", "description": "Order quantity"},
                },
            },
        ),
        types.Tool(
            name="get_order_history",
            description="Get the order history for a trading pair",
            inputSchema={
                "type": "object",
                "required": ["symbol"],
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair symbol (e.g., BTCUSDT)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent orders to fetch",
                        "default": 50,
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def handle_tool_call(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls by interacting with Binance."""
    global monitoring

    try:
        if name == "get_price":
            symbol = arguments["symbol"].upper()
            ticker = binance_client.get_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])
            return [
                types.TextContent(
                    type="text",
                    text=f"The current price of {symbol} is ${price:,.2f}.",
                )
            ]

        elif name == "get_balance":
            account = binance_client.get_account()
            balances = [
                {
                    "asset": balance["asset"],
                    "free": float(balance["free"]),
                    "locked": float(balance["locked"]),
                }
                for balance in account["balances"]
                if float(balance["free"]) > 0 or float(balance["locked"]) > 0
            ]
            balance_text = "\n".join(
                [f"{b['asset']}: {b['free']} free, {b['locked']} locked" for b in balances]
            )
            if not balance_text:
                balance_text = "No assets found with non-zero balances"
            return [
                types.TextContent(
                    type="text",
                    text=f"Your account balances:\n{balance_text}",
                )
            ]

        elif name == "place_market_order":
            symbol = arguments["symbol"].upper()
            side = arguments["side"].upper()
            quantity = float(arguments["quantity"])
            order = binance_client.create_order(
                symbol=symbol,
                side=side,
                type=Client.ORDER_TYPE_MARKET,
                quantity=quantity,
            )
            return [
                types.TextContent(
                    type="text",
                    text=f"Market order placed: {order['status']} (Order ID: {order['orderId']}).",
                )
            ]

        elif name == "get_order_history":
            symbol = arguments["symbol"].upper()
            limit = int(arguments.get("limit", 50))  # Default to 50 orders
            orders = binance_client.get_all_orders(symbol=symbol, limit=limit)

            if not orders:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No order history found for {symbol}.",
                    )
                ]

            formatted_orders = [
                f"Order ID: {order['orderId']}, Side: {order['side']}, "
                f"Type: {order['type']}, Status: {order['status']}, "
                f"Price: {float(order['price']) if float(order['price']) > 0 else 'N/A'}, "
                f"Quantity: {order['origQty']}, Time: {datetime.fromtimestamp(order['time'] / 1000).isoformat()}"
                for order in orders
            ]

            order_text = "\n".join(formatted_orders)
            return [
                types.TextContent(
                    type="text",
                    text=f"Order history for {symbol}:\n{order_text}",
                )
            ]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except BinanceAPIException as e:
        return [
            types.TextContent(
                type="text",
                text=f"Binance API error: {str(e)}",
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}",
            )
        ]


async def run():
    """Run the server as STDIO."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="binance-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run())
