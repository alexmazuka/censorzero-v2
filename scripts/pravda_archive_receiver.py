#!/usr/bin/env python3
"""Localhost receiver for the browser-assisted collection of pravda.com.ua
day-archive index pages (they sit behind a bot challenge, so they are fetched
once from a real, logged-in-to-nothing browser session; see PREREGISTRATION.md
section 6 and docs/DATA_DICTIONARY.md).

Run:  python3 scripts/pravda_archive_receiver.py
Then, in a browser tab already on https://www.pravda.com.ua/, run the loop in
scripts/pravda_archive_browser.js. Each day's raw HTML is stored gzipped as
data/raw/discovery/pravda_day_archives/YYYY-MM-DD.html.gz. Existing files are
never overwritten (immutability).
"""

import gzip
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "discovery" / "pravda_day_archives"
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        # Allow a public HTTPS page to POST to this loopback server: standard
        # CORS plus the Private Network Access grant Chrome 104+ requires.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        day = self.path.split("day=")[-1]
        if not DAY_RE.match(day):
            self.send_response(400)
            self._cors()
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        OUT.mkdir(parents=True, exist_ok=True)
        dest = OUT / f"{day}.html.gz"
        if not dest.exists() and length > 0:
            with gzip.open(dest, "wb") as fh:
                fh.write(body)
        self.send_response(204)
        self._cors()
        self.end_headers()

    def log_message(self, *args):  # quiet
        pass


if __name__ == "__main__":
    print(f"receiving into {OUT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8377), Handler).serve_forever()
