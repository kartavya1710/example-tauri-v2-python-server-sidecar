from core.mcp_hub_singleton import get_mcp_hub
from core.mcp_client import McpToolRequest
import traceback
import re
import time

class StreamProcessor:
    def __init__(self):
        self.buffer = ""
        self.inside_result = False
        self.current_result = ""
        self.current_tool_xml = ""
        self.action_result = None
        self.mcp_hub = get_mcp_hub()

    async def process_stream(self, content, browser_service):
        self.buffer = content
        print("-------------INSIDE PROCESS STREAM")
        await self._process_results()
        # await self._process_browser_actions(browser_service)
        if "<browser_action>" in self.buffer and "</browser_action>" in self.buffer:
            start = self.buffer.find("<browser_action>")
            end = self.buffer.find("</browser_action>") + len("</browser_action>")
            browser_action_xml = self.current_tool_xml[start:end]
            self.current_tool_xml = self.current_tool_xml[end:]

            self.action_result = await browser_service.execute_action(browser_action_xml)

        if ("<cronjob>" not in self.buffer and
                "<use_mcp_tool>" in self.buffer
                and "</use_mcp_tool>" in self.buffer):
            start = self.buffer.find("<use_mcp_tool>")
            end = self.buffer.find("</use_mcp_tool>") + len("</use_mcp_tool>")
            mcp_tool_xml = self.buffer[start:end]
            self.current_tool_xml = self.current_tool_xml[end:]

            try:
                print("mcp_tool_xml from process browser: \n", mcp_tool_xml)
                mcp_tool = McpToolRequest(xml_str=mcp_tool_xml)
                result = await mcp_tool.execute(self.mcp_hub)
                print("MCP tool result: ", result)
                self.action_result = {
                    "success": True,
                    "message": f"MCP tool executed successfully : {result}"
                }
            except Exception as e:
                print(traceback.format_exc())
                error_message = f"Error executing MCP tool: {str(e)}"
                print(error_message)
                self.action_result = {
                    "success": False,
                    "message": error_message
                }

        if "<cronjob>" in self.buffer and "</cronjob>" in self.buffer:
            start = self.buffer.find("<cronjob>")
            end = self.buffer.find("</cronjob>") + len("</cronjob>")
            cronjob_xml = self.buffer[start:end]
            self.current_tool_xml = self.current_tool_xml[end:]
            interval_match = re.search(r"<interval>(\d+)</interval>", cronjob_xml)
            starttime_match = re.search(r"<start_time>([^<]+)</start_time>", cronjob_xml)

            if interval_match:
                interval = int(interval_match.group(1))
                start_time = starttime_match.group(1) if starttime_match else None
                print("---------->start_time", start_time)
                # Extract the MCP tool XML from within cronjob
                query_start = cronjob_xml.find("<query>")
                query_end = cronjob_xml.find("</query>") + len("</query>")
                if query_start != -1 and query_end != -1:
                    query_xml = cronjob_xml[query_start:query_end]
                    # Add the cron job using the shared job store
                    from src.core.job_store import JobStore
                    job_store = JobStore()
                    job_id = f"job_{int(time.time())}"
                    print("Adding cron job:", job_id, interval, query_xml)
                    job_store.add_job(job_id, interval, query_xml, start_time)
                    self.action_result = {"success": True,
                                          "message": f"Cron job {job_id} created with interval {interval}s. The job will be executed by the cron manager process."}

        if "</attempt_completion>" in self.buffer:
            return True
        elif "<result>" in self.buffer:
            return True
        
        return False

    async def _process_results(self):
        while "<result>" in self.buffer or self.inside_result:
            if not self.inside_result:
                start_idx = self.buffer.find("<result>") + len("<result>")
                self.buffer = self.buffer[start_idx:]
                self.inside_result = True
                self.current_result = ""

            if "</result>" in self.buffer:
                end_idx = self.buffer.find("</result>")
                result_text = self.buffer[:end_idx]
                self.current_result += result_text
                self.buffer = self.buffer[end_idx + len("</result>"):]
                self.inside_result = False
            else:
                self.current_result += self.buffer
                self.buffer = ""
                break

    async def _process_browser_actions(self, browser_service):
        self.current_tool_xml += self.buffer

        if "<browser_action>" in self.current_tool_xml and "</browser_action>" in self.current_tool_xml:
            start = self.current_tool_xml.find("<browser_action>")
            end = self.current_tool_xml.find("</browser_action>") + len("</browser_action>")
            browser_action_xml = self.current_tool_xml[start:end]
            self.current_tool_xml = self.current_tool_xml[end:]

            self.action_result = await browser_service.execute_action(browser_action_xml)

        if ("<cronjob>" not in self.buffer and
            "<use_mcp_tool>" in self.buffer
            and "</use_mcp_tool>" in self.buffer
        ):
            start = self.buffer.find("<use_mcp_tool>")
            end = self.buffer.find("</use_mcp_tool>") + len("</use_mcp_tool>")
            mcp_tool_xml = self.buffer[start:end]
            self.current_tool_xml = self.current_tool_xml[end:]

            try:
                print("mcp_tool_xml from process browser: \n", mcp_tool_xml)
                mcp_tool = McpToolRequest(xml_str=mcp_tool_xml)
                result = await mcp_tool.execute(self.mcp_hub)
                print("MCP tool result: ", result)
                self.action_result = {
                    "success": True,
                    "message": f"MCP tool executed successfully : {result}"
                }
            except Exception as e:
                print(traceback.format_exc())
                error_message = f"Error executing MCP tool: {str(e)}"
                print(error_message)
                self.action_result = {
                    "success": False,
                    "message": error_message
                }

        if "<cronjob>" in self.buffer and "</cronjob>" in self.buffer:
            start = self.buffer.find("<cronjob>")
            end = self.buffer.find("</cronjob>") + len("</cronjob>")
            cronjob_xml = self.buffer[start:end]
            self.current_tool_xml = self.current_tool_xml[end:]
            interval_match = re.search(r"<interval>(\d+)</interval>", cronjob_xml)
            starttime_match = re.search(r"<start_time>([^<]+)</start_time>", cronjob_xml)

            if interval_match:
                interval = int(interval_match.group(1))
                start_time = starttime_match.group(1) if starttime_match else None
                print("---------->start_time", start_time)
                # Extract the MCP tool XML from within cronjob
                query_start = cronjob_xml.find("<query>")
                query_end = cronjob_xml.find("</query>") + len("</query>")
                if query_start != -1 and query_end != -1:
                    query_xml = cronjob_xml[query_start:query_end]
                    # Add the cron job using the shared job store
                    from src.core.job_store import JobStore
                    job_store = JobStore()
                    job_id = f"job_{int(time.time())}"
                    print("Adding cron job:", job_id, interval, query_xml)
                    job_store.add_job(job_id, interval, query_xml, start_time)
                    self.action_result ={"success": True,
                            "message": f"Cron job {job_id} created with interval {interval}s. The job will be executed by the cron manager process."}

