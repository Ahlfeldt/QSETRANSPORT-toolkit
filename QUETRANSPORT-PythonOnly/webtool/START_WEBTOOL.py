"""Serve the repository locally so Pyodide and Web Workers can run."""
from __future__ import annotations

import http.server
import socketserver
from pathlib import Path

PORT = 8765
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

class ReusableServer(socketserver.TCPServer):
    allow_reuse_address = True

def main() -> None:
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
        *args, directory=str(REPOSITORY_ROOT), **kwargs
    )
    address = f"http://localhost:{PORT}/webtool/"
    print("QUETRANSPORT webtool")
    print(f"Open {address}")
    print("Keep this window open while using the webtool. Press Ctrl+C to stop.")
    with ReusableServer(("127.0.0.1", PORT), handler) as server:
        server.serve_forever()

if __name__ == "__main__":
    main()
