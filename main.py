#!/usr/bin/env python3
"""
IMC 意图驱动裁剪 — 对比演示入口

用法：
  python main.py              # 默认速度（1.5s/tick）
  python main.py --speed 1.0  # 加速
  python main.py --speed 3.0  # 放慢
"""

import argparse
from display import run_demo


def main():
    parser = argparse.ArgumentParser(
        description="IMC 意图驱动裁剪 — 对比演示"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.5,
        help="每个 tick 的间隔秒数（默认 1.5）",
    )
    args = parser.parse_args()

    try:
        run_demo(speed=args.speed)
    except KeyboardInterrupt:
        print("\n演示已中断。")


if __name__ == "__main__":
    main()
