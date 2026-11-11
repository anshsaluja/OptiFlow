#!/usr/bin/env python3
"""Verify server-rendered OptiFlow dashboard routes over HTTP."""
import argparse
import time
import urllib.request

EXPECTED = {
    "/": ("Network overview", "Shipment allocations", "Snapshot loaded"),
    "/scenarios": ("Scenario impact analysis", "Disruption ranking", "Cost drivers"),
}


def check_route(base_url, route, markers, attempts=60, delay=2, timeout=5, opener=None, sleeper=None):
    """Retry startup failures; fail if any required server-rendered marker is absent."""
    opener = opener or urllib.request.urlopen
    sleeper = sleeper or time.sleep
    url = base_url.rstrip("/") + route
    last_error = None
    for attempt in range(attempts):
        try:
            with opener(url, timeout=timeout) as response:
                body = response.read()
                status = response.status
            if status != 200 or not body:
                raise RuntimeError(f"{route}: status={status}, bytes={len(body)}")
            html = body.decode("utf-8")
            missing = [marker for marker in markers if marker not in html]
            if missing:
                raise RuntimeError(f"{route}: missing rendered data markers {missing}")
            print(f"PASS {route}: HTTP {status}, {len(body)} bytes, rendered data verified")
            return
        except (OSError, RuntimeError, UnicodeError) as error:
            last_error = error
            if attempt + 1 < attempts:
                sleeper(delay)
    raise RuntimeError(f"Dashboard route {route} did not become ready: {last_error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--attempts", type=int, default=60)
    parser.add_argument("--delay", type=float, default=2)
    args = parser.parse_args()
    if args.attempts < 1 or args.delay < 0:
        parser.error("attempts must be positive and delay must be nonnegative")
    for route, markers in EXPECTED.items():
        check_route(args.base_url, route, markers, attempts=args.attempts, delay=args.delay)


if __name__ == "__main__":
    main()
