"""Toy example: Python does the mechanics, Claude does the orchestration."""

import argparse
import json


def add(a: float, b: float) -> float:
    return a + b


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("a", type=float)
    parser.add_argument("b", type=float)
    args = parser.parse_args()

    result = add(args.a, args.b)
    print(json.dumps({"a": args.a, "b": args.b, "result": result}))
