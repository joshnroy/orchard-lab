"""Holds a live game in memory for the coding agent; play.py talks to it over HTTP.

The hidden parameters arrive on stdin and stay in this process, which runs outside
the agent's sandbox (separate PID namespace, no view of this file system).
Prints the port it listens on, then serves until killed. Writes the finished game
log (browser JSON format) to config["out"].
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

sys.path.insert(0, str(Path(__file__).parent))
from apple_env import AppleEnv, GameLog  # noqa: E402

cfg = json.loads(sys.stdin.read())
TOKEN = cfg["token"]
lock = Lock()
state = dict(round=0, env=None, finished=False)
log = GameLog(cfg["pid"], cfg["config"], cfg["player"])


def new_round():
    state["env"] = AppleEnv(**cfg["rounds"][state["round"]])
    log.start_round(state["env"], state["round"] + 1)


def status_text():
    env, n = state["env"], len(cfg["rounds"])
    head = f"Round {state['round'] + 1} of {n}\n\n" if n > 1 else ""
    notebook = "\n".join(log.round["transcript"][1:])
    tail = ("The game is over." if state["finished"]
            else f"Apples left: {env.apples}. Legal actions: {', '.join(a.upper() for a in env.legal())}.")
    return f"{head}{env.rules_text()}\n\nLab notebook:\n{notebook}\n\n{tail}"


def do_step(action):
    res = state["env"].step(action)
    log.record(res)
    out = res["text"]
    if res["done"]:
        if state["round"] + 1 < len(cfg["rounds"]):
            state["round"] += 1
            new_round()
            out += (f"\n\nRound {state['round'] + 1} of {len(cfg['rounds'])}: a new year. You get a fresh set of "
                    f"{state['env'].p['n']} apples. Your skill starts over, and your starting skill and learning "
                    f"speed may be different from last round. The rules are the same.\n{state['env'].intro_text()}")
        else:
            state["finished"] = True
            log.finish(cfg["out"])
            out += "\n\nThe game is over."
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _reply(self, code, text):
        body = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if body.get("token") != TOKEN:
            return self._reply(403, "bad token")
        with lock:
            if body.get("cmd") == "status":
                return self._reply(200, status_text())
            if state["finished"]:
                return self._reply(409, "The game is over.")
            try:
                return self._reply(200, do_step(body["action"]))
            except (ValueError, KeyError) as e:
                return self._reply(400, f"Not allowed: {e}")


new_round()
srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
print(srv.server_address[1], flush=True)
srv.serve_forever()
