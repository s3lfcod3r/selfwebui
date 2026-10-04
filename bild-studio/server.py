#!/usr/bin/env python3
"""Statischer Server für die Oberfläche "Bonsai & Qwen Image Generator" (Port 8112, nur Heimnetz).

Die Oberfläche spricht aus dem Browser direkt mit dem Bild-Dienst (STUDIO_API, z. B. http://192.168.1.103:8111) und fragt Bonsai (STUDIO_BONSAI) an.
"""
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

WURZEL = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
                      ".html": "text/html; charset=utf-8", ".ttf": "font/ttf"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/config.json":
            daten = json.dumps({"api": os.environ.get("STUDIO_API", ""), "bonsai": os.environ.get("STUDIO_BONSAI", "")}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(daten)))
            self.end_headers()
            self.wfile.write(daten)
            return
        super().do_GET()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8112"))), partial(Handler, directory=WURZEL)).serve_forever()
