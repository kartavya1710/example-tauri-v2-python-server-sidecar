# /// script
# dependencies = [
#   "mcp",
#   "requests",
#   "python-dotenv"
# ]
# ///
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a server instance
server = Server("example-server")


# Add prompt capabilities
@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="example-prompt",
            description="An example prompt template",
            arguments=[
                types.PromptArgument(
                    name="arg1", description="Example argument", required=True
                )
            ],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    if name != "example-prompt":
        raise ValueError(f"Unknown prompt: {name}")

    return types.GetPromptResult(
        description="Example prompt",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text="Example prompt text"),
            )
        ],
    )


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="fetch",
            description="Fetches a website and returns its content",
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    }
                },
            },
        ),
        types.Tool(
            name="get_weather",
            description="Get current weather for a city",
            inputSchema={
                "type": "object",
                "required": ["city"],
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name to get weather for",
                    },
                    "units": {
                        "type": "string",
                        "description": "Temperature units (celsius/fahrenheit)",
                        "enum": ["celsius", "fahrenheit"],
                        "default": "celsius",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def handle_tool_call(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "get_weather":
        city = arguments["city"]
        units = arguments.get("units", "celsius")

        # Get API key from environment
        api_key = os.getenv("FREE_WEATHER_KEY")
        if not api_key:
            return [
                types.TextContent(
                    type="text",
                    text="Error: Weather API key not found in environment variables",
                )
            ]

        # Make API request
        try:
            response = requests.get(
                "http://api.weatherapi.com/v1/current.json",
                params={"key": api_key, "q": city, "aqi": "no"},
            )
            response.raise_for_status()
            data = response.json()

            # Extract weather data
            current = data["current"]
            location = data["location"]

            # Get temperature based on requested units
            temp = current["temp_c"] if units == "celsius" else current["temp_f"]

            return [
                types.TextContent(
                    type="text",
                    text=f"Weather in {location['name']}, {location['country']}:\n"
                    + f"Temperature: {temp}°{'C' if units == 'celsius' else 'F'}\n"
                    + f"Conditions: {current['condition']['text']}\n"
                    + f"Humidity: {current['humidity']}%\n"
                    + f"Wind Speed: {current['wind_kph']} km/h\n"
                    + f"Feels Like: {current['feelslike_c' if units == 'celsius' else 'feelslike_f']}°{'C' if units == 'celsius' else 'F'}\n"
                    + f"Last Updated: {current['last_updated']}",
                )
            ]

        except requests.RequestException as e:
            return types.TextContent(
                type="text", text=f"Error fetching weather data: {str(e)}"
            ).text

    raise ValueError(f"Unknown tool: {name}")


async def run():
    # Run the server as STDIO
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="example",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
