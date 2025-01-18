from fastapi import FastAPI, HTTPException, WebSocket, Depends
import asyncio
from core.browser_automation import BrowserAutomation
from pydantic import BaseModel
from core.mcp_hub_singleton import get_mcp_hub, initialize_mcp_hub
# from core.mcp_client import MCPHub
# from core.cron_handler import CronJobManager
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from datetime import datetime

def setup_logging():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(backend_dir, 'logs')
    
    # Create logs directory with explicit permissions
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log file with absolute path
    log_file = os.path.join(logs_dir, f'logs.txt')
    
    # Print debug info
    print(f"Log directory: {logs_dir}")
    print(f"Log file: {log_file}")

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

app = FastAPI()
# websocket_clients = set()
automation = BrowserAutomation()

class TaskRequest(BaseModel):
    message: str

server_instance = None  # Global reference to the Uvicorn server instance

# Configure CORS settings
origins = [
    "*",
    # "https://your-web-ui.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or use "*" to whitelist any url
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Tell client we are ready to accept requests.
# # This is a mock func, modify to your needs.
@app.on_event("startup")
async def startup():
    await automation.initialize()
    await initialize_mcp_hub()
    # cron_manager = CronJobManager(automation)
    # cron_manager.start()


@app.post("/start_task")
async def start_task(request: TaskRequest):
    try:
        print(request.message)
        # # Simulate a long-running task
        result = await automation.run(request.message, is_cron=False)

        # # If WebSocket clients are connected, broadcast the result
        # if websocket_clients:
        #     await broadcast_message({"message": "Task completed", "result": result})

        # # Return API response
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    return {"status": "Browser automation running"}


if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="127.0.0.1", port=8000)
    uvicorn.run(app, host="0.0.0.0", port=8008)
