"""Minimal stdio client for the Altium MCP server.

usage: python -I mcpcall.py <tool_name> [json_args | @file.json]
Prints the tool's text result to stdout.
"""
import json
import os
import subprocess
import sys

SERVER = os.path.join(os.environ["USERPROFILE"], "mcp-servers", "altium-mcp", "start_server.py")


def call(tool, args, timeout=900):
    proc = subprocess.Popen(
        [sys.executable, SERVER],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8",
    )

    def send(msg):
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def recv(want_id):
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            if msg.get("id") == want_id:
                return msg
        raise RuntimeError("server closed before replying")

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                     "clientInfo": {"name": "mcpcall", "version": "0"}}})
    recv(1)
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": tool, "arguments": args}})
    try:
        msg = recv(2)
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    if "error" in msg:
        return json.dumps(msg["error"])
    return "\n".join(c.get("text", "") for c in msg["result"].get("content", []))


if __name__ == "__main__":
    tool = sys.argv[1]
    raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
    if raw.startswith("@"):
        with open(raw[1:], encoding="utf-8") as f:
            raw = f.read()
    print(call(tool, json.loads(raw)))
