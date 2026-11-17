"""Bayes-optimal expectimax solver for the Orchard Lab apple task.

The player doesn't know their starting skill k0, learning rate lr, or how much a
demo helps (demoMult). We model that as a POMDP over a discrete grid of
hypotheses theta = (k0, lr, demoMult) with a prior. Everything except
reviews is deterministic given theta:

    skill(theta, P, D) = min(kmax, k0 + lr * (P + demoMult * D))

where P = practices so far and D = demos so far. Only reviews give
observations (c clean of m ~ Binomial(m, skill)), so the belief is the prior
times the review likelihoods. Expectimax over (apples, P, D, belief):

    V = max( defend:   A * E_b[skill]
             practice: V(A-1, P+1, D,   b)
             demo:     V(A-2, P,   D+1, b)
             review m: sum_c Pr(c|b) V(A-m, P, D, b|c) )

States are memoized on (A, P, D, rounded belief), which merges review histories
that lead to the same belief.

Two objectives (--objective):
  score    maximize expected clean cuts at the defense: terminal = A * skill   (the game's score)
  perfect  maximize P(every defended apple is clean): terminal = skill ** A,
           counted only if A >= --min-defend (default 1), otherwise 0

Usage:
  python solver/pomdp.py solve   [--n 20] [prior options]
  python solver/pomdp.py analyze data/orchard_X.json   # Q-values at each of a player's steps
  python solver/pomdp.py oracle  --k0 0.1 --lr 0.1 --demo 1.5  # sanity check: point-mass prior
"""
import argparse, json, math, sys, time
import numpy as np


# ---------------------------------------------------------------- prior
def floats(s):
    return [float(x) for x in str(s).split(",") if x.strip()]


def make_prior(k0s, lrs, demos, kmax=1.0):
    K0, LR, DM = np.meshgrid(k0s, lrs, demos, indexing="ij")
    K0, LR, DM = K0.ravel(), LR.ravel(), DM.ravel()
    b = np.full(K0.size, 1.0 / K0.size)
    return dict(K0=K0, LR=LR, DM=DM, kmax=kmax, b0=b)


# ---------------------------------------------------------------- solver
class Solver:
    def __init__(self, prior, demo_cost=2, demo_enabled=True, round_dp=10, objective="score", min_defend=1):
        self.p = prior
        self.objective = objective
        self.min_defend = min_defend
        self.demo_cost = demo_cost
        self.demo_enabled = demo_enabled
        self.round_dp = round_dp
        self.memo = {}
        self._lik = {}

    def skill(self, P, D):
        p = self.p
        return np.minimum(p["kmax"], p["K0"] + p["LR"] * (P + p["DM"] * D))

    def lik(self, P, D, m):
        """lik[c] = per-hypothesis probability of c clean cuts out of m."""
        key = (P, D, m)
        if key not in self._lik:
            k = self.skill(P, D)
            self._lik[key] = np.array([math.comb(m, c) * k**c * (1 - k) ** (m - c) for c in range(m + 1)])
        return self._lik[key]

    def terminal(self, A, k):
        """Value of defending with A apples at skill k (k may be a per-hypothesis vector)."""
        if self.objective == "score":
            return A * k
        return k**A if A >= self.min_defend else 0 * k

    def key(self, A, P, D, b):
        return (A, P, D, hash(np.round(b, self.round_dp).tobytes()))

    def fi(self, A, P, D):
        """Full-information value per hypothesis: best fixed practice/demo plan if theta were known.
        Upper bound on V for every belief, and linear in b, so reviewing can't raise E_b[fi]."""
        key = ("fi", A, P, D)
        if key not in self._lik:
            best = self.terminal(A, self.skill(P, D))
            for d in range(0, (A // self.demo_cost if self.demo_enabled else 0) + 1):
                for pr in range(0, A - d * self.demo_cost + 1):
                    best = np.maximum(best, self.terminal(A - pr - d * self.demo_cost, self.skill(P + pr, D + d)))
            self._lik[key] = best
        return self._lik[key]

    def review_value(self, A, P, D, b, m):
        L = self.lik(P, D, m)
        pc = L @ b
        v = 0.0
        for c in range(m + 1):
            if pc[c] > 1e-15:
                v += pc[c] * self.V(A - m, P, D, b * L[c] / pc[c])
        return v

    def q_values(self, A, P, D, b, prune=False):
        """Action values at a state: {'defend': v, 'practice': v, 'demo': v, ('review', m): v}.
        With prune=True, reviews that provably can't beat the best action so far are skipped
        (bound: E_b[fi(A-m)]), so the max is still exact but pruned entries are missing."""
        q = {"defend": float(b @ self.terminal(A, self.skill(P, D)))}
        if A >= 1:
            q["practice"] = self.V(A - 1, P + 1, D, b)
        if self.demo_enabled and A >= self.demo_cost:
            q["demo"] = self.V(A - self.demo_cost, P, D + 1, b)
        for m in range(1, A):  # reviewing all apples leaves nothing to defend: never useful
            if prune and float(b @ self.fi(A - m, P, D)) <= max(q.values()) + 1e-12:
                break  # fi shrinks as m grows, so every larger review is pruned too
            q[("review", m)] = self.review_value(A, P, D, b, m)
        return q

    def V(self, A, P, D, b):
        k = self.key(A, P, D, b)
        v = self.memo.get(k)
        if v is None:
            v = self.memo[k] = max(self.q_values(A, P, D, b, prune=True).values())
        return v

    ORDER = {"defend": 0, "practice": 1, "demo": 2}

    def best(self, A, P, D, b, full=False):
        """Optimal action; near-ties go to defend, then practice, demo, then the smallest review."""
        q = self.q_values(A, P, D, b, prune=not full)
        top = max(q.values())
        rank = lambda a: (self.ORDER[a], 0) if isinstance(a, str) else (3, a[1])
        a = min((x for x in q if q[x] >= top - 1e-9), key=rank)
        return a, q

    def update(self, P, D, m, c, b):
        L = self.lik(P, D, m)[c]
        post = b * L
        return post / post.sum()

    # ---- evaluate the Bayes-optimal policy against fixed true parameters
    def policy_value_true(self, A, P, D, b, theta):
        k0, lr, dm = theta
        kt = min(self.p["kmax"], k0 + lr * (P + dm * D))
        a, _ = self.best(A, P, D, b)
        if a == "defend":
            return float(self.terminal(A, kt))
        if a == "practice":
            return self.policy_value_true(A - 1, P + 1, D, b, theta)
        if a == "demo":
            return self.policy_value_true(A - self.demo_cost, P, D + 1, b, theta)
        m = a[1]
        return sum(math.comb(m, c) * kt**c * (1 - kt) ** (m - c)
                   * self.policy_value_true(A - m, P, D, self.update(P, D, m, c, b), theta)
                   for c in range(m + 1))


def fmt(a):
    return f"review {a[1]}" if isinstance(a, tuple) else a


def plan_tree(s, A, P, D, b, depth=0, max_depth=6, out=None):
    """Readable optimal plan: deterministic chains collapsed, review branches expanded."""
    out = out if out is not None else []
    steps = []
    while True:
        a, q = s.best(A, P, D, b)
        if a == "practice":
            steps.append("practice"); A -= 1; P += 1; continue
        if a == "demo":
            steps.append("demo"); A -= s.demo_cost; D += 1; continue
        break
    pad = "    " * depth
    if steps:
        out.append(pad + compress(steps))
    if a == "defend":
        out.append(pad + f"defend with {A} apples  (value {q['defend']:.3f})")
        return out
    m = a[1]
    out.append(pad + f"review {m}  (value {q[a]:.2f})")
    if depth >= max_depth:
        out.append(pad + "    …")
        return out
    L = s.lik(P, D, m); pc = L @ b
    for c in range(m + 1):
        if pc[c] > 1e-9:
            out.append(pad + f"  if {c}/{m} clean (p={pc[c]:.2f}):")
            plan_tree(s, A - m, P, D, b * L[c] / pc[c], depth + 1, max_depth, out)
    return out


def compress(steps):
    out, i = [], 0
    while i < len(steps):
        j = i
        while j < len(steps) and steps[j] == steps[i]:
            j += 1
        out.append(f"{steps[i]} ×{j-i}" if j - i > 1 else steps[i])
        i = j
    return " → ".join(out)


# ---------------------------------------------------------------- CLI
def build(args, demo_enabled=True):
    prior = make_prior(floats(args.k0_grid), floats(args.lr_grid), floats(args.demo_grid), args.kmax)
    return Solver(prior, demo_enabled=demo_enabled, objective=args.objective, min_defend=args.min_defend), prior


def cmd_solve(args):
    s, prior = build(args, demo_enabled=not args.no_demo)
    t = time.time()
    a, q = s.best(args.n, 0, 0, prior["b0"])
    print(f"prior: {prior['b0'].size} hypotheses  k0∈{floats(args.k0_grid)}  lr∈{floats(args.lr_grid)}  demo×∈{floats(args.demo_grid)}")
    print(f"solved n={args.n} in {time.time()-t:.1f}s, {len(s.memo):,} belief states")
    print(f"objective={args.objective}: Bayes-optimal value {max(q.values()):.3f}\n")
    print("Optimal plan:")
    print("\n".join(plan_tree(s, args.n, 0, 0, prior["b0"], max_depth=args.depth)))


def cmd_oracle(args):
    prior = make_prior([args.k0], [args.lr], [args.demo], args.kmax)
    s = Solver(prior, objective=args.objective, min_defend=args.min_defend)
    a, q = s.best(args.n, 0, 0, prior["b0"])
    print(f"known params k0={args.k0} lr={args.lr} demo×{args.demo}, objective={args.objective}: optimal value {max(q.values()):.3f}")
    print("\n".join(plan_tree(s, args.n, 0, 0, prior["b0"])))


def cmd_analyze(args):
    log = json.load(open(args.log))
    for R in log["rounds"]:
        pr = R["params"]
        demo_on = pr.get("demoMult") not in (None, "off", 0)
        s, prior = build(args, demo_enabled=demo_on)
        n = pr["n"]; A, P, D, b = n, 0, 0, prior["b0"]
        theta = (pr["k0"], pr["lr"], pr["demoMult"] or 0)
        t = time.time()
        v0 = s.V(A, P, D, b)
        print(f"=== {log['pid']} · round {R['round']} · true k0={pr['k0']} lr={pr['lr']} demo×{pr['demoMult']} ===")
        print(f"(solved in {time.time()-t:.1f}s, {len(s.memo):,} belief states)")
        print(f"objective={args.objective}: Bayes-optimal policy is worth {v0:.3f} under the prior, "
              f"{s.policy_value_true(A, P, D, b, theta):.3f} under the TRUE params")
        print(f"Player's score: {R['final']['score']} of {R['final']['apples_tested']} defended\n")
        print(f"{'day':>3}  {'apples':>6}  {'player did':<12} {'optimal':<12} {'Q(player)':>9} {'Q(best)':>8} {'loss':>6}  E[skill]  true skill")
        total = 0.0
        for st in R["steps"]:
            a_star, q = s.best(A, P, D, b)
            act = st["action"]
            if act == "review" and ("review", st["m"]) not in q:
                q[("review", st["m"])] = s.review_value(A, P, D, b, st["m"])
            a_p = ("review", st["m"]) if act == "review" else act
            qp, qb = q[a_p], q[a_star]
            total += qb - qp
            Ek = float(b @ s.skill(P, D))
            print(f"{st['t']:>3}  {A:>6}  {fmt(a_p):<12} {fmt(a_star):<12} {qp:>9.2f} {qb:>8.2f} {qb-qp:>6.2f}  {Ek:>8.2f}  {st['k_before']:>10.2f}")
            if act == "practice": A -= 1; P += 1
            elif act == "demo": A -= 2; D += 1
            elif act == "review":
                b = s.update(P, D, st["m"], st["clean"], b); A -= st["m"]
                post_k = float(b @ s.skill(P, D))
                print(f"{'':>17}↳ saw {st['clean']}/{st['m']} clean → belief E[skill] now {post_k:.2f}")
        print(f"\nTotal value given up by suboptimal choices: {total:.3f}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def prior_opts(p):
        p.add_argument("--k0-grid", default="0,0.1,0.2,0.3,0.4,0.5", help="prior support for starting skill")
        p.add_argument("--lr-grid", default="0.025,0.05,0.1,0.15,0.2", help="prior support for learning rate")
        p.add_argument("--demo-grid", default="1.5,3", help="prior support for demo multiplier")
        p.add_argument("--kmax", type=float, default=1.0)
        p.add_argument("--objective", choices=["score", "perfect"], default="score")
        p.add_argument("--min-defend", type=int, default=1, help="perfect objective: minimum apples you must defend")

    p = sub.add_parser("solve", help="solve from the start of a game")
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--no-demo", action="store_true")
    p.add_argument("--depth", type=int, default=3, help="how many review levels to print")
    prior_opts(p); p.set_defaults(f=cmd_solve)

    p = sub.add_parser("analyze", help="score each step of a saved game against the optimal policy")
    p.add_argument("log"); prior_opts(p); p.set_defaults(f=cmd_analyze)

    p = sub.add_parser("oracle", help="known-parameter optimum (sanity check)")
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--k0", type=float, default=0.1); p.add_argument("--lr", type=float, default=0.1)
    p.add_argument("--demo", type=float, default=1.5); p.add_argument("--kmax", type=float, default=1.0)
    p.add_argument("--objective", choices=["score", "perfect"], default="score")
    p.add_argument("--min-defend", type=int, default=1)
    p.set_defaults(f=cmd_oracle)

    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
