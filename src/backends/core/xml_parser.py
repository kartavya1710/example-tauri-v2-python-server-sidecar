import re

class XMLParser:
    def parse_browser_action(self, xml_str):
        """Parse browser action from XML string"""
        action_match = re.search(r"<action>(\w+)</action>", xml_str)
        if not action_match:
            return None

        action_type = action_match.group(1)
        url_match = re.search(r"<url>(.*?)</url>", xml_str)
        coordinate_match = re.search(r"<coordinate>(\d+),\s*(\d+)</coordinate>", xml_str)
        text_match = re.search(r"<text>(.*?)</text>", xml_str)

        return {
            "action": action_type,
            "url": url_match.group(1) if url_match else None,
            "coordinate": (int(coordinate_match.group(1)), int(coordinate_match.group(2))) if coordinate_match else None,
            "text": text_match.group(1) if text_match else None,
        }