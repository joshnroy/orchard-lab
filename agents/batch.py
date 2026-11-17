"""Run repeated games for the LLM players.

  python agents/batch.py --player llm   --seeds 381892,513651 --reps 10 --jobs 5
  python agents/batch.py --player agent --seeds 381892,513651 --reps 10 --jobs 1

Logs land in data/ as <tag>_<player>_s<seed>_r<NN>_<time>.json. Coding-agent runs
default to one at a time: each run holds a copy of the CLI's OAuth token, and two
copies refreshing at once would invalidate each other (see robocode's claude_auth.py).
Extra options (e.g. --model, --thinking, --effort) are passed through to the player.
"""
import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = {"llm": "agents/llm_player.py", "agent": "agents/agent_player.py"}


def run(player, seed, rep, tag, extra):
    pid = f"{tag}_{player}_s{seed}_r{rep:02d}"
    log = ROOT / "data" / "batch_logs" / f"{pid}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w") as f:
        rc = subprocess.run([sys.executable, str(ROOT / SCRIPT[player]), "--seed", str(seed), "--pid", pid, *extra],
                            stdout=f, stderr=subprocess.STDOUT, cwd=ROOT).returncode
    print(f"{pid}: {'ok' if rc == 0 else f'FAILED ({rc}), see {log}'}", flush=True)
    return rc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--player", choices=SCRIPT, required=True)
    ap.add_argument("--seeds", default="381892,513651")
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--jobs", type=int, default=None)
    ap.add_argument("--tag", default="rep")
    a, extra = ap.parse_known_args()
    jobs = a.jobs or (5 if a.player == "llm" else 1)
    tasks = [(int(s), r) for s in a.seeds.split(",") for r in range(1, a.reps + 1)]
    with ThreadPoolExecutor(jobs) as ex:
        rcs = list(ex.map(lambda t: run(a.player, t[0], t[1], a.tag, extra), tasks))
    print(f"{rcs.count(0)}/{len(rcs)} succeeded")


if __name__ == "__main__":
    main()
