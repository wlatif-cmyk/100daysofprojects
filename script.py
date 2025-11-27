#!/usr/bin/env python3
"""Simple CLI greeting script.

Usage:
  python script.py --name Alice
"""

import argparse
import datetime


def greet(name: str) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Hello, {name}! Time: {now}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple greeting script")
    parser.add_argument("--name", "-n", default="World", help="Name to greet")
    args = parser.parse_args()
    print(greet(args.name))


if __name__ == "__main__":
    main()
