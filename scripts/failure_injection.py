#!/usr/bin/env python3
"""Small failure drill helper for local SRE demos."""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="ticketing.sqlite")
    parser.add_argument("--mode", choices=["check", "lock-db", "clear"], default="check")
    args = parser.parse_args()

    db_path = Path(args.db)
    if args.mode == "check":
        print({"db_exists": db_path.exists(), "db_path": str(db_path)})
        return
    if args.mode == "clear":
        os.environ.pop("TICKETING_DB_FORCE_FAIL", None)
        print("cleared local failure flags")
        return
    if args.mode == "lock-db":
        conn = sqlite3.connect(str(db_path))
        conn.execute("BEGIN EXCLUSIVE")
        print("database lock acquired; press Ctrl+C to release")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            conn.close()


if __name__ == "__main__":
    main()

