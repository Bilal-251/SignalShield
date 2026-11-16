# Pre-registration (commit before the main run)

Model: Cohere command-a-03-2025 ( temperature 0.3), single model. Items: fictional-entity multiple choice, 6 docs each (3 true, 2 false, 1 neutral).
Primary metric: false-answer adoption rate (item-level mean over repeats). Intervals: bootstrap over items.

- H1: Honest in-band labels (A1) reduce adoption versus no labels (A0).
- H2: Forged in-band labels (A4) retain less than 50% of A1's benefit.
- H3: Out-of-band labels under forgery (A6) retain more of A3's benefit than in-band under forgery (A4 vs A1).
- H4: Honest labels with tiers reversed (A7) lower accuracy versus A0.

Success is not required for any hypothesis; all results are reported. Wording ablation (W1, W2) is exploratory.
Known limitation: in A1 and A3 labels are perfectly informative by construction (an upper bound).
