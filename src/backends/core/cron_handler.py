from typing import Dict, Any, Optional, Protocol
import asyncio
import time
import threading
import datetime
from dataclasses import dataclass
from core.job_store import JobStore, StoredJob
from core.mcp_client import McpToolRequest
import traceback


class MCPHubProtocol(Protocol):
    """Protocol defining the interface needed from MCPHub"""

    async def execute_mcp_tool(self, xml_str: str) -> dict:
        """Execute an MCP tool from XML string"""
        ...


class CronJobManager:
    _instance = None
    _initialized = False

    def __new__(cls, handler: Any = None):
        if cls._instance is None:
            print("Creating new CronJobManager instance")
            cls._instance = super(CronJobManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, handler: Any = None):
        if not self._initialized:
            print("Initializing CronJobManager")
            self.job_store = JobStore()
            self._stop_event = asyncio.Event()
            self._task: Optional[asyncio.Task] = None
            self._initialized = True
            self.handler = handler
            self._loop = None

    def add_job(self, job_id: str, interval: int, query: str, start_time: Optional[float] = None) -> None:
        """Add a new cron job"""
        print(f"Adding new cron job {job_id} with interval {interval}s and start time {start_time}")
        self.job_store.add_job(job_id, interval, query, start_time)

    def remove_job(self, job_id: str) -> None:
        """Remove a cron job"""
        print(f"Removing cron job {job_id}")
        self.job_store.remove_job(job_id)

    async def _run_async(self) -> None:
        """Main cron job async function"""
        print("Cron job manager running")

        while not self._stop_event.is_set():
            try:
                await self._check_and_execute_jobs()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error in cron loop: {str(e)}")
                if not self._stop_event.is_set():
                    await asyncio.sleep(5)

    async def _check_and_execute_jobs(self) -> None:
        """Check and execute due jobs"""
        current_time = time.time()
        jobs = self.job_store.get_jobs()

        if jobs:
            print(f"\nChecking {len(jobs)} cron jobs at {time.strftime('%H:%M:%S')}:")

            for job_id, job in jobs.items():
                if not job.is_active:
                    print(f"- Job {job_id}: Inactive")
                    continue

                if job.start_time:
                    start_time_struct = datetime.datetime.strptime(job.start_time, "%Y-%m-%d %H:%M:%S")
                    start_time_timestamp = start_time_struct.timestamp()
                    if current_time < start_time_timestamp:
                        print(
                            f"- Job {job_id}: Not yet started (starts at {time.strftime('%H:%M:%S', time.localtime(start_time_timestamp))})")
                        continue

                time_since_last_run = current_time - job.last_run
                if time_since_last_run >= job.interval:
                    print(f"- Job {job_id}: Due for execution (last run: {time_since_last_run:.1f}s ago)")
                    try:
                        print(f"  Executing job {job_id}")
                        await self.handler.run(job.query, is_cron=True)
                        self.job_store.update_last_run(job_id)
                        print(f"  Job {job_id} executed successfully")
                    except Exception as e:
                        print(f"  Error executing job {job_id}: {str(e)}")
                else:
                    print(f"- Job {job_id}: Next run in {job.interval - time_since_last_run:.1f}s")

    def start(self) -> None:
        """Start the cron job manager"""
        if not self._task:
            print("Starting cron job manager")
            self._stop_event.clear()
            self._loop = asyncio.get_event_loop()
            self._task = self._loop.create_task(self._run_async())
            print("Cron job manager started")

    async def stop(self) -> None:
        """Stop the cron job manager"""
        if self._task:
            print("Stopping cron job manager")
            self._stop_event.set()
            await self._task
            self._task = None
            print("Cron job manager stopped")

    def pause_job(self, job_id: str) -> None:
        """Pause a cron job"""
        print(f"Pausing cron job {job_id}")
        self.job_store.update_job_status(job_id, False)

    def resume_job(self, job_id: str) -> None:
        """Resume a paused cron job"""
        print(f"Resuming cron job {job_id}")
        self.job_store.update_job_status(job_id, True)

    def get_job(self, job_id: str) -> Optional[StoredJob]:
        """Get a cron job by ID"""
        jobs = self.job_store.get_jobs()
        return jobs.get(job_id)

    def list_jobs(self) -> Dict[str, StoredJob]:
        """List all cron jobs"""
        return self.job_store.get_jobs()
