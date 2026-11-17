"""Score many saved games against the Bayes-optimal policy and summarize by player.

  python analysis/aggregate.py data/*.json [--csv analysis/games.csv]

For each game: score, expected score (apples defended × final skill), expected
points lost against the observed-information optimal policy (solver/pomdp.py,
default prior), number of reviews, and apples spent on each kind of action.
Games are grouped by player type (from the log's "player" field or pid prefix).
"""
import argparse
import csv
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "solver"))
from pomdp import Solver, make_prior  # noqa: E402

PRIOR = make_prior([0, .1, .2, .3, .4, .5], [.025, .05, .1, .15, .2], [1.5, 3])
_solvers = {}


def solver_for(demo_on):
    if demo_on not in _solvers:
        _solvers[demo_on] = Solver(PRIOR, demo_enabled=demo_on)
    return _solvers[demo_on]


def game_loss(R):
    pr = R["params"]
    s = solver_for(pr.get("demoMult") not in (None, "off", 0))
    A, P, D, b, loss = pr["n"], 0, 0, PRIOR["b0"], 0.0
    for stp in R["steps"]:
        a_star, q = s.best(A, P, D, b)
        act = stp["action"]
        key = ("review", stp["m"]) if act == "review" else act
        if key not in q:
            q[key] = s.review_value(A, P, D, b, stp["m"])
        loss += q[a_star] - q[key]
        if act == "practice":
            A -= 1; P += 1
        elif act == "demo":
            A -= 2; D += 1
        elif act == "review":
            b = s.update(P, D, stp["m"], stp["clean"], b); A -= stp["m"]
    return loss


def player_type(d):
    p = d.get("player", {})
    name = {"llm_only": "LLM only", "coding_agent": "Coding agent"}.get(p.get("name"), "Human")
    if name != "Human" and p.get("model", "claude-opus-5-5") != "claude-opus-5-5":
        name += f" ({p['model']}"
        name += f", effort {p['effort']})" if p.get("effort") not in (None, "", "cli-default") else ")"
    return name


def summarize(paths):
    rows = []
    for path in paths:
        d = json.load(open(path))
        for R in d.get("rounds", []):
            if "final" not in R:
                continue
            steps = R["steps"]
            spent = defaultdict(int)
            for stp in steps:
                spent[stp["action"]] += stp["m"]
            rows.append(dict(
                file=Path(path).name, pid=d["pid"], player=player_type(d), seed=R["params"]["seed"],
                round=R["round"], score=R["final"]["score"], defended=R["final"]["apples_tested"],
                clean_pct=round(100 * R["final"]["score"] / R["final"]["apples_tested"], 1) if R["final"]["apples_tested"] else None,
                final_skill=round(R["final"]["k_final"], 3),
                expected=round(R["final"]["expected_score"], 3), loss=round(game_loss(R), 3),
                reviews=sum(s["action"] == "review" for s in steps),
                apples_practice=spent["practice"], apples_demo=spent["demo"], apples_review=spent["review"],
                days=R["final"]["days"], cost_usd=d.get("cost_usd") or (d.get("agent_summary") or {}).get("cost_usd")))
    return rows


def mean_ci(xs):
    if not xs:
        return "–"
    m = st.mean(xs)
    if len(xs) < 2:
        return f"{m:.2f}"
    return f"{m:.2f} ± {1.96 * st.stdev(xs) / math.sqrt(len(xs)):.2f}"


def table(rows, by=("player",)):
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in by)].append(r)
    cols = ["score", "defended", "clean_pct", "final_skill", "expected", "loss", "reviews", "apples_review"]
    out = ["| " + " | ".join(by) + " | games | " + " | ".join(cols) + " |",
           "|" + "---|" * (len(by) + 1 + len(cols))]
    for key in sorted(groups):
        g = groups[key]
        out.append("| " + " | ".join(str(k) for k in key) + f" | {len(g)} | " +
                   " | ".join(mean_ci([r[c] for r in g if r[c] is not None]) for c in cols) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--csv")
    a = ap.parse_args()
    rows = summarize(a.logs)
    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)
    print(table(rows)); print(); print(table(rows, ("player", "seed")))
