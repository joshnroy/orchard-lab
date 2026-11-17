# Participant "Abhay 1": replay and optimal-policy comparison

**Settings:** same as [Kartik 1](kartik_1.md). 20 apples, starting skill k₀ = 0.1, learning rate 0.1, demos at 1.5×, skill cap 1.0, 1 round, seed 513651.
**Played:** 2026-11-17, about 4.7 minutes from first view to defense.
**Result:** defended 15 apples, 6 clean cuts → **score 6** (expected 7.5 at his final skill).

## Replay

| Day | Action | Apples left | Hidden skill | Value if defended | Response time |
|---|---|---|---|---|---|
| 0 | start | 20 | 0.10 | 2.0 | |
| 1 | demo | 18 | 0.25 | 4.5 | **122 s** |
| 2 | practice | 17 | 0.35 | 6.0 | 4.6 s |
| 3 | demo | 15 | 0.50 | 7.5 | **51 s** |
| 4 | defend | 0 | 0.50 | | 8.3 s |

Defense outcomes: `100110010010100`, 6 of 15 clean. At skill 0.5 the expected count was 7.5. Scoring 6 or fewer had about a 30% chance, so he was somewhat unlucky.

## Optimal solvers

These use the same solver and prior as the Kartik analysis: observed information only, and a uniform prior over k₀ ∈ {0,…,0.5}, lr ∈ {0.025,…,0.2}, demo boost ∈ {1.5×, 3×}.

| Player | Expected score |
|---|---|
| Full information | **11.0** (practice 9×, defend 11) |
| Bayes-optimal, observed information only | **8.25** (practice 3×, demo 1×, defend 15) |
| Abhay | **7.5** (demo, practice, demo, defend 15); actual: 6 |
| Kartik, for comparison | 4.75; actual: 5 |

### Goal 1: maximize expected score

| Day | Apples | Abhay did | Optimal | Value of his move | Value of best move | Loss | Believed skill (avg) | True skill |
|---|---|---|---|---|---|---|---|---|
| 1 | 20 | demo | practice | 10.76 | 10.76 | 0.00 | 0.25 | 0.10 |
| 2 | 18 | practice | practice | 10.76 | 10.76 | 0.00 | 0.48 | 0.25 |
| 3 | 17 | demo | practice | 10.74 | 10.76 | 0.02 | 0.58 | 0.35 |
| 4 | 15 | defend | defend | 10.74 | 10.74 | 0.00 | 0.72 | 0.50 |

**Total loss: 0.02 expected points. Given what he could know, Abhay played essentially optimally.** He trained with 5 apples, never reviewed, and defended the same 15 apples the optimal policy does. The optimal plan from the start (practice ×3, demo, defend 15) uses the same 5 training apples. The only difference is the mix: 2 demos + 1 practice instead of 1 demo + 3 practices.

That mix is why he lands at 7.5 rather than 8.25 with the real settings: with a 1.5× boost, a demo is worth less per apple than a practice. He couldn't have known that ahead of time. Under the prior, the two plans are worth almost the same (a gap of 0.02).

### Goal 2: perfect defense

Not informative here. Abhay defended 15 apples, and the chance of 15/15 at any skill below about 0.95 is close to zero. Requiring at least 15 apples makes every plan nearly equal, and the solver finds zero loss at every step.

## Takeaways

1. **Abhay matches the Bayes-optimal policy and Kartik doesn't.** Same settings and same instructions, but very different strategies: Abhay trained briefly and defended big, while Kartik trained heavily, reviewed, and defended small.
2. **Being optimal didn't guarantee a better outcome.** Abhay was 0.75 below the optimal policy in expectation (from the demo mix) and about 1.5 below his own expectation on the day (bad luck in the cuts). He still beat Kartik, but only by one point (6 vs 5), even though his expected score was 2.75 higher.
3. **He deliberated up front and then committed.** He took 2 minutes on the first decision and 51 s on the second demo, then defended quickly. Kartik made quick, routine-like decisions. This fits a "plan, then execute" style as opposed to "act and monitor".
4. **The optimal policy depends on the prior.** At the defense the solver's average believed skill is 0.72, but the true skill is 0.50: the prior (average k₀ 0.25) is more optimistic than the real settings. A more pessimistic prior would recommend more training and make Abhay look like he stopped too early. A sensitivity check over several priors is worth doing before drawing conclusions.

## Reproduce

```bash
python3 solver/pomdp.py analyze data/orchard_Abhay_1.json
```
