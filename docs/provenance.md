# Source mapping and provenance

[Documentation index](README.md) · [Validation guide](../README.md#validation)

## Original bundle

The original bundle, `hunl_r1.zip`, is not included. Its filenames and SHA-256
digests remain in the derivations as historical source identities. The table
below maps those filenames to this checkout; current hashes may differ after edits.

## File mapping

| Original location | Current location |
| --- | --- |
| `hunl_r1/EFG.md` | [R1 game specification](r1-game-specification.md) |
| `hunl_r1/kernel.py` | [Reference kernel](../hunl_r1/kernel.py) |
| `hunl_r1/preflop.json` | [Preflop tree](../data/preflop-tree.json) |
| `hunl_r1/validate.py` | [Full-suite entry point](../validation/__main__.py) |
| `hunl_r1/validate_betting.py` | [Betting validator](../validation/betting.py) |
| `hunl_r1/validate_cards.py` | [Card validator](../validation/cards.py) |
| `hunl_r1/actual_run.log` | [Historical reference run](../artifacts/validation/reference-run.log) |
| `docs/LLM_input_text.md` | [Original derivation request](dcfr/derivation-request.md) |
| `docs/LLM_output_text_version_a.md` | [Derivation A](dcfr/derivation-a.md) |
| `docs/LLM_output_text_version_b.md` | [Derivation B](dcfr/derivation-b.md) |
| `docs/LLM_output_text_version_c.md` | [Derivation C](dcfr/derivation-c.md) |
| `docs/LLM_output_text_version_d.md` | [Derivation D](dcfr/derivation-d.md) |

## Historical validation

The initial repository organization preserved the preflop JSON and historical
reference log byte-for-byte. It retained the game rules while updating the
specification's navigation and runnable-artifact instructions, kernel usage
documentation, and validator imports and paths.

The derivations' source audits report checks from their preparation, including
checks beyond the historical reference log. These reports and original hashes
remain historical; editorial changes do not reproduce those executions.
Mechanics checks do not certify an equilibrium strategy.

## Current validation

Follow the [validation guide](../README.md#validation) for a fresh mechanics run
and its acceptance checks. Record the command, current source hashes, executed
coverage, and results in a new, Git-ignored log. Preserve the historical reference
log and the derivations' original source digests.

The [agent guide](../AGENTS.md#change-verification) lists checks by change type.
