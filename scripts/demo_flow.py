#!/usr/bin/env python3
"""Runs an end-to-end API demo against a local service."""

from __future__ import annotations

import json
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:8000"


def request(method: str, path: str, payload: dict[str, str] | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    ticket = request(
        "POST",
        "/tickets",
        {
            "title": "Production login failures",
            "description": "Users receive intermittent 403 responses.",
            "priority": "critical",
            "requester": "incident-commander",
        },
    )
    assigned = request("POST", f"/tickets/{ticket['id']}/assign", {"assignee": "sre-oncall"})
    request(
        "POST",
        f"/tickets/{ticket['id']}/comments",
        {"author": "sre-oncall", "body": "Correlating auth logs with gateway errors."},
    )
    drained = request("POST", "/events/drain")
    print(json.dumps({"ticket": assigned, "events": drained}, indent=2))


if __name__ == "__main__":
    main()

