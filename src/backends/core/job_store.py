import json
import os
from typing import Dict, Any, Optional
from dataclasses import asdict, dataclass
import time

@dataclass
class StoredJob:
    job_id: str
    interval: int
    query: str
    last_run: float
    start_time: Optional[float] = None
    is_active: bool = True

class JobStore:
    """File-based storage for cron jobs to share between processes"""
    
    def __init__(self, store_path: str = "cron_jobs.json"):
        self.store_path = store_path
        self._ensure_store_exists()
    
    def _ensure_store_exists(self):
        """Create store file if it doesn't exist"""
        if not os.path.exists(self.store_path):
            self._save_jobs({})
    
    def _save_jobs(self, jobs: Dict[str, Dict[str, Any]]):
        """Save jobs to file"""
        with open(self.store_path, 'w') as f:
            json.dump(jobs, f, indent=2)
    
    def _load_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Load jobs from file"""
        try:
            with open(self.store_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    
    def add_job(self, job_id: str, interval: int, query: str, start_time: Optional[float] = None):
        """Add a new job to the store"""
        jobs = self._load_jobs()
        jobs[job_id] = asdict(StoredJob(
            job_id=job_id,
            interval=interval,
            query=query,
            last_run=time.time(),
            start_time=start_time
        ))
        self._save_jobs(jobs)
    
    def update_last_run(self, job_id: str):
        """Update the last run time for a job"""
        jobs = self._load_jobs()
        if job_id in jobs:
            jobs[job_id]['last_run'] = time.time()
            self._save_jobs(jobs)
    
    def get_jobs(self) -> Dict[str, StoredJob]:
        """Get all jobs from store"""
        jobs = self._load_jobs()
        return {
            job_id: StoredJob(**job_data)
            for job_id, job_data in jobs.items()
        }
    
    def remove_job(self, job_id: str):
        """Remove a job from store"""
        jobs = self._load_jobs()
        if job_id in jobs:
            del jobs[job_id]
            self._save_jobs(jobs)
    
    def update_job_status(self, job_id: str, is_active: bool):
        """Update job active status"""
        jobs = self._load_jobs()
        if job_id in jobs:
            jobs[job_id]['is_active'] = is_active
            self._save_jobs(jobs)
