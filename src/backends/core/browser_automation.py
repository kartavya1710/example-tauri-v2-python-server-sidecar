import traceback
from core.browser_manager import BrowserManager
from services.openai_service import OpenAIService
from services.browser_service import BrowserService
from utils.stream_processor import StreamProcessor
from utils.common import StreamEventType
from core.mcp_hub_singleton import get_mcp_hub
from core.prompt import system_prompt


class BrowserAutomation:
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.openai_service = OpenAIService()
        self.browser_service = BrowserService(self.browser_manager)
        self.api_conversation_history = []
        self.mcp_hub = get_mcp_hub()
        self.cron_history = []
        self.is_cron = False

    async def initialize(self):
        # await self.browser_manager.initialize()
        pass

    async def cleanup(self):
        # await self.browser_manager.cleanup()
        pass
    async def create_task_content(self, message):
        task_content = f"<task>\n{message}\n</task>"
        return [{"type": "text", "text": task_content}]

    async def make_api_requests(self, task, history):
        try:
            history.append({"role": "user", "content": task})
            print("\n\n------>this is the api conversation history", history)

            message_stream = self.openai_service.create_message(system_prompt(), history)
            stream_processor = StreamProcessor()
            assistant_message =  ""
            
            async for event in message_stream:
                if event.type == StreamEventType.TEXT:
                    print(event.text, end="")
                    assistant_message += event.text
                    
            if assistant_message:
                should_end = await stream_processor.process_stream(
                    assistant_message,
                    self.browser_service
                )
                print("-----------should end", should_end)
                if should_end:
                    return True
                history.append({
                        "role": "assistant",
                        "content": [{"type": "text", "text": assistant_message}],
                    })
                
                if stream_processor.action_result.get("success"):
                    if "screenshot" in stream_processor.action_result:
                        history.append({
                            "role": "user",
                            "content": [{
                                "type": "text",
                                "text": f"Here is screenshot of last action"
                            }]
                        })

                        if stream_processor.action_result.get("screenshot"):
                            history[-1]["content"].append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "data": stream_processor.action_result["screenshot"],
                                        "media_type": "image/png",
                                    },
                                })
                    else:
                        history.append({
                            "role": "user",
                            "content": [{
                                "type": "text",
                                "text": stream_processor.action_result.get('message', 'Unknown message')
                            }]
                        })
                
                else:
                    history.append({
                        "role": "user",
                        "content": [{
                            "type": "text",
                            "text": f"Browser action failed: {stream_processor.action_result.get('message', 'Unknown error')}"
                        }]
                    })

            return False
        except Exception as e:
            print(traceback.format_exc())

    async def run(self, message, is_cron):
        try:
            await self.initialize()
            self.is_cron = is_cron

            task_content = await self.create_task_content(message)
            next_user_content = task_content
            while True:
                if self.is_cron:
                    self.cron_history = []
                    did_end_loop = await self.make_api_requests(next_user_content, self.cron_history)
                    if did_end_loop:
                        break
                    next_user_content = [
                        {
                            "type": "text",
                            "text": "You responded with only text but haven't called attempt_completion. Please continue with the task...",
                        }
                    ]
                else:
                    did_end_loop = await self.make_api_requests(next_user_content, self.api_conversation_history)
                    if did_end_loop:
                        break

                    next_user_content = [
                        {
                            "type": "text",
                            "text": "You responded with only text but haven't called attempt_completion. Please continue with the task...",
                        }
                    ]
                
        except Exception as e:
            print(f"An error occurred: {str(e)}")
