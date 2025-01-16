from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Union

class StreamEventType(str, Enum):
    USAGE = "usage"
    TEXT = "text"

    def __str__(self):
        return self.value


@dataclass
class StreamEvent:
    type: StreamEventType
    text: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cache_write_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None