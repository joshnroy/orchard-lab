# 🍎 Orchard Lab

A cute, Stardew-style browser game for studying **sequential decision-making under an unknown skill and learning rate**. It's built so humans and LLMs can play the *exact same* task for a 1:1 comparison: when to practice, when to check how good you are, when to ask for a demonstration, and when to stop.

Part of a Computational Models of Cognition final project (Josh Roy & Samuel M. Bateman).

**Play it:** https://joshnroy.github.io/orchard-lab/. This static copy can't save to a server, so participants should download their data at the end. Run `server.py` for automatic saving.

## The task

You're an apprentice in the Orchard Lab with `n` apples. You have a hidden cutting skill `k` (the probability that a cut is clean) and a hidden learning rate `lr`. Each day you pick one action:

| Action | Apples used | Effect | What you observe |
|---|---|---|---|
| **Practice** | 1 | `k ← min(kmax, k + lr)` | nothing (you don't learn whether the cut was clean) |
| **Mock review (m)** | m | none | how many of the m cuts were clean ~ Binomial(m, k) |
| **Ask for a demo** | 2 | `k ← min(kmax, k + demoMult · lr)`, where `demoMult` ∈ {1.5, 3} | nothing |
| **Final test** (`DEFEND`) | all remaining | ends the round | clean cuts on all remaining apples, which is the **score** |

Expected score if you defend now = `apples_left × k`. Practicing makes you better but leaves fewer apples to score with. That's the trade-off.

**Common random numbers:** each apple `i` has a fixed random draw `u_i` from the seed, and a cut is clean iff `u_i < k` at that moment. A human and an LLM with the same seed face the same luck.

## Running it

No build step. You need Python 3.

```bash
python3 server.py            # serves on http://0.0.0.0:8080 (PORT=xxxx to change)
```

Open `http://<host>:8080`. Finished sessions are saved automatically to `data/<pid>_<timestamp>.json`. Participants can also download JSON/CSV/text transcripts from the end screen. You can also open `index.html` directly from disk; everything works except the automatic server save.

## Setting up a session

**Participants just open the plain URL** (e.g. `http://<host>:8080/` or the GitHub Pages link). The game starts right away with the study settings. Participants never see the settings, and adding URL parameters doesn't change them. Each game gets an anonymous random ID such as `p_3fa9c01b22de`, and the start and finish times are recorded. Nobody types a name.

The study settings live in one constant near the top of the UI script in `index.html`:

```js
const STUDY = { n:20, rounds:1, k:'0.1', lr:'0.1', demo:'1.5', kmax:1 };
```

The seed is random for each participant and saved in the data, so an LLM can later replay the same apple luck.

**Researcher setup** (for testing): open `?setup=1`. That screen lets you choose apples, rounds, k₀, learning rate (comma list = one per round), demo boost (1.5×, 3×, off), seed, skill cap and a debug panel. In setup mode these URL parameters prefill it:

```
http://host:8080/?setup=1&n=20&k=0.1,0.3&lr=0.1&demo=3&rounds=2&seed=42&debug=1
```

| Param | Default | Notes |
|---|---|---|
| `setup` | — | `1` opens the researcher setup screen; required for any other parameter to apply |
| `n` | 20 | apples per round |
| `k` | 0.1 | starting skill; comma list = per round |
| `lr` | 0.1 | learning rate; comma list = per round |
| `demo` | 1.5 | `1.5`, `3`, or `off` |
| `rounds` | 1 | skill resets each round |
| `seed` | random | round r uses `seed + 7919·r` |
| `kmax` | 1 | skill cap |
| `debug` | 0 | `1` shows hidden skill, the value of stopping now, and the oracle strategy |

Saved data has `mode: "participant"` or `"researcher"`, so test games are easy to filter out.

## Running an LLM on the same task

The game logic is a self-contained `AppleEnv` class (top `<script>` in `index.html`, also exposed as `window.AppleEnv`). It has no DOM dependencies, so it runs in Node or a browser console:

```js
const env = new AppleEnv({n: 20, k0: 0.1, lr: 0.1, demoMult: 3, seed: 42});
env.rulesText();                    // the exact rules text the human reads on the 📜 scroll
env.step({type: 'practice'});       // -> {obs, reward, done, text, record}
env.step({type: 'review', m: 3});
env.step({type: 'demo'});
env.step({type: 'defend'});         // reward = clean cuts
env.legal();                        // currently legal action types
env.oracle();                       // best fixed plan given the true params (analysis only)
```

Give the LLM `rulesText()` as its prompt, then each step's `text`, which is the same line the human sees in the Lab Notebook. Parse its reply into one of `PRACTICE`, `REVIEW m`, `DEMO`, `DEFEND`.

## Data format

Each saved JSON has `pid`, `config`, and `rounds[]`. Each round has:

- `params`: `n, k0, lr, kmax, demoMult, demoCost, seed`
- `steps[]`: `t, action, m, apples_before, apples_after, k_before, k_after, clean, outcomes` (1/0 per apple cut), `rt_ms` (time since the action became available), `ts`, `text`
- `final`: `score, apples_tested, k_final, expected_score, oracle_practice, oracle_demos, oracle_expected, days`
- `transcript`: rules text and notebook lines, the same text an LLM would see

The CSV export has one row per step.

## Tests

```bash
pip install playwright && playwright install chromium
python3 server.py &
python3 tests/e2e.py http://localhost:8080
```

Plays two full rounds in headless Chromium (practice → demo → review → defend, then a second round with different params), checks apple counts, hidden-skill updates, server save and CSV export, phone layout, and participant mode (no setup screen, URL can't change settings, anonymous ID).

## Bayes-optimal solver

`solver/pomdp.py` is an exact expectimax solver over beliefs. The player doesn't know `k0`, `lr`, or the demo multiplier, so the solver puts a discrete prior over all three. Only reviews produce observations, so the belief is the prior times binomial review likelihoods. Search over (apples, practices, demos, belief) is memoized. Reviews are pruned with an exact bound: no review can beat the full-information value with m fewer apples. With n = 20 it solves in well under a second for the score objective.

```bash
python3 solver/pomdp.py solve --n 20                         # optimal plan from the start
python3 solver/pomdp.py analyze data/<pid>_<time>.json       # Q-values and loss at every step a player took
python3 solver/pomdp.py oracle --k0 0.1 --lr 0.1 --demo 3    # known-parameter optimum (sanity check)
```

Options:
- `--objective score` (default): maximize expected clean cuts at the defense, which is the game's score.
- `--objective perfect [--min-defend M]`: maximize the probability that every apple at the defense is clean, defending at least M apples.
- `--k0-grid`, `--lr-grid`, `--demo-grid`: set the prior. The default is uniform over k0 ∈ {0,…,0.5}, lr ∈ {0.025,…,0.2}, demo× ∈ {1.5, 3}. Results depend on this prior.

## LLM players

`agents/` has two LLM players, adapted from [robocode](https://github.com/tomsilver/robocode). Both see the same text a human sees, and both save logs in the browser's format, so `solver/pomdp.py analyze` works on them. `agents/apple_env.py` is a Python version of the game that produces exactly the browser's random draws, so a seed gives an LLM the same apple luck a human had.

```bash
# LLM only: one `claude -p` call per game day, all tools disabled, empty system prompt
python3 agents/llm_player.py --seed 381892 --model claude-opus-5-5 [--effort high]   # thinking is always adaptive; --effort sets depth

# Coding agent: Claude Code with shell and file tools, acting through `python3 play.py <action>`
python3 agents/agent_player.py --seed 381892 --model claude-opus-5-5 [--effort high] [--budget 5]
```

Both take the game settings as options: `--n --k0 --lr --demo --rounds --seed`; comma lists give one value per round. Both need the `claude` CLI logged in (`claude auth login`). They clear the environment before calling it, so they also work when launched from inside Claude Code.

The coding agent runs in a bubblewrap sandbox. It sees an empty home with only its work directory, read-only system directories and Python. The hidden parameters live only in `agents/game_server.py`'s memory, which is outside the sandbox and in a separate PID namespace. Run transcripts go to `agents/runs/` (git-ignored).

First results: [analysis/llm_vs_humans.md](analysis/llm_vs_humans.md).
