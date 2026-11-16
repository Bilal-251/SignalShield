# SignalShield: Do Reliability Labels Survive an Adversary?

An experiment on whether source-reliability labels can protect an AI research agent from planted false evidence, and what happens when an attacker can forge those labels.

Built for the Apart Research **AI x Epistemics Research Sprint** (November 2026).

## The idea in one minute

AI agents that answer questions by reading documents can be steered by a few planted false documents. A common defense is to attach a reliability label to each source ("High", "Medium", "Low"). That defense assumes the label can be trusted. If the label sits in the same text the attacker controls, the attacker can simply write "High" on their own false document.

SignalShield tests this directly, with a controlled setup where only the labels change between conditions:

- **In-band labels:** the label is written inside the document text (an attacker can forge it).
- **Out-of-band labels:** the label comes from a separate `get_reliability(doc_id)` tool that the attacker cannot write to.

## Main results

80 synthetic questions, 2 repeats each, 960 runs, model: Cohere Command A (`command-a-03-2025`). Lower false-answer adoption is better. Intervals are 95% bootstrap intervals over items.

| Arm | Condition | False-answer adoption | 95% CI | Accuracy |
| --- | --- | --- | --- | --- |
| A0 | No labels | 0.394 | [0.306, 0.487] | 0.588 |
| A1 | Honest labels, in-band | 0.219 | [0.138, 0.306] | 0.775 |
| A3 | Honest labels, out-of-band tool | 0.094 | [0.037, 0.156] | 0.906 |
| A4 | **Forged** labels, in-band | **0.600** | [0.506, 0.688] | 0.400 |
| A6 | Forged text in documents, honest out-of-band tool | 0.231 | [0.156, 0.312] | 0.750 |
| A7 | Honest labels, tiers reversed (truth on Low sources) | 0.812 | [0.738, 0.881] | 0.181 |

**Takeaways**

1. Honest labels help (39.4% to 21.9% in-band, 9.4% out-of-band).
2. Forged in-band labels backfire: adoption of the false answer rose to 60.0%, **worse than no labels at all**.
3. An out-of-band channel kept about 54% of its benefit under the same forgery (interval 0.31 to 0.77). In-band labels kept none.
4. Labels that point the wrong way are costly: accuracy fell from 58.8% to 18.1%.

Hypotheses were written down before the main run, see [`prereg.md`](prereg.md). All four were supported, but see the limitations below before reading much into the effect sizes.

## Experimental design

Each question is about a **fictional** entity (so real-world knowledge cannot help), with four answer options and six documents: 2 supporting the true answer, 2 supporting a planted false answer, 2 neutral. Source domains and reliability tiers are assigned by code, not by the model. Answers are parsed with a regex, so there is no LLM judge.

| Arm | Labels | Where they live | Notes |
| --- | --- | --- | --- |
| A0 | none | n/a | baseline |
| A1 | honest tier | inside the document text | |
| A2 | honest track record | inside the document text | not run in the sprint |
| A3 | honest tier | separate lookup tool | attacker cannot write |
| A4 | forged tier | inside the document text | false documents claim "High" |
| A5 | forged track record | inside the document text | not run in the sprint |
| A6 | forged text and honest tool | both | does the tool rescue the agent? |
| A7 | honest tier, reversed | inside the document text | truth sits on Low sources |

The agent is a ReAct-style loop with a BM25 `search` tool (top 4 snippets), a `read` tool, and in out-of-band arms a `get_reliability` tool. Up to 4 tool steps, then a forced final answer in the form `ANSWER: <letter>`.

Primary metric: false-answer adoption rate (mean over repeats within an item). Uncertainty: bootstrap that resamples **items**. "Benefit retained under forgery" is `(A0 - A4) / (A0 - A1)` for in-band and `(A0 - A6) / (A0 - A3)` for out-of-band.

## Repository layout

| File | Purpose |
| --- | --- |
| `run_all.py` | One-click runner: generate items, run all arms, analyze. Works from the VS Code Run button. |
| `config.py` | Model name, prices, budget cap, arms, domains. Reads `.env`. |
| `llm.py` | Cohere wrapper: disk cache, spend tracking, hard budget stop, rate-limit handling, mock mode. |
| `gen_items.py` | Generates and validates the fictional-entity questions. |
| `inject.py` | Builds each arm: label text, forgery, reversal, out-of-band labels. |
| `agent.py` | The tool-using agent and answer parsing. |
| `run.py` | Resumable, budget-guarded experiment runner. |
| `analyze.py` | Tables, bootstrap intervals, figures, writes `results.md`. |
| `prereg.md` | Pre-registered hypotheses. |
| `debug_one.py`, `debug_tools.py` | Small diagnostics for checking API access and one agent run. |

## Quick start

Requires Python 3.10+ and a [Cohere](https://cohere.com) API key.

```bash
git clone <this-repo>
cd signalshield
pip install -r requirements.txt
```

Put your key in a file named `.env` next to `config.py` (this file is git-ignored; never commit it):

```
COHERE_API_KEY=your_key_here
```

Or set it in the shell: `export COHERE_API_KEY=your_key_here` (Windows: `set COHERE_API_KEY=your_key_here`).

**Easiest:** open `run_all.py` and run it (in VS Code, press the Run button). It makes the items, runs all six arms, and writes `results.md`, `fig1_adoption.png` and `fig2_retained.png`. If it stops, run it again: finished work is cached and skipped.

**Step by step:**

```bash
python gen_items.py --n 80 --out items.json
python run.py --n-items 80 --arms A0,A1,A3,A4,A6,A7 --reps 2
python analyze.py
```

Optional arms: add `A2,A5` to `--arms` for the track-record variants.

**Try it offline (no key, no cost):** `MOCK=1 python run_all.py` (Windows: `set MOCK=1` first) runs the whole pipeline against a simulated model. Use this only to check that the code runs; its numbers mean nothing.

## Cost and safety rails

- The run in the paper cost roughly **$18** in API spend, including item generation.
- `SS_BUDGET` (default `400`) is a hard cap in USD: the wrapper refuses new calls once recorded spend reaches it. Set it lower while experimenting, for example `SS_BUDGET=5`.
- Prices in `config.py` are list prices; check your Cohere dashboard.
- Every API response is cached on disk (`cache/`), so re-running costs nothing for finished calls.

## Using a different model

Set `SS_MODEL` (default `command-a-03-2025`). Command A+ (`command-a-plus-05-2026`) always thinks, so set `THINK_BUDGET` in `config.py` to a number such as `800`; turning thinking off made that model write its reasoning into the answer text and broke the JSON item generator. Update the prices in `config.py` to match the model.

## Limitations

Read these before relying on the numbers.

- **One model, one run.** Results are from Command A only. The original plan was Command A+, but rate limits made that impractical in the sprint window.
- **Synthetic items.** Fictional entities remove prior knowledge but are simpler than real misinformation, and the documents are LLM-written.
- **Perfectly informative labels.** In honest arms the labels match the truth by construction, so A1 and A3 are an **upper bound** on the benefit.
- **A simple attacker.** One fixed forgery template. No adaptive attacker, no partial forgery, and the out-of-band tool is assumed honest.
- **Small sample.** 80 items x 2 repeats. The in-band "benefit retained" ratio is unstable because its denominator is small; read its sign more than its size.
- **Design changed after a pilot.** The first item design (3 true, 2 false, 1 neutral documents) was too easy (5% false adoption with no labels), so it was rebalanced to 2/2/2. Hypotheses did not change.
- **Run quality.** 5 of 960 runs ended in an error and 0.5% gave no parseable answer.
- **Not run.** Track-record arms (A2, A5) and the wording ablation.

## Dual-use and ethics

The finding that forged in-band labels raise false-answer adoption could be read as a recipe for attackers. We judge the risk low: the attack is trivial and already obvious to anyone planning a poisoning attack, while the defensive finding (deliver reliability information through a channel the content author cannot write to) is actionable for builders. All entities are fictional and all domains end in `.example`. No human participants or personal data are involved.

## Reproducibility notes

- Model `command-a-03-2025`, temperature 0.3, 80 items, 2 repeats, bootstrap over items.
- Sampling at temperature above 0 means a re-run will not match exactly; the cached responses in `cache/` reproduce a run exactly if included.
- Commit `items.json`, `runs.jsonl` and `results.md` alongside the code so others can check the analysis without paying for the API calls. They contain no secrets.

## License

Add a license before publishing (MIT is a common choice for research code).

## Citation

```
@misc{signalshield2026,
  title  = {SignalShield: Do Reliability Labels Survive an Adversary?},
  author = {Muhammad Bilal Yousaf},
  year   = {2026},
  note   = {Apart Research AI x Epistemics Research Sprint}
}
```

