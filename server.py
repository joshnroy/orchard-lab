"""Serve the Orchard Lab game and save finished sessions to ./data/*.json."""
import json, os, time, re
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def do_POST(self):
        if self.path.rstrip("/") != "/save":
            self.send_error(404); return
        n = int(self.headers.get("Content-Length", 0))
        if n > 5_000_000: self.send_error(413); return
        body = json.loads(self.rfile.read(n))
        pid = re.sub(r"[^A-Za-z0-9_-]", "_", str(body.get("pid", "anon")))[:40]
        path = os.path.join(DATA, f"{pid}_{int(time.time())}.json")
        with open(path, "w") as f: json.dump(body, f, indent=2)
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Serving on http://agni:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
