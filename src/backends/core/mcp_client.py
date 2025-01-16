import asyncio
import json
from typing import List, Dict, Any
from contextlib import AsyncExitStack
from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client, get_default_environment


@dataclass
class McpServer:
    name: str
    config: str
    status: str = "disconnected"
    error: str = ""
    tools: List[Dict[str, Any]] = None
    resources: List[Dict[str, Any]] = None
    resource_templates: List[Dict[str, Any]] = None

    def __post_init__(self):
        self.tools = [] if self.tools is None else self.tools
        self.resources = [] if self.resources is None else self.resources
        self.resource_templates = (
            [] if self.resource_templates is None else self.resource_templates
        )


@dataclass
class McpConnection:
    server: McpServer
    session: ClientSession
    transport: tuple[asyncio.StreamReader, asyncio.StreamWriter]
    exit_stack: AsyncExitStack


class McpToolRequest:
    def __init__(self, xml_str: str):
        """Parse MCP tool request from XML string format.

        Args:
            xml_str: XML string in the format:
            <use_mcp_tool>
                <server_name>server</server_name>
                <tool_name>tool</tool_name>
                <arguments>{json object}</arguments>
            </use_mcp_tool>
        """
        try:
            # Extract server_name
            server_match = re.search(r'<server_name>(.*?)</server_name>', xml_str)
            if not server_match:
                raise ValueError("Missing <server_name> element")
            self.server_name = server_match.group(1)

            # Extract tool_name
            tool_match = re.search(r'<tool_name>(.*?)</tool_name>', xml_str)
            if not tool_match:
                raise ValueError("Missing <tool_name> element")
            self.tool_name = tool_match.group(1)

            # Extract arguments
            # print("xml_str: ", xml_str)
            args_match = re.search(r'<arguments>(.*?)</arguments>', xml_str, re.S).group(1)
            print("args_match: ", args_match)
            self.arguments = json.loads(args_match.strip())
            if not args_match:
                raise ValueError("Missing <arguments> element")
            # self.arguments = args_match.group(1)
        except Exception as e:
            raise ValueError(f"Invalid XML format: {str(e)}")

    async def execute(self, hub: 'MCPHub') -> Dict[str, Any]:
        """Execute the tool request using the provided MCPHub instance.

        Args:
            hub: MCPHub instance to use for execution

        Returns:
            Dict containing the tool execution results
        """
        return await hub.call_tool(
            self.server_name,
            self.tool_name,
            self.arguments
        )


class MCPHub:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            print("Creating new MCPHub instance")
            cls._instance = super(MCPHub, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            print("Initializing MCPHub")
            self.connections: List[McpConnection] = []
            self._initialized = True

    async def connect_to_server(self, name: str, config: Dict[str, Any]):
        """Connect to an MCP server

        Args:
            name: Name of the server
            config: Server configuration containing command, args, and env
        """
        # Remove existing connection if it exists
        self.connections = [
            conn for conn in self.connections if conn.server.name != name
        ]

        try:
            server = McpServer(name=name, config=str(config), status="connecting")
            env = get_default_environment()
            server_env = config.get("env", None)
            env.update(server_env) if server_env else None

            server_params = StdioServerParameters(
                command=config["command"],
                args=config["args"],
                env=env
            )

            exit_stack = AsyncExitStack()
            stdio_transport = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            session = await exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )

            await session.initialize()

            connection = McpConnection(
                server=server,
                session=session,
                transport=stdio_transport,
                exit_stack=exit_stack
            )

            # Initial fetch of tools and resources
            connection.server.tools = await self.fetch_tools_list(connection)
            connection.server.resources = await self.fetch_resources_list(connection)
            connection.server.resource_templates = (
                await self.fetch_resource_templates_list(connection)
            )

            connection.server.status = "connected"
            connection.server.error = ""

            self.connections.append(connection)

            print(
                f"\nConnected to server {name} with tools:",
                [tool["name"] for tool in connection.server.tools],
            )

        except Exception as e:
            server.status = "disconnected"
            server.error = str(e)
            raise

    async def fetch_tools_list(self, connection: McpConnection) -> List[Dict[str, Any]]:
        """Fetch list of available tools from a server"""
        try:
            response = await connection.session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in response.tools
            ]
        except Exception:
            return []

    async def fetch_resources_list(
            self, connection: McpConnection
    ) -> List[Dict[str, Any]]:
        """Fetch list of available resources from a server"""
        try:
            response = await connection.session.list_resources()
            return [
                {
                    "uri": resource.uri,
                    "name": resource.name,
                    "mime_type": resource.mimeType,
                    "description": resource.description,
                }
                for resource in response.resources
            ]
        except Exception:
            return []

    async def fetch_resource_templates_list(
            self, connection: McpConnection
    ) -> List[Dict[str, Any]]:
        """Fetch list of available resource templates from a server"""
        try:
            response = await connection.session.list_resource_templates()
            return [
                {
                    "uri_template": template.uriTemplate,
                    "name": template.name,
                    "mime_type": template.mimeType,
                    "description": template.description,
                }
                for template in response.resourceTemplates
            ]
        except Exception:
            return []

    async def delete_connection(self, name: str):
        """Delete a server connection"""
        connection = next(
            (conn for conn in self.connections if conn.server.name == name), None
        )
        if connection:
            try:
                # Close exit stack which will handle cleanup of all resources
                await connection.exit_stack.aclose()
            except Exception as e:
                print(f"Failed to close connection for {name}: {e}")
            finally:
                self.connections = [
                    conn for conn in self.connections if conn.server.name != name
                ]

    async def read_resource(self, server_name: str, uri: str) -> Dict[str, Any]:
        """Read a resource from a server"""
        connection = next(
            (conn for conn in self.connections if conn.server.name == server_name), None
        )
        if not connection:
            raise ValueError(f"No connection found for server: {server_name}")

        response = await connection.session.read_resource(uri)
        return {
            "contents": [
                {
                    "uri": content.uri,
                    "mime_type": content.mimeType,
                    "text": content.text,
                }
                for content in response.contents
            ]
        }

    async def call_tool(
            self, server_name: str, tool_name: str, tool_arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call a tool on a server with timeout"""
        connection = next(
            (conn for conn in self.connections if conn.server.name == server_name), None
        )
        if not connection:
            raise ValueError(f"No connection found for server: {server_name}")

        try:
            # Add 30 second timeout to prevent hanging
            response = await asyncio.wait_for(
                connection.session.call_tool(tool_name, tool_arguments or {}),
                timeout=30.0
            )
            return {
                "content": [
                    {"type": content.type, "text": content.text}
                    for content in response.content
                ]
            }
        except asyncio.TimeoutError:
            error_msg = f"Tool call to {tool_name} on {server_name} timed out after 30 seconds"
            print(error_msg)
            return {
                "content": [
                    {"type": "error", "text": error_msg}
                ]
            }
        except Exception as e:
            error_msg = f"Error calling tool {tool_name} on {server_name}: {str(e)}"
            print(error_msg)
            return {
                "content": [
                    {"type": "error", "text": error_msg}
                ]
            }

    def get_servers(self) -> List[McpServer]:
        """Get list of all connected servers"""
        return [conn.server for conn in self.connections]

    async def cleanup(self):
        """Clean up all connections and resources"""
        for connection in self.connections:
            try:
                await connection.exit_stack.aclose()
            except Exception as e:
                print(f"Error cleaning up connection: {str(e)}")

    def format_server_info(self) -> str:
        """Format information about connected MCP servers including their tools and resources.

        Returns:
            str: Formatted string containing server information, or a message if no servers are connected.
        """
        servers = self.get_servers()
        if not servers:
            return "(No MCP servers currently connected)"

        connected_servers = [
            server for server in servers if server.status == "connected"
        ]
        if not connected_servers:
            return "(No MCP servers currently connected)"

        server_info = []
        for server in connected_servers:
            # Parse config string back to dict
            config = eval(server.config)  # Safe since we created this string ourselves

            # Format command and args
            command_str = config["command"]
            if config.get("args"):
                command_str += f" {' '.join(config['args'])}"

            # Start with server header
            sections = [f"## {server.name} (`{command_str}`)"]

            # Add tools section if there are tools
            if server.tools:
                tool_strings = []
                for tool in server.tools:
                    tool_str = f"- {tool['name']}: {tool['description']}"
                    if tool.get("input_schema"):
                        schema_str = json.dumps(tool["input_schema"], indent=2)
                        # Indent each line of the schema
                        schema_lines = schema_str.split("\n")
                        indented_schema = "\n    ".join(schema_lines)
                        tool_str += f"\n    Input Schema:\n    {indented_schema}"
                    tool_strings.append(tool_str)

                if tool_strings:
                    sections.append("### Available Tools")
                    sections.extend(tool_strings)

            # Add resource templates section if there are templates
            if server.resource_templates:
                template_strings = []
                for template in server.resource_templates:
                    template_str = f"- {template['uri_template']} ({template['name']})"
                    if template.get("description"):
                        template_str += f": {template['description']}"
                    template_strings.append(template_str)

                if template_strings:
                    sections.append("\n### Resource Templates")
                    sections.extend(template_strings)

            # Add direct resources section if there are resources
            if server.resources:
                resource_strings = []
                for resource in server.resources:
                    resource_str = f"- {resource['uri']} ({resource['name']})"
                    if resource.get("description"):
                        resource_str += f": {resource['description']}"
                    resource_strings.append(resource_str)

                if resource_strings:
                    sections.append("\n### Direct Resources")
                    sections.extend(resource_strings)

            server_info.append("\n".join(sections))

        return "\n\n".join(server_info)


async def main():
    """Test the MCPHub functionality"""
    hub = MCPHub()

    try:
        memory_tracker_config = {
            "command": "node",
            "args": [
                "/Users/snehmehta/Documents/Cline/MCP/memory-tracker/build/index.js"
            ],
            "env": None,
        }

        # weather_config = {
        #     "command": "python",
        #     "args": ["server.py"],
        #     "env": None,
        # }
        search_config = {
            "command": "uv",
            "args": [
                "--directory",
                "/Users/snehmehta/work/miraiminds/mcp-server-tavily/",
                "run",
                "tavily-search",
            ],
            "env": None,
        }

        print("Connecting to memory-tracker server...")
        await hub.connect_to_server("memory-tracker", memory_tracker_config)
        # await hub.connect_to_server("weather", weather_config)
        await hub.connect_to_server("search", search_config)
        # Get server list
        servers = hub.get_servers()
        print("\nConnected servers:", [server.name for server in servers])

        # Test get_memory_usage tool
        print("\nTesting get_memory_usage tool...")
        result = await hub.call_tool("memory-tracker", "get_memory_usage")
        print("Memory usage:", result)

        # Test start_monitoring tool
        print("\nStarting memory monitoring (5 second interval)...")
        await hub.call_tool("memory-tracker", "start_monitoring", {"interval": 5})

        # Test XML tool request
        xml_str = """
        <use_mcp_tool>
        <server_name>search</server_name>
        <tool_name>search</tool_name>
        <arguments>
        {
          "query": "what is mcp by anthropic"
        }
        </arguments>
        </use_mcp_tool>
        """
        tool_request = McpToolRequest(xml_str)
        result = await tool_request.execute(hub)
        print("\nSearch result:", result)

        # Stop monitoring
        print("\nStopping memory monitoring...")
        await hub.call_tool("memory-tracker", "stop_monitoring")

    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        # Clean up
        print("\nCleaning up...")
        await hub.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
