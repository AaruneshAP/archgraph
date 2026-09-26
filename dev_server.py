#!/usr/bin/env python3
"""
Local development server for Phase 5 live demo.
Serves static frontend at / and routes /api/analyze to api/analyze.py handler.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from api.analyze import handler as AnalyzeHandler


class DevServerHandler(AnalyzeHandler, SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        if self.path.startswith("/api/analyze"):
            super().do_OPTIONS()
        else:
            self.send_response(200)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/api/analyze"):
            super().do_POST()
        else:
            self.send_error(404, "Not Found")

    def do_GET(self):
        if self.path in ("/", ""):
            self.path = "/index.html"
        SimpleHTTPRequestHandler.do_GET(self)


def run(port: int = 3000):
    server = HTTPServer(("127.0.0.1", port), DevServerHandler)
    print(f"Phase 5 live demo running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dev server.")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    run(port)
