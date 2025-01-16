#!/usr/bin/env python3
# /// script
# dependencies = [
#   "mcp",
#   "python-dotenv"
# ]
# ///
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
import os
from dotenv import load_dotenv
from src.core.cron_handler import CronJobManager
from datetime import datetime

# Load environment variables
load_dotenv()

# Create a server instance
server = Server("cron-server")
cron_manager = CronJobManager()

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="add_cron_job",
            description="Add a new scheduled job",
            inputSchema={
                "type": "object",
                "required": ["job_id", "interval", "query"],
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Unique identifier for the job",
                    },
                    "interval": {
                        "type": "integer",
                        "description": "Interval in seconds between job executions",
                    },
                    "query": {
                        "type": "string",
                        "description": "The query/command to execute",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Optional start time in YYYY-MM-DD HH:MM:SS format",
                    }
                },
            },
        ),
        types.Tool(
            name="remove_cron_job",
            description="Remove an existing cron job",
            inputSchema={
                "type": "object",
                "required": ["job_id"],
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "ID of the job to remove",
                    }
                },
            },
        ),
        types.Tool(
            name="list_cron_jobs",
            description="List all cron jobs",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="pause_cron_job",
            description="Pause a cron job",
            inputSchema={
                "type": "object",
                "required": ["job_id"],
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "ID of the job to pause",
                    }
                },
            },
        ),
        types.Tool(
            name="resume_cron_job",
            description="Resume a paused cron job",
            inputSchema={
                "type": "object",
                "required": ["job_id"],
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "ID of the job to resume",
                    }
                },
            },
        ),
    ]

@server.call_tool()
async def handle_tool_call(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "add_cron_job":
            job_id = arguments["job_id"]
            interval = arguments["interval"]
            query = arguments["query"]
            start_time = None
            
            if "start_time" in arguments:
                start_time = datetime.strptime(arguments["start_time"], "%Y-%m-%d %H:%M:%S").timestamp()
            
            cron_manager.add_job(job_id, interval, query, start_time)
            return [
                types.TextContent(
                    type="text",
                    text=f"Successfully added cron job '{job_id}'"
                )
            ]

        elif name == "remove_cron_job":
            job_id = arguments["job_id"]
            cron_manager.remove_job(job_id)
            return [
                types.TextContent(
                    type="text",
                    text=f"Successfully removed cron job '{job_id}'"
                )
            ]

        elif name == "list_cron_jobs":
            jobs = cron_manager.list_jobs()
            if not jobs:
                return [
                    types.TextContent(
                        type="text",
                        text="No cron jobs found"
                    )
                ]
            
            job_list = []
            for job_id, job in jobs.items():
                status = "Active" if job.is_active else "Paused"
                next_run = job.last_run + job.interval
                job_list.append(
                    f"Job ID: {job_id}\n"
                    f"Status: {status}\n"
                    f"Interval: {job.interval}s\n"
                    f"Query: {job.query}\n"
                    f"Last Run: {datetime.fromtimestamp(job.last_run).strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Next Run: {datetime.fromtimestamp(next_run).strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
            
            return [
                types.TextContent(
                    type="text",
                    text="Current Cron Jobs:\n\n" + "\n".join(job_list)
                )
            ]

        elif name == "pause_cron_job":
            job_id = arguments["job_id"]
            cron_manager.pause_job(job_id)
            return [
                types.TextContent(
                    type="text",
                    text=f"Successfully paused cron job '{job_id}'"
                )
            ]

        elif name == "resume_cron_job":
            job_id = arguments["job_id"]
            cron_manager.resume_job(job_id)
            return [
                types.TextContent(
                    type="text",
                    text=f"Successfully resumed cron job '{job_id}'"
                )
            ]

        raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]

async def run():
    # Start the cron manager
    cron_manager.start()
    
    # Run the server as STDIO
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="cron-server",
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
