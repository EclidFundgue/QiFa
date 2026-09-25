"""问候逻辑。"""

from __future__ import annotations


def greet(name: str) -> str:
    """返回问候语；空名字回落为 World。"""
    cleaned = name.strip() or "World"
    return f"Hello, {cleaned}!"
