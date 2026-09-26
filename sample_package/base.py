"""
Base service definition module.
"""

class BaseService:
    def __init__(self, service_name: str):
        self.service_name = service_name

    def execute(self) -> str:
        return f"Executing {self.service_name}"
