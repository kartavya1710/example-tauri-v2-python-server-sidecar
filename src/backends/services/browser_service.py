from core.xml_parser import XMLParser
import asyncio
import base64
from PIL import Image
import io

class BrowserService:
    def __init__(self, browser_manager):
        self.xml_parser = XMLParser()
        self.browser_manager = browser_manager

    async def execute_action(self, xml_str):
        try:
            action = self.xml_parser.parse_browser_action(xml_str)
            if action:
                # Implement browser action execution logic here
                result = await self._execute_browser_action(action)
                return result
        except Exception as e:
            print(f"Error executing browser action: {str(e)}")
            return None

    async def _execute_browser_action(self, action):
        """
        Private method to execute the actual browser action
        Implement different action types here
        """
        action_type = action["action"]

        result = {"success": True, "message": "", "logs": [], "scroll_info": {}}
        
        if action_type == 'launch':
            print("\nExecuting launch action...")
            success = await self.browser_manager.navigate(action["url"])

            if not success:
                result["success"] = False
                result["message"] = "Failed to navigate to the URL"
                return result

            result["message"] = f"Launched browser at: {action['url']}"
            await asyncio.sleep(2)
        elif action_type == 'click':
            await self.browser_manager.ensure_cursor_exists()
            squashed_x, squashed_y = action['coordinate']
            x, y = self.browser_manager.convert_coordinates(squashed_x, squashed_y)
            # self.scroll_position = await self.page.evaluate("window.scrollY")
            # actual_y = y
            # print("\nscroll_position", self.scroll_position)
            # print(f"Clicking at ({x}, {actual_y})")
            actual_y = y

            try:
                await self.browser_manager.page.evaluate(f"""
                                   () => {{
                                       const cursor = document.querySelector('.custom-cursor');
                                       if (cursor) {{
                                           cursor.style.left = '{x}px';
                                           cursor.style.top = '{actual_y}px';
                                       }}
                                   }}
                               """)
                await asyncio.sleep(0.5)

                await self.browser_manager.page.evaluate("""
                                   () => {
                                       const cursor = document.querySelector('.custom-cursor');
                                       if (cursor) {
                                           cursor.classList.add('clicking');
                                           setTimeout(() => cursor.classList.remove('clicking'), 200);
                                       }
                                   }
                               """)
                async with self.browser_manager.page.expect_navigation(wait_until="networkidle",
                                                                       timeout=5000) as navigation:
                    await self.browser_manager.page.mouse.click(x, actual_y)
                    try:
                        await navigation.value
                        print("Navigation completed")
                    except:
                        print("No navigation occurred")

                # if self.context.pages:
                #     self.page = self.context.pages[-1]  # Switch to the most recently opened tab
                #     await self.page.bring_to_front()
            except Exception as e:
                print(f"Error updating cursor: {str(e)}")

            result["message"] = f"Clicked at coordinates: ({squashed_x}, {squashed_y})"
            await asyncio.sleep(0.3)

        elif action_type == 'move':
            await self.browser_manager.ensure_cursor_exists()
            squashed_x, squashed_y = action['coordinate']
            x, y = self.browser_manager.convert_coordinates(squashed_x, squashed_y)
            actual_y = y

            try:
                await self.browser_manager.page.evaluate(f"""
                                   () => {{
                                       const cursor = document.querySelector('.custom-cursor');
                                       if (cursor) {{
                                           cursor.style.left = '{x}px';
                                           cursor.style.top = '{actual_y}px';
                                       }}
                                   }}
                               """)
                await asyncio.sleep(0.5)

                await self.browser_manager.page.mouse.move(x, actual_y)
            except Exception as e:
                print(f"Error updating cursor: {str(e)}")

            result["message"] = f"Clicked at coordinates: ({squashed_x}, {squashed_y})"
            await asyncio.sleep(0.3)


        elif action_type == 'type':
            await self.browser_manager.page.keyboard.type(action['text'])
            result["message"] = f"Typed text: {action['text']}"
            await asyncio.sleep(0.3)

        elif action_type == 'scroll_down':
            scroll_info = await self.browser_manager.update_scroll_info()
            if scroll_info:
                if (
                        self.browser_manager.scroll_position + scroll_info["viewportHeight"]
                        < self.browser_manager.total_scroll_height
                ):
                    await self.browser_manager.page.mouse.wheel(0, 600)
                    # await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                    # Update cursor position after scroll
                    await self.browser_manager.page.evaluate("""
                                       () => {
                                           const cursor = document.querySelector('.custom-cursor');
                                           if (cursor) {
                                               const currentTop = parseInt(cursor.style.top) || 0;
                                               cursor.style.top = (currentTop - window.innerHeight) + 'px';
                                           }
                                       }
                                   """)
                    result["message"] = "Scrolled down"
                else:
                    result["message"] = "Reached bottom of page"
            await asyncio.sleep(0.2)

        elif action_type == 'scroll_up':
            scroll_info = await self.browser_manager.update_scroll_info()
            if scroll_info:
                if self.browser_manager.scroll_position > 0:
                    await self.browser_manager.page.mouse.wheel(0, -600)
                    # await self.page.evaluate("window.scrollBy(0, -window.innerHeight)")
                    # Update cursor position after scroll
                    await self.browser_manager.page.evaluate("""
                                       () => {
                                           const cursor = document.querySelector('.custom-cursor');
                                           if (cursor) {
                                               const currentTop = parseInt(cursor.style.top) || 0;
                                               cursor.style.top = (currentTop + window.innerHeight) + 'px';
                                           }
                                       }
                                   """)
                    result["message"] = "Scrolled up"
                else:
                    result["message"] = "Reached top of page"
            await asyncio.sleep(0.5)

        elif action_type == 'wait':
            await asyncio.sleep(2)
            result["message"] = "Waited for page to load"

        elif action_type == 'close':
            # await self.cleanup()
            result["message"] = "Browser closed"
            return result


        # Capture screenshot and console logs after action
        if self.browser_manager.page:
            # await asyncio.sleep(0.5)
            screenshot_bytes = await self.browser_manager.page.screenshot(
                type="jpeg",
                quality=80,
                clip={
                    "x": 0,
                    "y": 0,
                    "width": self.browser_manager.viewport_width,
                    "height": self.browser_manager.viewport_height
                },
            )

            image = Image.open(io.BytesIO(screenshot_bytes))
            squashed_image = image.resize((1200, 800), Image.Resampling.LANCZOS)

            # Save the screenshot to the root directory
            squashed_buffer = io.BytesIO()
            squashed_image.save(squashed_buffer, format="PNG", quality=95)
            squashed_bytes = squashed_buffer.getvalue()

            screenshot_b64 = base64.b64encode(squashed_bytes).decode("utf-8")
            
            # Store screenshot in both result and as a separate field
            result["screenshot"] = screenshot_b64
            result = {
                "message": result["message"],
                "success": result["success"],
                "screenshot": screenshot_b64
            }
            
            # Import the broadcast function at runtime to avoid circular imports
            from src.api import broadcast_screenshot
            await broadcast_screenshot(screenshot_b64)

        return result
