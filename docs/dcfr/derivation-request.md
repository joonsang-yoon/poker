# Original DCFR derivation request

[DCFR index](README.md) · [R1 game specification](../r1-game-specification.md)

The original brief below applies to peer derivations [A](derivation-a.md),
[B](derivation-b.md), [C](derivation-c.md), and [D](derivation-d.md).
It is retained verbatim. For current locations of its historical archive
filenames, see [source provenance](../provenance.md).

## Original text

From hunl_r1.zip (EFG.md governs; kernel.py/preflop.json), derive vectorized tabular DCFR in one English .md: river→turn→flop→preflop. Preserve exact EFG: cards/chance, full-history infosets (no state merging), half-up→minimum→snap→dedup, redundant caps, net payoffs, all-in runouts. Per street, root a strict top-down dependency hierarchy at BR-certified subgame exploitability≤0.005Pₑ (entry pot; preflop 1.5 BB). Define assumptions, exploitability, compatible boundary ranges, notation, tensor shapes/indices/masks. Recursively derive GPU primitives: best-five ranking, payoffs, blockers/chance, reaches, counterfactual values, regret matching, DCFR discounts, reach-weighted average strategies, infoset-consistent best responses, range-dependent continuation values. Specify initialization, normalization, zero-reach rules, update order; no black boxes. Separate backward evaluation from equilibrium solving. Prove numerical/continuation error propagation and local-to-global bound conditions.
