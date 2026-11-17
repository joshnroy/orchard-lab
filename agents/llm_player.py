"""LLM-only player: one plain completion per game day, no tools.

Adapted from robocode's ClaudeCLIClient (src/robocode/utils/llm/cli_client.py):
`claude -p` with built-in and MCP tools disabled and the system prompt emptied,
resuming the same CLI session each turn so the model sees one continuous
conversation. As in robocode, the CLI keeps an irreducible ~2k-token preamble.

The model sees exactly the human's text: the rules scroll, then one Lab
Notebook line per day. The only addition is the answer-format instruction.

Usage:
  python agents/llm_player.py --seed 381892 --model claude-opus-5-5
  python agents/llm_player.py --k0 0.1 --lr 0.1 --demo 3 --rounds 3 --thinking 8000
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from apple_env import AppleEnv, GameLog  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FORMAT = (
    "Think it through however you like, then end your reply with one line in exactly one of these forms:\n"
    "ACTION: PRACTICE\nACTION: REVIEW m   (m = number of apples, e.g. ACTION: REVIEW 3)\n"
    "{demo}ACTION: DEFEND"
)
ACTION_RE = re.compile(r"ACTION:\s*(PRACTICE|DEMO|DEFEND|REVIEW\s+(\d+))\b", re.I)


class ClaudeCLI:
    """Plain-LLM completions through the Claude CLI, continuing one session."""

    def __init__(self, model: str, thinking: int = 0, timeout: float = 600):
        self.model, self.thinking, self.timeout = model, thinking, timeout
        self.session_id = None
        self.cost = 0.0

    def send(self, text: str) -> str:
        args = ["claude", "-p", "--output-format", "json", "--model", self.model,
                "--tools", "", "--disallowedTools", "*", "--system-prompt", "",
                "--exclude-dynamic-system-prompt-sections",
                "--max-thinking-tokens", str(self.thinking)]
        if self.session_id:
            args += ["--resume", self.session_id]
        # Clean environment: when launched from inside Claude Code / the desktop app, the
        # parent's session and auth-proxy variables would otherwise hijack the CLI's login.
        env = {k: os.environ[k] for k in ("HOME", "PATH", "LANG", "USER", "TERM") if k in os.environ}
        # Run from an empty directory so no project CLAUDE.md or settings leak in.
        cwd = ROOT / "agents" / ".llm_cwd"
        cwd.mkdir(exist_ok=True)
        r = subprocess.run(args, input=text, capture_output=True, text=True, env=env,
                           cwd=cwd, timeout=self.timeout)
        if r.returncode != 0:
            raise RuntimeError(f"claude exited {r.returncode}: {r.stdout[-2000:]} {r.stderr[-2000:]}")
        data = json.loads(r.stdout)
        if data.get("is_error"):
            raise RuntimeError(f"claude error: {data}")
        self.session_id = data["session_id"]
        self.cost += data.get("total_cost_usd") or 0.0
        return data["result"]


def parse_action(reply: str):
    matches = ACTION_RE.findall(reply)
    if not matches:
        return None
    word, m = matches[-1]
    word = word.split()[0].upper()
    return {"type": "review", "m": int(m)} if word == "REVIEW" else {"type": word.lower()}


def play_round(llm: ClaudeCLI, env: AppleEnv, log: GameLog, first: bool, rnd: int, rounds: int, max_retries=3):
    fmt = FORMAT.format(demo="ACTION: DEMO\n" if env.demo_enabled else "")
    if first:
        header = (f"This game has {rounds} rounds. " if rounds > 1 else "")
        msg = f"{header}{env.rules_text()}\n\n{env.intro_text()}\n\n{fmt}"
    else:
        msg = (f"Round {rnd} of {rounds}: a new year. You get a fresh set of {env.p['n']} apples. Your skill starts over, "
               f"and your starting skill and learning speed may be different from last round. The rules are the same.\n\n"
               f"{env.intro_text()}\n\n{fmt}")
    while not env.done:
        reply, action, err = llm.send(msg), None, None
        for _ in range(max_retries + 1):
            action = parse_action(reply)
            try:
                if action is None:
                    raise ValueError("I couldn't find an ACTION line.")
                res = env.step(action)
                break
            except ValueError as e:
                err = str(e)
                log.data.setdefault("invalid_replies", []).append(dict(round=rnd, day=env.t + 1, reply=reply, error=err))
                reply = llm.send(f"That action isn't possible: {err} Apples left: {env.apples}. Please choose again.\n\n{fmt}")
        else:
            raise RuntimeError(f"No valid action after {max_retries} retries: {err}")
        log.record(res, reply=reply)
        print(f"  {res['text']}", flush=True)
        msg = res["text"] if res["done"] else f"{res['text']}\n\nWhat do you do next?"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--thinking", type=int, default=0, help="max thinking tokens (0 = off, as in robocode)")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--k0", default="0.1", help="comma list = one per round")
    ap.add_argument("--lr", default="0.1", help="comma list = one per round")
    ap.add_argument("--demo", default="1.5", help="1.5, 3, or off")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--pid", default=None)
    ap.add_argument("--out", default=str(ROOT / "data"))
    a = ap.parse_args()

    k0s, lrs = [float(x) for x in a.k0.split(",")], [float(x) for x in a.lr.split(",")]
    demo = None if a.demo == "off" else float(a.demo)
    pid = a.pid or f"llm_{a.model}_t{a.thinking}_s{a.seed}"
    config = dict(pid=pid, n=a.n, rounds=a.rounds, k=k0s, lr=lrs, demoMult=demo, seed=a.seed, kmax=1, debug=False)
    llm = ClaudeCLI(a.model, a.thinking)
    log = GameLog(pid, config, dict(name="llm_only", model=a.model, thinking=a.thinking))
    for r in range(a.rounds):
        env = AppleEnv(n=a.n, k0=k0s[r % len(k0s)], lr=lrs[r % len(lrs)], demoMult=demo, seed=a.seed + r * 7919)
        log.start_round(env, r + 1)
        print(f"[{pid}] round {r+1}", flush=True)
        play_round(llm, env, log, r == 0, r + 1, a.rounds)
    Path(a.out).mkdir(exist_ok=True)
    path = log.finish(Path(a.out) / f"{pid}_{int(__import__('time').time())}.json",
                      cost_usd=llm.cost, session_id=llm.session_id)
    print(f"saved {path}  (cost ${llm.cost:.3f})")


if __name__ == "__main__":
    main()
