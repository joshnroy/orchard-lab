# Participant "Kartik 1": replay and optimal-policy comparison

**Settings:** 20 apples, starting skill k₀ = 0.1, learning rate 0.1, demos at 1.5× (each demo adds 0.15 skill for 2 apples), skill cap 1.0, 1 round, seed 381892.
**Played:** 2026-11-17, about 50 seconds from first action to defense.
**Result:** defended 5 apples, 5 clean cuts → **score 5**.

## Replay

"Value if defended" is apples left × hidden skill: the expected score if he had defended right then. The hidden skill was never shown to him.

| Day | Action | Apples left | Hidden skill | Value if defended | What he saw | Response time |
|---|---|---|---|---|---|---|
| 0 | start | 20 | 0.10 | 2.0 | | |
| 1 | practice | 19 | 0.20 | 3.8 | nothing | 6.7 s |
| 2 | demo | 17 | 0.35 | 6.0 | nothing | 6.3 s |
| 3 | practice | 16 | 0.45 | 7.2 | nothing | 3.0 s |
| 4 | review 2 | 14 | 0.45 | 6.3 | 1 of 2 clean | 8.1 s |
| 5 | demo | 12 | 0.60 | 7.2 | nothing | 1.6 s |
| 6 | practice | 11 | 0.70 | **7.7 (peak)** | nothing | 1.8 s |
| 7 | review 3 | 8 | 0.70 | 5.6 | 2 of 3 clean | 7.8 s |
| 8 | demo | 6 | 0.85 | 5.1 | nothing | 3.7 s |
| 9 | practice | 5 | 0.95 | 4.75 | nothing | 0.5 s |
| 10 | defend | 0 | 0.95 | | **5 of 5 clean** | 1.7 s |

He spent 15 of 20 apples on training (4 on practice, 6 on demos, 5 on reviews) and defended with 5.

## Optimal solvers

`solver/pomdp.py` finds the best policy using **only what the player can observe**: action counts, apples left, and review outcomes. It doesn't know the hidden values, so it holds a uniform prior over 60 possibilities:

- starting skill k₀ ∈ {0, 0.1, …, 0.5}
- learning rate ∈ {0.025, 0.05, 0.1, 0.15, 0.2}
- demo boost ∈ {1.5×, 3×}

Its belief is updated only by review results. The hidden settings are used only to score how a policy would have done in this game.

| Player | Expected score |
|---|---|
| Full information (knows k₀, lr and demo boost) | **11.0** (practice 9×, defend 11) |
| Bayes-optimal, observed information only | **8.25** |
| Kartik (expected, given the skill he ended with) | **4.75** (actual: 5) |

### Goal 1: maximize expected score (the game's actual scoring)

From the start, the optimal plan is **practice 3×, demo 1×, defend 15 apples, with no reviews**. It's worth 10.76 under the prior and 8.25 with Kartik's real settings.

Each of Kartik's steps scored against the optimal policy, given what he knew at that moment:

| Day | Apples | Kartik did | Optimal | Value of his move | Value of best move | Loss | Believed skill (avg) | True skill |
|---|---|---|---|---|---|---|---|---|
| 1 | 20 | practice | practice | 10.76 | 10.76 | 0.00 | 0.25 | 0.10 |
| 2 | 19 | demo | practice | 10.76 | 10.76 | 0.00 | 0.35 | 0.20 |
| 3 | 17 | practice | practice | 10.76 | 10.76 | 0.00 | 0.58 | 0.35 |
| 4 | 16 | review 2 | practice | 9.50 | 10.76 | **1.26** | 0.66 | 0.45 |
| 5 | 14 | demo | demo | 8.08 | 8.08 | 0.00 | 0.54 | 0.45 |
| 6 | 12 | practice | defend | 7.94 | 8.08 | 0.14 | 0.67 | 0.60 |
| 7 | 11 | review 3 | defend | 5.78 | 7.94 | **2.17** | 0.72 | 0.70 |
| 8 | 8 | demo | defend | 4.35 | 5.03 | 0.68 | 0.63 | 0.70 |
| 9 | 6 | practice | defend | 3.82 | 4.35 | 0.53 | 0.72 | 0.85 |
| 10 | 5 | defend | defend | 3.82 | 3.82 | 0.00 | 0.76 | 0.95 |

**Total loss: 4.77 expected points.** The two reviews cost 3.43 of that. They used 5 apples, and their results didn't change what the best move was. From day 6 on, the optimal policy would have defended.

The day-4 review moved his belief down (1/2 clean → believed skill fell from 0.66 to 0.54). The day-7 review did the same (2/3 → 0.72 to 0.63). Both results were consistent with his true skill, but 2–3 apples is too few to learn much.

### Goal 2: maximize the chance of a perfect defense

Here the goal is the probability that every apple at the defense is clean. With no minimum, the trivial answer is to train until 1 apple is left and defend just that one. So this run requires **defending at least 5 apples**, which is how many Kartik kept. Because 5 was chosen to match his play, this comparison is partly circular.

The optimal plan is **practice 5×, demo 5×, defend exactly 5 apples**: a 0.80 chance of a perfect defense under the prior (1.00 with his true settings).

| Day | Apples | Kartik did | Optimal | Value of his move | Value of best move | Loss |
|---|---|---|---|---|---|---|
| 1 | 20 | practice | practice | 0.80 | 0.80 | 0.00 |
| 2 | 19 | demo | practice | 0.80 | 0.80 | 0.00 |
| 3 | 17 | practice | practice | 0.80 | 0.80 | 0.00 |
| 4 | 16 | review 2 | practice | 0.77 | 0.80 | 0.04 |
| 5 | 14 | demo | practice | 0.70 | 0.70 | 0.00 |
| 6 | 12 | practice | practice | 0.70 | 0.70 | 0.00 |
| 7 | 11 | review 3 | demo | 0.58 | 0.70 | **0.12** |
| 8 | 8 | demo | practice | 0.40 | 0.41 | 0.01 |
| 9 | 6 | practice | practice | 0.40 | 0.40 | 0.00 |
| 10 | 5 | defend | defend | 0.40 | 0.40 | 0.00 |

**Total loss: 0.16 of probability, out of 0.80 achievable.** Under this goal his play was close to optimal:

- He stopped at exactly 5 apples, which was the optimal stopping point.
- He mixed practice and demos. The optimal policy also uses demos, because it doesn't know whether they're worth 1.5× or 3×.
- His one real mistake was the 3-apple review on day 7.

His actual 5/5 had about a 77% chance at his final skill of 0.95.

## Takeaways

1. **He played like someone aiming to be reliably good, not to maximize clean cuts.** Under the game's real scoring he lost 4.8 of about 10 achievable expected points. Under a "perfect with ≥ 5 apples" goal he lost only 0.16 of 0.80.
2. **The reviews were the costly choice under both goals.** They were small samples that used apples without changing the best decision.
3. **Demos weren't a mistake from his point of view.** They only look bad in hindsight because the boost turned out to be 1.5×. The solver counts his demos as zero loss under both goals.
4. **He sped up and settled into a routine.** Decisions went from about 6–8 s early to under 2 s by the end (455 ms on day 9), apart from the review dialogs.

## Caveats

- This is one participant, one round. The proposal predicts learning across repeated games, which needs `rounds ≥ 3`.
- The solver's prior (the parameter ranges, linear learning with a cap, a demo boost of exactly 1.5× or 3×) gives it more structural knowledge than the player gets. The human is told only that practice and demos help "by an unknown amount". The true settings are also exact points in the prior, which helps the solver.
- The minimum of 5 apples in Goal 2 was chosen after seeing his play.

## Reproduce

```bash
python3 solver/pomdp.py analyze data/orchard_Kartik_1.json                                   # Goal 1
python3 solver/pomdp.py analyze data/orchard_Kartik_1.json --objective perfect --min-defend 5  # Goal 2
python3 solver/pomdp.py solve --n 20                                                          # optimal plan from the start
```

The raw log isn't in the repo: `data/` is git-ignored, since logs contain participant IDs.
