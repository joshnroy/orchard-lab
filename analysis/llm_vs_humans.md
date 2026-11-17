# LLMs vs humans: first comparison

Two LLM players, adapted from [robocode](https://github.com/tomsilver/robocode), played the same two games as the human participants [Kartik 1](kartik_1.md) and [Abhay 1](abhay_1.md). Each used the same settings and seed as the human. A seed fixes how lucky each apple is, but each player's choices decide which apples are used where.

**Settings (all games):** 20 apples, starting skill k₀ = 0.1, learning rate 0.1, demos at 1.5×, 1 round. Seeds: 381892 (Kartik's) and 513651 (Abhay's).

## Players

| Player | What it is | Sees |
|---|---|---|
| **Human** | browser game (`index.html`) | rules scroll + Lab Notebook lines |
| **LLM only** (`agents/llm_player.py`) | Opus 5.5 through `claude -p` with all tools disabled and an empty system prompt, one call per game day in one continuous session. Robocode's `ClaudeCLIClient` setup. Thinking is adaptive at the CLI's default effort: Opus 5.5 can't turn thinking off, and the CLI ignores `--max-thinking-tokens 0`. | the same rules text and notebook lines, plus one line describing the answer format |
| **Coding agent** (`agents/agent_player.py`) | Opus 5.5 in Claude Code with Bash/Read/Write/Edit/Glob/Grep, as in robocode's agentic backend. It acts only through `python3 play.py <action>` and can write and run any code. Sandboxed with bubblewrap. | the same rules text, plus `play.py` usage |

## All players, with clean-cut percentage

"Clean %" is clean cuts ÷ apples defended, the defense's accuracy. "Final skill" is the hidden skill at the defense, which is the expected clean %. Values are means ± 95% CI.

| Player | Games | Score | Apples defended | Clean % | Final skill | Expected score | Loss vs optimal | Reviews | Cost / game |
|---|---|---|---|---|---|---|---|---|---|
| **Opus 5.5, LLM only** (CLI default effort) | 20 | 6.40 ± 0.77 | 11.65 ± 0.87 | 56.0 ± 7.3 | 0.67 ± 0.05 | **7.62 ± 0.46** | **1.86 ± 0.26** | 0.90 | $0.37 |
| **Fable 5.2, LLM only** (effort high) | 10 | 6.30 ± 0.72 | 13.20 ± 1.98 | 50.9 ± 10.5 | 0.54 ± 0.06 | **6.89 ± 0.58** | **1.90 ± 0.73** | 0.90 | ~$0.18* |
| **Opus 5.5, coding agent** | 20 | 4.75 ± 0.63 | 9.05 ± 1.18 | 55.4 ± 8.5 | 0.67 ± 0.06 | **5.75 ± 0.38** | **3.31 ± 0.38** | 1.95 | $0.92 |
| Kartik | 1 | 5 | 5 | **100** | 0.95 | 4.75 | 4.77 | 2 | |
| Abhay | 1 | 6 | 15 | 40 | 0.50 | 7.50 | 0.02 | 0 | |
| [Jaime](jaime_1.md) † | 1 | 3 | 4 | 75 | 0.75 | 3.00 | 5.53 | 3 | |
| *Bayes-optimal* | | | *15* | | *0.55* | *8.25* | *0* | *0* | |

\* The CLI (2.1.299) doesn't know Fable 5.2's price and reports almost zero, so this cost is estimated from token counts at $8 / $40 per MTok. Fable's games used little thinking: 16.8k thinking tokens across all 10.

† Jaime played a different seed (220085) that no LLM has played yet. Same settings otherwise.

**Clean % measures accuracy, not score.** Defending fewer apples after more training gives a higher clean % but usually a lower score. Kartik is the extreme case: 100% clean on only 5 apples, for a score of 5. Abhay got 40% on 15 apples, for a score of 6 and a much higher expected score. The optimal policy also aims for about 55% on 15 apples rather than high accuracy. Every model ends up between those two extremes (51–56%).

**Fable 5.2 at high effort is no better than Opus 5.5.** Its loss against the optimal policy (1.90 ± 0.73) matches Opus (1.86 ± 0.26), but it plays in two distinct ways:
- **4 of 10 games:** practice 3–4 times, never review, defend 16–17 apples. This is nearly the optimal policy.
- **6 of 10 games:** review once or twice (one game reviewed on day 1), then defend 9–14 apples. These lose about 2–4 points each, the same review mistake the other models make.

It stops training earlier than Opus (final skill 0.54 vs 0.67), so its expected score is lower with these hidden settings (6.89 vs 7.62). Under the solver's prior, though, stopping early costs almost nothing, which is why the loss is the same. Fable needs more games to separate the two clearly; 10 games gives wide intervals.

## Repeated runs: 10 games per player per seed

After the first single games below, each LLM player played **10 more games on each seed** (40 games, $25.82 total). Values are means ± 95% CI; the per-game data is in [games.csv](games.csv).

| Player | Games | Actual score | Expected score | Loss vs optimal | Reviews | Apples on reviews | Apples defended | Cost / game |
|---|---|---|---|---|---|---|---|---|
| **LLM only** | 20 | 6.40 ± 0.77 | **7.62 ± 0.46** | **1.86 ± 0.26** | 0.90 ± 0.24 | 2.45 ± 0.58 | 11.65 ± 0.87 | $0.37 |
| **Coding agent** | 20 | 4.75 ± 0.63 | **5.75 ± 0.38** | **3.31 ± 0.38** | 1.95 ± 0.30 | 4.80 ± 0.69 | 9.05 ± 1.18 | $0.92 |
| Kartik | 1 | 5 | 4.75 | 4.77 | 2 | 5 | 5 | |
| Abhay | 1 | 6 | 7.50 | 0.02 | 0 | 0 | 15 | |
| *Bayes-optimal* | | | *8.25* | *0* | *0* | *0* | *15* | |

By seed:

| Player | Seed | Actual score | Expected score | Loss |
|---|---|---|---|---|
| LLM only | Kartik's | 7.50 ± 0.53 | 7.33 ± 0.37 | 2.02 ± 0.36 |
| LLM only | Abhay's | 5.30 ± 1.10 | 7.91 ± 0.82 | 1.70 ± 0.37 |
| Coding agent | Kartik's | 6.00 ± 0.41 | 5.91 ± 0.44 | 3.40 ± 0.47 |
| Coding agent | Abhay's | 3.50 ± 0.44 | 5.60 ± 0.63 | 3.23 ± 0.63 |

**How they play:**
- **LLM only:** a stable script. In 20 games it never reviewed on day 1, practiced 2–4 times before any review, reviewed once (16 of 20 games, usually 3 apples), trained a few more times, and defended about 11–12 apples. 4 games had no review, and 8 used a demo. Most common sequence: practice ×3, review 3, practice ×3, defend.
- **Coding agent:** checks first. It **reviewed on day 1 in 17 of 20 games**, before any training, and reviewed about twice per game. It used a demo in 16 of 20 and defended fewer apples. It wrote its own code in only 1 of 20 games; otherwise it just ran `play.py`. Most common sequence: review 3, demo, practice ×2, review 3, practice ×2, defend.

**Seed effects:** both players score about 2 points lower on Abhay's seed even though their expected scores are similar. With these strategies, the apples that reach the defense on that seed are unlucky ones. This is why comparisons use expected score and loss.

## Results: first single games

"Loss" is expected points given up against the Bayes-optimal policy. That policy sees only what the player saw; see `solver/pomdp.py`.

| Player | Seed | Moves | Defended | Score | Expected score | Loss | Cost |
|---|---|---|---|---|---|---|---|
| Kartik | Kartik's | P, D, P, R2, D, P, R3, D, P, defend | 5 | 5 | 4.75 | 4.77 | |
| LLM only | Kartik's | P×3, R3, D, P×2, defend | 10 | 7 | 7.50 | 2.25 | $0.60 |
| Coding agent | Kartik's | R2, D, P×2, R2, P×2, defend | 10 | 7 | 6.50 | 2.60 | $2.01 |
| Abhay | Abhay's | D, P, D, defend | 15 | 6 | 7.50 | **0.02** | |
| LLM only | Abhay's | P×2, R3, P×4, defend | 11 | 4 | 7.70 | 2.24 | $0.58 |
| Coding agent | Abhay's | R2, P×3, R2, D, P×2, R2, defend | 7 | 3 | 5.25 | 3.86 | $2.08 |
| *Bayes-optimal* | either | P×3, D, defend | 15 | | *8.25* | 0 | |
| *Full information* | either | P×9, defend | 11 | | *11.0* | | |

P = practice, D = demo, Rm = mock review of m apples. "Expected score" is apples defended × final skill, which removes the luck of the defense itself.

## Findings

1. **Reviews are where everyone loses points.** Every review cost 1.1–2.2 expected points, and nobody's review changed the best next move. The LLM reviewed once per game (3 apples), the coding agent 2–3 times (2 apples each, starting on day 1 before any training), and Kartik twice. Abhay never reviewed and is the only near-optimal player.
2. **LLM only ≈ the better human; the coding agent is clearly worse.** Over 20 games each, the plain LLM's expected score is 7.62 ± 0.46 and the coding agent's 5.75 ± 0.38; the intervals don't overlap. Abhay's 7.5 matches the LLM, and Kartik's 4.75 is below both.
3. **Tools made the model worse, not better.** The coding agent wrote its own code in only 1 of 20 games. Its main difference from the plain LLM is a habit of measuring first: it reviewed on day 1, before any training, in 17 of 20 games. That review costs apples while skill is near its starting value, so it says nothing about whether training works. The agent cost about 2.5× more per game.
4. **The LLM-only player reasons like a marginal-value calculation.** In its replies it compared each practice's likely skill gain with the cost of one fewer apple at the defense, and stopped when the trade looked even. Its one misjudgement was the value of a 3-apple review.
5. **Actual scores are noisy.** At these skill levels a 10–15 apple defense has a standard deviation of about 1.5 clean cuts. The LLM scored 4 on Abhay's seed despite the best expected score in that game. Compare players by expected score and loss, not raw score.

## Caveats

- **Three humans, three seeds.** The LLM numbers rest on 10–20 games per player, but the human side is 3 people, each playing once. [Jaime](jaime_1.md) (loss 5.53, three reviews) is on a seed the LLMs haven't played yet.
- **Effort.** The Opus 5.5 runs used adaptive thinking at the CLI's default effort for both players. An earlier version of this page said "no extended thinking", which was wrong: the CLI ignored `--max-thinking-tokens 0`, and a test prompt still produced thinking tokens.
- **The optimal baseline depends on the prior.** The solver assumes a uniform prior over k₀ ∈ {0,…,0.5}, lr ∈ {0.025,…,0.2} and demo ∈ {1.5, 3}, and it knows the game's structure. Losses are measured against that.
- **Wording changed after these runs.** All games on this page used the earlier "PhD student / thesis defense" rules text. The game and the LLM players now say "apprentice / final test" instead; the actions and rules are otherwise unchanged.
- **Prompts are matched as closely as possible but not identical.** The LLM gets an answer-format line, and the agent gets `play.py` instructions and a short system prompt.

## Reproduce

```bash
python3 agents/llm_player.py   --seed 381892 --pid llm_kartikseed
python3 agents/agent_player.py --seed 381892 --pid agent_kartikseed
python3 solver/pomdp.py analyze data/<log>.json

python3 agents/batch.py --player llm   --reps 10        # 10 games per seed
python3 agents/batch.py --player agent --reps 10
python3 analysis/aggregate.py data/*.json --csv analysis/games.csv
```
