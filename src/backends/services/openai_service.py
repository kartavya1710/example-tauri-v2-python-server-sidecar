import uuid
from openai import OpenAI
from utils.common import StreamEvent, StreamEventType
import dotenv


class OpenAIService:
    def __init__(self):

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key="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"
        )
        self.user_id = uuid.uuid4().hex

    def convert_to_openai_messages(self, messages):
        openai_messages = []
        for msg in messages:
            role = msg["role"] if "role" in msg else "user"
            content = msg["content"]

            if isinstance(content, str):
                openai_messages.append({
                    "role": "assistant" if role == "assistant" else "user",
                    "content": content
                })
            elif isinstance(content, list):
                processed_content = []
                for part in content:
                    if "type" in part:
                        if part["type"] == "text":
                            if not processed_content:
                                processed_content.append({"type": "text", "text": part["text"]})
                            else:
                                if isinstance(processed_content[-1], dict) and processed_content[-1]["type"] == "text":
                                    processed_content[-1]["text"] += part["text"]
                                else:
                                    processed_content.append({"type": "text", "text": part["text"]})
                        elif part["type"] == "image":
                            processed_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{part['source']['media_type']};base64,{part['source']['data']}"
                                }
                            })

                openai_messages.append({
                    "role": "assistant" if role == "assistant" else "user",
                    "content": processed_content[0]["text"] if len(processed_content) == 1 and 
                              processed_content[0]["type"] == "text" else processed_content
                })

        return openai_messages

    async def create_message(self,system_prompt, messages):
        openai_messages = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(self.convert_to_openai_messages(messages))

        stream = self.client.chat.completions.create(
            model="GPT-4o-mini",
            messages=openai_messages,
            stream=True,
            max_tokens=8192,
            temperature=0,
            metadata={"user_id": self.user_id}
        )

        for chunk in stream:
            if hasattr(chunk, "error"):
                error = getattr(chunk, "error")
                error_msg = f"OpenRouter API Error {error.get('code', 'unknown')}: {error.get('message', 'Unknown error')}"
                print(error_msg)
                raise Exception(error_msg)

            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield StreamEvent(type=StreamEventType.TEXT, text=delta.content)