# Participant "Jaime 1": replay and optimal-policy comparison

**Settings:** same as [Kartik 1](kartik_1.md) and [Abhay 1](abhay_1.md). 20 apples, starting skill k₀ = 0.1, learning rate 0.1, demos at 1.5×, skill cap 1.0, 1 round, seed 220085.
**Played:** 2026-11-17, about 6 minutes from first view to the defense.
**Result:** defended 4 apples, 3 clean cuts → **score 3** (expected 3.0 at their final skill).

## Replay

| Day | Action | Apples left | Hidden skill | Value if defended | What they saw | Response time |
|---|---|---|---|---|---|---|
| 0 | start | 20 | 0.10 | 2.0 | | |
| 1 | review 3 | 17 | 0.10 | 1.7 | **0 of 3 clean** | **196 s** |
| 2 | demo | 15 | 0.25 | 3.75 | | 2.8 s |
| 3 | review 3 | 12 | 0.25 | 3.0 | **0 of 3 clean** | 6.9 s |
| 4 | practice | 11 | 0.35 | 3.85 | | 1.3 s |
| 5 | practice | 10 | 0.45 | 4.5 | | 4.7 s |
| 6 | review 3 | 7 | 0.45 | 3.15 | **1 of 3 clean** | **50 s** |
| 7 | practice | 6 | 0.55 | 3.3 | | 14.8 s |
| 8 | practice | 5 | 0.65 | 3.25 | | 1.1 s |
| 9 | practice | 4 | 0.75 | 3.0 | | 2.6 s |
| 10 | defend | 0 | 0.75 | | 3 of 4 clean | 2.2 s |

"Value if defended" is apples left × hidden skill, the expected score of stopping on that day. Its peak was 4.5 on day 5, and by the defense it was 3.0. The 3 reviews used 9 of the 20 apples.

The review results were about what the true skill predicts. 0 of 3 at skill 0.10 had a 73% chance, 0 of 3 at 0.25 had 42%, and 1 of 3 at 0.45 had 41%. Defense: `0111`, 3 of 4 clean, exactly the expected 3.0.

## Optimal solvers

These use the same solver and prior as the other analyses: observed information only, and a uniform prior over k₀ ∈ {0,…,0.5}, lr ∈ {0.025,…,0.2}, demo boost ∈ {1.5×, 3×}.

| Player | Expected score |
|---|---|
| Full information | **11.0** (practice 9×, defend 11) |
| Bayes-optimal, observed information only | **8.25** (practice 3×, demo 1×, defend 15); actual on Jaime's seed: **5 of 15** |
| Abhay | 7.5; actual: 6 |
| Kartik | 4.75; actual: 5 |
| **Jaime** | **3.0**; actual: 3 |

Played on Jaime's seed, the optimal policy never reviews, so its moves don't depend on luck: practice ×3, demo, defend 15. It scores **5 of 15**, an unlucky draw against its expected 8.25 (it gets 9 of 15 on Kartik's seed and 6 of 15 on Abhay's). Full information (practice ×9 to skill 1.0) gets 11 of 11 on every seed.

### Goal 1: maximize expected score

| Day | Apples | Jaime did | Optimal | Value of their move | Value of best move | Loss | Believed skill (avg) | True skill |
|---|---|---|---|---|---|---|---|---|
| 1 | 20 | review 3 | practice | 8.70 | 10.76 | **2.06** | 0.25 | 0.10 |
| 2 | 17 | demo | practice | 7.74 | 7.74 | 0.00 | 0.15 | 0.10 |
| 3 | 15 | review 3 | practice | 5.92 | 7.74 | **1.81** | 0.38 | 0.25 |
| 4 | 12 | practice | practice | 3.94 | 3.94 | 0.00 | 0.22 | 0.25 |
| 5 | 11 | practice | practice | 3.94 | 3.94 | 0.00 | 0.29 | 0.35 |
| 6 | 10 | review 3 | practice | 2.60 | 3.94 | **1.34** | 0.36 | 0.45 |
| 7 | 7 | practice | practice | 2.37 | 2.37 | 0.00 | 0.33 | 0.45 |
| 8 | 6 | practice | defend | 2.28 | 2.37 | 0.09 | 0.40 | 0.55 |
| 9 | 5 | practice | defend | 2.04 | 2.28 | 0.23 | 0.46 | 0.65 |
| 10 | 4 | defend | defend | 2.04 | 2.04 | 0.00 | 0.51 | 0.75 |

**Total loss: 5.53 expected points, the largest of any player so far.** The three reviews account for 5.21 of it.

- **Day 1 review (−2.06):** made before any training, when skill is at its starting value. It can say how good Jaime is now, but nothing about how fast they learn, and that is what decides how long to train. The coding agent made the same opening move in 17 of 20 games.
- **Day 3 review (−1.81):** made right after the demo. The second 0/3 made the solver's belief quite pessimistic (average believed skill 0.22), but no result of that review would have changed the best next move: practice.
- **Day 6 review (−1.34):** 1 of 3 clean, with only 10 apples left. It used 30% of the remaining apples.
- **Days 8–9 (−0.32):** after the pessimistic reviews, the solver would have defended 6 apples. Jaime kept practising. With their actual settings this was the right call: true skill rose 0.10 per practice. Judged only on what Jaime had seen, though, it was slightly too much training.

### Goal 2: perfect defense (at least 4 apples)

Jaime trained hard and defended few apples, as Kartik did, so this goal may be closer to what they were aiming for. With "all of at least 4 defended apples clean" as the goal, the optimal policy has a 0.83 chance under the prior (1.00 with the true settings). Jaime lost **0.27** of that, all from the three reviews (0.05, 0.09, 0.13), and every practice and the defense were optimal. Their actual chance of 4 of 4 at skill 0.75 was 32%.

## Takeaways

1. **Jaime is the clearest "measure, then train" player so far.** They reviewed 3 times, used 9 apples on reviews, and reviewed first. Abhay never reviewed and was near-optimal. Kartik reviewed twice and lost 4.77. Jaime reviewed three times and lost 5.53. Across the three humans, more apples spent on reviews means a lower expected score.
2. **They learned well but ran out of apples.** Final skill was 0.75, the highest of the three humans after Kartik's 0.95, and 75% of their final cuts were clean. The best they could have done by stopping was 4.5 (on day 5), still below the optimal 8.25 because of the 6 apples already spent on reviews.
3. **Early bad luck pushed them toward caution.** Two 0-of-3 reviews in a row are discouraging. A reasonable reaction is to keep checking. Every review result here was typical for the true skill, but a player can't tell that from inside the game.
4. **Long pause at the start, then fast.** 196 s on the first move (reading the rules) and 50 s before the third review. Everything else took a few seconds.
5. **On this seed the LLMs all beat Jaime** (see below), and Fable 5.2 came close to the optimal policy.

## LLMs on Jaime's seed

Each player ran 10 games on seed 220085 with the same settings. Values are means ± 95% CI. These 30 games ran while the game briefly used "apprentice / final test" wording instead of "PhD student / thesis defense". The rules, actions and numbers were the same.

| Player | Games | Score | Defended | Clean % | Expected score | Loss vs optimal | Reviews | Reviewed on day 1 |
|---|---|---|---|---|---|---|---|---|
| **Fable 5.2, LLM only** (effort high) | 10 | 5.20 ± 0.39 | 15.0 ± 1.8 | 38 | **7.89 ± 0.47** | **0.65 ± 0.54** | 0.2 | 0 of 10 |
| **Opus 5.5, LLM only** | 10 | 6.00 ± 0.72 | 9.7 ± 2.0 | 68 | **7.07 ± 1.07** | **2.18 ± 0.85** | 1.4 | 2 of 10 |
| **Opus 5.5, coding agent** | 10 | 5.40 ± 0.52 | 8.1 ± 2.6 | 79 | **5.54 ± 0.76** | **3.31 ± 0.93** | 1.9 | 7 of 10 |
| Jaime | 1 | 3 | 4 | 75 | 3.00 | 5.53 | 3 | yes |
| *Bayes-optimal* | | 5 | 15 | 33 | *8.25* | *0* | *0* | |

- **Fable 5.2** practised 4 times and defended 16 apples in 8 of 10 games, which is nearly the optimal policy. It reviewed in only 1 game. On the earlier seeds it reviewed in 6 of 10 games, so this run makes its no-review style look like its main one.
- **Opus LLM-only** mostly practised 3–5 times, then reviewed once or twice and trained more. It reviewed on day 1 in 2 games, which it never did in its 20 games on the other seeds.
- **The coding agent** reviewed on day 1 in 7 of 10 games, as on the other seeds, and defended the fewest apples. It also cost the most: $15.95 for 10 games, against $5.20 for Opus LLM-only and about $1.32 for Fable.
- **Raw scores are bunched (5–6)** because this seed is unlucky for large defenses. The optimal policy itself scores only 5 here, and every Fable game that defended 15–16 apples scored 5. The coding agent's 5.4 comes from small, accurate defenses, but its expected score is much lower. Compare by expected score and loss.

Jaime's play is closest to the coding agent's: review first, review often, defend few apples. Jaime went further in the same direction, with three reviews and 4 apples defended.

```bash
python3 agents/batch.py --player llm   --seeds 220085 --reps 10
python3 agents/batch.py --player llm   --seeds 220085 --reps 10 --tag fable --model claude-fable-5-2 --effort high
python3 agents/batch.py --player agent --seeds 220085 --reps 10
```

## Reproduce

```bash
python3 solver/pomdp.py analyze data/orchard_Jaime_1.json                                       # Goal 1
python3 solver/pomdp.py analyze data/orchard_Jaime_1.json --objective perfect --min-defend 4    # Goal 2
```
