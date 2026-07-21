#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 AI Act SME Compliance Engine contributors
"""Local static dev server for web/ (ADR-013). Identical to
`python -m http.server` except it pins the module/wasm MIME types that some
platforms' mimetypes registry omits (notably .mjs -> text/plain on Windows,
which browsers reject for ES modules). The production target (GitHub Pages)
serves these correctly; this is only for the local serve/e2e. Zero exfiltration
is a property of the PAGE (CSP), not the server. Usage: serve_web.py [PORT]."""
import http.server
import os
import sys

MIME = {".mjs": "text/javascript", ".js": "text/javascript",
        ".wasm": "application/wasm", ".json": "application/json"}


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, **MIME}

    def end_headers(self):
        # dev server: never cache, so a corrected MIME/asset is always re-fetched
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web"))
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    # ThreadingHTTPServer (like `python -m http.server`): Pyodide fetches its
    # runtime assets in PARALLEL; a single-threaded server deadlocks on them.
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"serving web/ on http://127.0.0.1:{port} (Ctrl-C to stop)")
        httpd.serve_forever()
