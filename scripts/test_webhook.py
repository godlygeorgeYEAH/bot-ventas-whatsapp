#!/usr/bin/env python3
"""
Simple script to POST a JSON payload to a webhook using requests.
Usage:
    python scripts/post_webhook.py
    python scripts/post_webhook.py --url http://localhost:8000/webhook/waha
    python scripts/post_webhook.py --data-file payload.json

Requires: requests (pip install requests)
"""

import argparse
import json
import sys
from pathlib import Path

import requests

DEFAULT_URL = "http://localhost:8000/webhook/waha"
DEFAULT_PAYLOAD = {
    "event": "message",
    "payload": {
        "from": "1234567890@c.us",
        "body": "Hola, quiero hacer un pedido",
        "type": "chat",
    },
}


def load_payload_from_file(path: str):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Payload file not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON in payload file: {e}")


def main():
    parser = argparse.ArgumentParser(description="POST a JSON payload to a webhook using requests.")
    parser.add_argument("--url", "-u", default=DEFAULT_URL, help="Webhook URL")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--data-file", "-f", help="Path to JSON file to send as body")
    group.add_argument("--data-json", "-j", help='Raw JSON string to send (useful for CI)')
    parser.add_argument("--timeout", "-t", type=float, default=10.0, help="Request timeout in seconds")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON response when possible")

    args = parser.parse_args()

    if args.data_file:
        payload = load_payload_from_file(args.data_file)
    elif args.data_json:
        try:
            payload = json.loads(args.data_json)
        except json.JSONDecodeError as e:
            raise SystemExit(f"Invalid JSON provided to --data-json: {e}")
    else:
        payload = DEFAULT_PAYLOAD

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(args.url, json=payload, headers=headers, timeout=args.timeout)
    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(2)

    print(f"HTTP {resp.status_code} {resp.reason}")

    content_type = resp.headers.get("Content-Type", "")
    text = resp.text

    if args.pretty and "application/json" in content_type:
        try:
            parsed = resp.json()
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except Exception:
            print(text)
    else:
        print(text)

    # exit non-zero for non-2xx responses
    if not (200 <= resp.status_code < 300):
        sys.exit(3)


if __name__ == "__main__":
    main()
