"""
Utility helper functions module.
"""

def format_message(prefix: str, msg: str) -> str:
    return f"[{prefix.upper()}] {msg}"

def compute_total(a: int, b: int) -> int:
    return a + b
