from typing import Any


class StubAsyncResult:
    def __init__(self, task_id: str, state: str, info: Any):
        self.task_id = task_id
        self.state = state
        self.info = info

    def get(self):
        return self.info
