from dataclasses import dataclass
from typing import Any


@dataclass
class ActionResult:
    """Simple Class for holding action result"""

    is_success: bool
    message: str
    result_object: Any
