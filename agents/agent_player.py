"""Coding-agent player: Claude Code with shell and file tools plays the game.

Adapted from robocode's agentic approach (src/robocode/utils/backends/claude.py):
`claude -p --output-format stream-json --dangerously-skip-permissions` with
Bash/Read/Write/Edit/Glob/Grep, the task prompt on stdin, and a system prompt
file. The agent can write and run any code it likes, but it acts on the game
only through `python3 play.py <action>`, once per game day, like a human clicking.

Isolation (robocode uses Docker/Apptainer; here bubblewrap):
  * The hidden parameters live only in game_server.py's memory, outside the sandbox.
  * The agent sees an empty home with just its work directory, read-only system
    dirs, and Python. It can't see this repo, saved participant logs, or your
    Claude history. It has its own PID namespace, so it can't inspect the server.
  * Claude auth is a private copy of your CLI credentials, synced back afterwards
    if the CLI refreshed the token (as robocode's claude_auth.py does).

Usage:
  python agents/agent_player.py --seed 381892
  python agents/agent_player.py --k0 0.1 --lr 0.1 --demo 3 --rounds 3 --effort high
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
CLAUDE_BIN = Path(shutil.which("claude") or HOME / ".local/bin/claude").resolve()
CONDA = HOME / "miniconda3"

SYSTEM_PROMPT = """You are an autonomous agent working in a sandboxed directory with shell and file tools.
Complete the task you are given on your own; there is no human to answer questions."""

TASK = """You are going to play a decision-making game.

{header}{rules}

{intro}

How to play: in your working directory, run
  python3 play.py status       show the rules, your notebook so far, and apples left (free; not an action)
  python3 play.py practice
  python3 play.py review M     (M = number of apples)
{demo_line}  python3 play.py defend

Every command except `status` uses up one game day and cannot be undone.
You may write and run any code you like to help you decide (Python 3 with numpy and scipy is available).
Nothing in this environment reveals the hidden values; decide from what you observe.
Play until the game is over, then reply with a short summary of your strategy."""


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def make_home(run_dir: Path) -> Path:
    home = run_dir / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    shutil.copy2(HOME / ".claude/.credentials.json", home / ".claude/.credentials.json")
    os.chmod(home / ".claude/.credentials.json", 0o600)
    full = json.loads((HOME / ".claude.json").read_text())
    keep = {k: full[k] for k in ("hasCompletedOnboarding", "oauthAccount", "userID") if k in full}
    (home / ".claude.json").write_text(json.dumps(keep))
    return home


def sync_credentials(home: Path, host_hash_before: str | None):
    """If the sandboxed CLI refreshed its token, copy it back so the host login stays valid."""
    inner, host = home / ".claude/.credentials.json", HOME / ".claude/.credentials.json"
    if sha(inner) == host_hash_before:
        return "unchanged"
    if sha(host) != host_hash_before:
        return "host changed during run; left host credentials alone"
    shutil.copy2(inner, host)
    return "refreshed token copied back to host"


def bwrap_cmd(home: Path, work: Path, claude_args: list[str]) -> list[str]:
    cmd = ["bwrap", "--die-with-parent", "--unshare-pid", "--unshare-ipc", "--unshare-uts", "--new-session",
           "--ro-bind", "/usr", "/usr", "--ro-bind", "/etc", "/etc", "--ro-bind", "/sys", "/sys",
           "--symlink", "usr/bin", "/bin", "--symlink", "usr/sbin", "/sbin",
           "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
           "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--tmpfs", "/home", "--tmpfs", "/run"]
    if Path("/run/systemd/resolve").exists():
        cmd += ["--ro-bind", "/run/systemd/resolve", "/run/systemd/resolve"]
    cmd += ["--bind", str(home), "/home/agent", "--bind", str(work), "/home/agent/work",
            "--ro-bind", str(CLAUDE_BIN), "/opt/claude/claude"]
    path = "/usr/bin:/bin"
    if CONDA.exists():  # same path as on the host: conda's prefix is hard-coded
        cmd += ["--ro-bind", str(CONDA), str(CONDA)]
        path = f"{CONDA}/bin:{path}"
    cmd += ["--chdir", "/home/agent/work", "--clearenv",
            "--setenv", "HOME", "/home/agent", "--setenv", "USER", "agent", "--setenv", "PATH", path,
            "--setenv", "LANG", "C.UTF-8", "--setenv", "TERM", "dumb", "/opt/claude/claude"]
    return cmd + claude_args


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="", help="Claude Code --effort (low/medium/high/xhigh/max); robocode main added this")
    ap.add_argument("--budget", type=float, default=5.0, help="max USD for the agent run")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--k0", default="0.1")
    ap.add_argument("--lr", default="0.1")
    ap.add_argument("--demo", default="1.5")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--pid", default=None)
    ap.add_argument("--timeout", type=float, default=1800)
    a = ap.parse_args()

    k0s, lrs = [float(x) for x in a.k0.split(",")], [float(x) for x in a.lr.split(",")]
    demo = None if a.demo == "off" else float(a.demo)
    pid = a.pid or f"agent_{a.model}_s{a.seed}"
    stamp = int(time.time())
    run_dir = ROOT / "agents" / "runs" / f"{pid}_{stamp}"
    work = run_dir / "work"
    work.mkdir(parents=True)
    out = ROOT / "data" / f"{pid}_{stamp}.json"
    out.parent.mkdir(exist_ok=True)

    rounds = [dict(n=a.n, k0=k0s[r % len(k0s)], lr=lrs[r % len(lrs)], demoMult=demo, seed=a.seed + r * 7919)
              for r in range(a.rounds)]
    token = secrets.token_hex(16)
    config = dict(pid=pid, n=a.n, rounds=a.rounds, k=k0s, lr=lrs, demoMult=demo, seed=a.seed, kmax=1, debug=False)
    server = subprocess.Popen(["python3", str(ROOT / "agents/game_server.py")], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, text=True)
    server.stdin.write(json.dumps(dict(token=token, rounds=rounds, pid=pid, config=config, out=str(out),
                                       player=dict(name="coding_agent", model=a.model, effort=a.effort))))
    server.stdin.close()
    port = int(server.stdout.readline())

    shutil.copy2(ROOT / "agents/play.py", work / "play.py")
    (work / ".game.json").write_text(json.dumps(dict(port=port, token=token)))
    (work / ".agent").mkdir()
    (work / ".agent/system_prompt.md").write_text(SYSTEM_PROMPT)

    from apple_env import AppleEnv  # noqa: E402
    env0 = AppleEnv(**rounds[0])
    task = TASK.format(header=f"The game has {a.rounds} rounds.\n\n" if a.rounds > 1 else "",
                       rules=env0.rules_text(), intro=env0.intro_text(),
                       demo_line="  python3 play.py demo\n" if env0.demo_enabled else "")
    (run_dir / "task_prompt.md").write_text(task)

    claude_args = ["-p", "--output-format", "stream-json", "--verbose", "--model", a.model,
                   "--dangerously-skip-permissions", "--tools", "Bash,Read,Write,Edit,Glob,Grep",
                   "--setting-sources", "project", "--system-prompt-file", ".agent/system_prompt.md",
                   "--max-budget-usd", str(a.budget)]
    if a.effort:
        claude_args += ["--effort", a.effort]

    home = make_home(run_dir)
    host_hash = sha(HOME / ".claude/.credentials.json")
    print(f"[{pid}] agent running in {run_dir}", flush=True)
    t0 = time.time()
    try:
        with open(run_dir / "stream.jsonl", "w") as stream:
            r = subprocess.run(bwrap_cmd(home, work, claude_args), input=task, stdout=stream,
                               stderr=open(run_dir / "stderr.txt", "w"), text=True, timeout=a.timeout)
        rc = r.returncode
    except subprocess.TimeoutExpired:
        rc = "timeout"
    finally:
        cred = sync_credentials(home, host_hash)
        shutil.rmtree(home, ignore_errors=True)  # don't leave a token or account info on disk
        server.terminate()

    result = {}
    for line in open(run_dir / "stream.jsonl"):
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            result = ev
    summary = dict(returncode=rc, seconds=round(time.time() - t0), cost_usd=result.get("total_cost_usd"),
                   num_turns=result.get("num_turns"), final_reply=result.get("result"), credentials=cred,
                   game_log=str(out) if out.exists() else None)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    if out.exists():
        d = json.loads(out.read_text())
        d.update(agent_summary=summary, run_dir=str(run_dir))
        out.write_text(json.dumps(d, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    main()
