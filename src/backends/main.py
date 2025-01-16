from fastapi import FastAPI, HTTPException, WebSocket, Depends
import asyncio
from core.browser_automation import BrowserAutomation
from pydantic import BaseModel
# from core.mcp_hub_singleton import get_mcp_hub, initialize_mcp_hub
# from core.mcp_client import MCPHub
# from core.cron_handler import CronJobManager
from fastapi.middleware.cors import CORSMiddleware

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
# @app.on_event("startup")
# async def startup():
#     await automation.initialize()
#     await initialize_mcp_hub()
#     cron_manager = CronJobManager(automation)
#     cron_manager.start()


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
        return {"success": True, "result": "Hello"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    return {"status": "Browser automation running"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        websocket_clients.remove(websocket)


async def broadcast_message(message: dict):
    disconnected_clients = []
    for client in websocket_clients:
        try:
            await client.send_json(message)
        except:
            disconnected_clients.append(client)
    for client in disconnected_clients:
        websocket_clients.remove(client)


async def broadcast_screenshot(screenshot_data: str):
    for client in websocket_clients:
        try:
            await client.send_json({"screenshot": screenshot_data})
        except:
            websocket_clients.remove(client)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8008)
