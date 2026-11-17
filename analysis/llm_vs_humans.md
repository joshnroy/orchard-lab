# LLMs vs humans: first comparison

Two LLM players, adapted from [robocode](https://github.com/tomsilver/robocode), played the same two games as the human participants [Kartik 1](kartik_1.md) and [Abhay 1](abhay_1.md). Each used the same settings and seed as the human. A seed fixes how lucky each apple is, but each player's choices decide which apples are used where.

**Settings (all games):** 20 apples, starting skill k₀ = 0.1, learning rate 0.1, demos at 1.5×, 1 round. Seeds: 381892 (Kartik's) and 513651 (Abhay's).

## Players

| Player | What it is | Sees |
|---|---|---|
| **Human** | browser game (`index.html`) | rules scroll + Lab Notebook lines |
| **LLM only** (`agents/llm_player.py`) | Opus 5.5 through `claude -p` with all tools disabled and an empty system prompt, one call per game day in one continuous session. Robocode's `ClaudeCLIClient` setup; no extended thinking. | the same rules text and notebook lines, plus one line describing the answer format |
| **Coding agent** (`agents/agent_player.py`) | Opus 5.5 in Claude Code with Bash/Read/Write/Edit/Glob/Grep, as in robocode's agentic backend. It acts only through `python3 play.py <action>` and can write and run any code. Sandboxed with bubblewrap. | the same rules text, plus `play.py` usage |

## Results

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
2. **LLM only ≈ the better human; the coding agent is worse.** Ranked by expected score: Abhay (7.5) ≈ LLM only (7.5–7.7) > coding agent (5.25–6.5) > Kartik (4.75).
3. **The coding agent didn't use its tools to reason.** It never wrote or ran any code. It used Bash only for `play.py`, often chaining several moves in one command (for example demo, practice, practice). It paid 3.5× the LLM's cost for slightly worse play.
4. **The LLM-only player reasons like a marginal-value calculation.** In its replies it compared each practice's likely skill gain with the cost of one fewer apple at the defense, and stopped when the trade looked even. Its one misjudgement was the value of a 3-apple review.
5. **Actual scores are noisy.** At these skill levels a 10–15 apple defense has a standard deviation of about 1.5 clean cuts. The LLM scored 4 on Abhay's seed despite the best expected score in that game. Compare players by expected score and loss, not raw score.

## Caveats

- **One game per player per seed.** LLM play varies from run to run, so these are anecdotes until each player is run 10–20 times per seed.
- **One model, one setting.** Opus 5.5 with no extended thinking for the LLM and default effort for the agent. Thinking and effort may change review behaviour.
- **The optimal baseline depends on the prior.** The solver assumes a uniform prior over k₀ ∈ {0,…,0.5}, lr ∈ {0.025,…,0.2} and demo ∈ {1.5, 3}, and it knows the game's structure. Losses are measured against that.
- **Prompts are matched as closely as possible but not identical.** The LLM gets an answer-format line, and the agent gets `play.py` instructions and a short system prompt.

## Reproduce

```bash
python3 agents/llm_player.py   --seed 381892 --pid llm_kartikseed
python3 agents/agent_player.py --seed 381892 --pid agent_kartikseed
python3 solver/pomdp.py analyze data/<log>.json
```
