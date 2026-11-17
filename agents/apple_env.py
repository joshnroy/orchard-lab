"""Python port of AppleEnv from index.html.

Same dynamics, same rules text, same observation text, and the same mulberry32
random stream, so a given seed gives an LLM exactly the apple luck a human gets
in the browser. Saved games use the browser's JSON log format, so
solver/pomdp.py analyze works on them unchanged.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone


def mulberry32(seed: int):
    a = seed & 0xFFFFFFFF

    def rng() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rng


class AppleEnv:
    def __init__(self, n=20, k0=0.1, lr=0.1, kmax=1.0, demoMult=1.5, demoCost=2, seed=1):
        self.p = dict(n=n, k0=k0, lr=lr, kmax=kmax, demoMult=demoMult, demoCost=demoCost, seed=seed)
        self.reset()

    def reset(self):
        rng = mulberry32(self.p["seed"])
        self.u = [rng() for _ in range(self.p["n"])]  # common random numbers: apple i's luck
        self.idx, self.k, self.apples, self.t, self.done = 0, self.p["k0"], self.p["n"], 0, False
        self.trace = []

    @property
    def demo_enabled(self):
        return self.p["demoMult"] not in (None, "off", 0)

    def _cut(self):
        ok = self.u[self.idx] < self.k
        self.idx += 1
        self.apples -= 1
        return ok

    def _burn(self, c):
        self.idx += c
        self.apples -= c

    def legal(self):
        a = []
        if self.apples >= 1:
            a += ["practice", "review"]
        if self.demo_enabled and self.apples >= self.p["demoCost"]:
            a.append("demo")
        return a + ["defend"]

    def step(self, action: dict):
        if self.done:
            raise ValueError("The game is already over.")
        typ = action["type"]
        before = dict(apples=self.apples, k=self.k)
        if typ == "practice":
            if self.apples < 1:
                raise ValueError("No apples left to practice on.")
            self._burn(1)
            self.k = min(self.p["kmax"], self.k + self.p["lr"])
            obs = dict(type=typ)
        elif typ == "review":
            m = int(action.get("m", 0))
            if not 1 <= m <= self.apples:
                raise ValueError(f"Review size must be between 1 and {self.apples}.")
            outcomes = [self._cut() for _ in range(m)]
            obs = dict(type=typ, m=m, outcomes=outcomes, clean=sum(outcomes))
        elif typ == "demo":
            if not self.demo_enabled:
                raise ValueError("Demonstrations are not available.")
            if self.apples < self.p["demoCost"]:
                raise ValueError(f"A demo needs {self.p['demoCost']} apples.")
            self._burn(self.p["demoCost"])
            self.k = min(self.p["kmax"], self.k + self.p["demoMult"] * self.p["lr"])
            obs = dict(type=typ)
        elif typ == "defend":
            m = self.apples
            outcomes = [self._cut() for _ in range(m)]
            obs = dict(type=typ, m=m, outcomes=outcomes, clean=sum(outcomes))
            self.done = True
        else:
            raise ValueError(f"Unknown action {typ!r}.")
        self.t += 1
        m_used = obs.get("m", 1 if typ == "practice" else self.p["demoCost"] if typ == "demo" else 0)
        rec = dict(t=self.t, action=typ, m=m_used, apples_before=before["apples"], apples_after=self.apples,
                   k_before=before["k"], k_after=self.k, clean=obs.get("clean"))
        self.trace.append(rec)
        return dict(obs=obs, reward=obs["clean"] if typ == "defend" else 0, done=self.done,
                    text=self.obs_text(obs), record=rec)

    def rules_text(self):
        d, p = self.demo_enabled, self.p
        lines = [
            "You are a new apprentice in the Orchard Lab, learning to cut apples cleanly.",
            f"You start with {p['n']} apples. You have some apple-cutting skill, but you do not know how good you are, and you do not know how fast you learn.",
            "",
            "Each day you choose ONE action:",
            "  PRACTICE — practice cutting on 1 apple. Uses 1 apple. Practice improves your skill by an unknown amount. You do not find out whether the practice cut was clean.",
            "  REVIEW m — a mock review: you cut m apples (1 ≤ m ≤ apples left) and are told how many of the m cuts were clean. Uses m apples. Does not change your skill.",
        ]
        if d:
            lines.append(f"  DEMO — ask an expert to show you how it's done. The expert uses {p['demoCost']} apples. Watching improves your skill by an unknown amount. You do not get a score for the expert's cuts.")
        lines += [
            "  DEFEND — finish training and take the final test: you cut ALL of your remaining apples.",
            "",
            f"Your score is the number of clean cuts in the final test. Apples used for practice, reviews{', or demos' if d else ''} do not count toward your score. Try to get the highest score you can.",
        ]
        return "\n".join(lines)

    def intro_text(self):
        return f"Day 0: You arrive at the Orchard Lab with {self.p['n']} apples."

    def obs_text(self, o):
        left = f"Apples left: {self.apples}."
        if o["type"] == "practice":
            return f"Day {self.t}: You practiced cutting on 1 apple. {left}"
        if o["type"] == "demo":
            return f"Day {self.t}: An expert demonstrated cutting on {self.p['demoCost']} apples while you watched. {left}"
        if o["type"] == "review":
            m = o["m"]
            return f"Day {self.t}: Mock review of {m} apple{'s' if m > 1 else ''}: {o['clean']} of {m} cuts were clean. {left}"
        m, c = o["m"], o["clean"]
        return f"Day {self.t}: Final test! You cut {m} apple{'' if m == 1 else 's'}: {c} clean cut{'' if c == 1 else 's'}. Final score: {c}."

    def oracle(self):
        p = self.p
        dm = p["demoMult"] if self.demo_enabled else 0
        best = dict(ev=-1.0)
        for d in range(p["n"] // p["demoCost"] + 1):
            for pr in range(p["n"] - d * p["demoCost"] + 1):
                left = p["n"] - pr - d * p["demoCost"]
                ev = left * min(p["kmax"], p["k0"] + pr * p["lr"] + d * dm * p["lr"])
                if ev > best["ev"] + 1e-12:
                    best = dict(practice=pr, demos=d, ev=ev)
        return best


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class GameLog:
    """Builds a log in the browser's JSON format (one round per AppleEnv)."""

    def __init__(self, pid: str, config: dict, player: dict):
        self.data = dict(pid=pid, started=now_iso(), userAgent=player.get("name", "agent"),
                         player=player, config=config, rounds=[])
        self._ready = time.monotonic()

    def start_round(self, env: AppleEnv, rnd: int):
        self.env = env
        self.round = dict(round=rnd, params=dict(env.p), started=now_iso(), steps=[],
                          transcript=[env.rules_text(), env.intro_text()])
        self.data["rounds"].append(self.round)
        self._ready = time.monotonic()

    def record(self, res, **extra):
        now = time.monotonic()
        step = dict(res["record"], rt_ms=round((now - self._ready) * 1000), ts=now_iso(),
                    outcomes="".join(str(int(x)) for x in res["obs"].get("outcomes", [])), text=res["text"])
        step.update(extra)
        self.round["steps"].append(step)
        self.round["transcript"].append(res["text"])
        if res["done"]:
            env, o = self.env, self.env.oracle()
            last = self.round["steps"][-1]
            self.round["final"] = dict(apples_tested=last["m"], score=res["reward"], k_final=env.k,
                                       expected_score=last["m"] * env.k, oracle_practice=o["practice"],
                                       oracle_demos=o["demos"], oracle_expected=o["ev"], days=env.t)
        self._ready = time.monotonic()

    def finish(self, path, **extra):
        self.data["finished"] = now_iso()
        self.data.update(extra)
        with open(path, "w") as f:
            json.dump(self.data, f, indent=2)
        return path
