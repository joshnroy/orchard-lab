# 🍎 Orchard Lab — PhD Simulator

A cute, Stardew-style browser game for studying **sequential decision-making under an unknown skill and learning rate**. It's built so humans and LLMs can play the *exact same* task for a 1:1 comparison: when to practice, when to check how good you are, when to ask for a demonstration, and when to stop.

Part of a Computational Models of Cognition final project (Josh Roy & Samuel M. Bateman).

## The task

You're a PhD student with `n` apples. You have a hidden cutting skill `k` (the probability that a cut is clean) and a hidden learning rate `lr`. Each day you pick one action:

| Action | Apples used | Effect | What you observe |
|---|---|---|---|
| **Practice** | 1 | `k ← min(kmax, k + lr)` | nothing (you don't learn whether the cut was clean) |
| **Mock review (m)** | m | none | how many of the m cuts were clean ~ Binomial(m, k) |
| **Ask for a demo** | 2 | `k ← min(kmax, k + demoMult · lr)`, where `demoMult` ∈ {1.5, 3} | nothing |
| **Defend thesis** | all remaining | ends the round | clean cuts on all remaining apples, which is the **score** |

Expected score if you defend now = `apples_left × k`. Practicing makes you better but leaves fewer apples to score with. That's the trade-off.

**Common random numbers:** each apple `i` has a fixed random draw `u_i` from the seed, and a cut is clean iff `u_i < k` at that moment. A human and an LLM with the same seed face the same luck.

## Running it

No build step. You need Python 3.

```bash
python3 server.py            # serves on http://0.0.0.0:8080 (PORT=xxxx to change)
```

Open `http://<host>:8080`. Finished sessions are saved automatically to `data/<pid>_<timestamp>.json`. Participants can also download JSON/CSV/text transcripts from the end screen. You can also open `index.html` directly from disk; everything works except the automatic server save.

## Setting up a session

The **setup screen** lets the researcher choose:

- **Participant ID**
- **Apples (n)**
- **Rounds**: repeated games ("PhD years"); skill resets each round
- **Starting skill k₀** and **learning rate**: hidden from the player. A comma list such as `0.1, 0.3` uses a different value each round.
- **Demonstration boost**: 1.5× lr, 3× lr, or off
- **Random seed**
- *Researcher options:* skill cap `kmax`, and a debug panel that shows hidden `k`, the expected value of defending now, and the oracle strategy

**Don't let participants see the setup screen**, because it shows the hidden parameters. Fill it in and click **🔗 Copy participant link**. That gives you a URL with `go=1`, which skips setup and asks the participant only for their ID. Every setting can also go in the URL:

```
http://host:8080/?n=20&k=0.1&lr=0.1&demo=3&rounds=3&seed=42&go=1
```

| Param | Default | Notes |
|---|---|---|
| `n` | 20 | apples per round |
| `k` | 0.1 | starting skill; comma list = per round |
| `lr` | 0.1 | learning rate; comma list = per round |
| `demo` | 1.5 | `1.5`, `3`, or `off` |
| `rounds` | 1 | |
| `seed` | random | round r uses `seed + 7919·r` |
| `kmax` | 1 | skill cap |
| `pid` | — | participant ID (if missing with `go=1`, the game asks) |
| `go` | — | `1` skips the setup screen |
| `debug` | 0 | `1` shows hidden skill |

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

Plays two full rounds in headless Chromium (practice → demo → review → defend, then a second round with different params), checks apple counts, hidden-skill updates, server save and CSV export, phone layout, and participant-link mode.
