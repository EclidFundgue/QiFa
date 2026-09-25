"""tiny-cli 入口：解析参数并打印问候语。"""

from __future__ import annotations

import sys

from greet import greet


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    name = args[0] if args else "World"
    print(greet(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
