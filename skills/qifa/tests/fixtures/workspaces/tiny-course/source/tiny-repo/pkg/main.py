"""tiny-repo fixture：两个函数的最小调用链。"""


def helper(value: int) -> int:
    return value + 1


def run(value: int) -> int:
    result = helper(value)
    return result
