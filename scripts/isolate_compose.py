#!/usr/bin/env python3
"""Create an isolated, loopback-only dashboard Compose config from rendered JSON.

Usage: docker compose -f compose.yaml config --format json | python3 scripts/isolate_compose.py 15173 > /tmp/compose.json
The rendered configuration retains absolute bind paths and named-volume definitions.
"""
import json
import sys


def isolate(config, port):
    if isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535:
        raise ValueError("Host port must be an integer between 1024 and 65535")
    if not isinstance(config, dict) or not isinstance(config.get("services"), dict):
        raise ValueError("Expected rendered Compose services")
    dashboard = config["services"].get("dashboard")
    if not isinstance(dashboard, dict):
        raise ValueError("Missing dashboard service")
    mappings = dashboard.get("ports")
    if not isinstance(mappings, list) or len(mappings) != 1:
        raise ValueError("Dashboard must publish exactly one port")
    mapping = mappings[0]
    if not isinstance(mapping, dict):
        raise ValueError("Expected normalized Compose port mapping")
    target = mapping.get("target")
    published = mapping.get("published")
    host_ip = mapping.get("host_ip", "127.0.0.1")
    protocol = mapping.get("protocol", "tcp")
    if str(target) != "5173" or str(published) != "5173":
        raise ValueError("Unexpected dashboard port mapping")
    if host_ip not in ("127.0.0.1", "::1") or protocol != "tcp":
        raise ValueError("Dashboard port must be loopback-only TCP")
    dashboard["ports"] = [{
        "mode": "ingress", "target": 5173, "published": str(port),
        "host_ip": "127.0.0.1", "protocol": "tcp",
    }]
    return config


def main():
    if len(sys.argv) != 2:
        raise ValueError("Usage: isolate_compose.py HOST_PORT")
    port = int(sys.argv[1])
    config = json.load(sys.stdin)
    json.dump(isolate(config, port), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Invalid Compose configuration: {exc}", file=sys.stderr)
        sys.exit(2)
