#!/usr/bin/env python3
"""Tiny no-dependency load smoke script for demo runs."""

from __future__ import annotations

import json
import time
from urllib.request import Request, urlopen


def post_json(url: str, payload: dict[str, str]) -> int:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        response.read()
        return response.status


def main() -> None:
    start = time.perf_counter()
    count = 25
    for index in range(count):
        post_json(
            "http://127.0.0.1:8000/tickets",
            {
                "title": f"load-smoke-{index}",
                "description": "synthetic request",
                "priority": "medium",
                "requester": "load-smoke",
            },
        )
    elapsed = time.perf_counter() - start
    print({"requests": count, "seconds": round(elapsed, 3), "rps": round(count / elapsed, 2)})


if __name__ == "__main__":
    main()

