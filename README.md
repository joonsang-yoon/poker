# R1 HUNL reference kernel

This repository provides the exact-game reference kernel for 100 BB R1 heads-up
no-limit Hold'em (HUNL), independent exhaustive validators, and four peer DCFR
derivations. No strategy trainer or computed equilibrium certificate is
implemented.

[Game specification](docs/r1-game-specification.md) ·
[Documentation reading order](docs/README.md#reading-order) ·
[DCFR comparison](docs/dcfr/README.md#peer-derivations)

## Quickstart

Use Python 3.10+ and the standard library; no installation is required. Run from
the repository root. For this Windows/WSL checkout, run Python and Git inside WSL.

```sh
python3 -m hunl_r1 --demo
python3 -m hunl_r1 --preflop
```

The demo plays a complete exact-card hand and prints JSON. `--preflop`
prints the complete preflop adjacency as JSON. The [validation suite](#validation)
compares that export with the reference JSON.

Use the game API from Python:

```python
from hunl_r1 import kernel

game = kernel.new_game()
```

## Validation

Run from the repository root in a WSL shell. Use a UTC-timestamped log for each
run and capture the validator's exit status before inspecting the log:

```sh
validation_log="artifacts/validation/run-$(date -u +%Y%m%dT%H%M%SZ).log"
python3 -u -m validation > "$validation_log" 2>&1
validation_status=$?
printf 'Exit status: %s\nLog: %s\n' "$validation_status" "$validation_log"
tail -n 1 "$validation_log"
```

The complete independent suite includes every physical five-card hand and can
take several minutes. Success requires both printed `Exit status: 0` and a final
log line of `RESULT=PASS`. If either is missing, inspect the full log before
reporting success. The log records the command, Python version, timestamps,
source hashes, and executed coverage.

The suite checks betting transitions, cards and chance, full-history information
sets, ranking, net payoffs, and agreement with the reference preflop export.
It does not compute or certify an equilibrium strategy.

New validation logs are ignored by Git. Use a fresh run to validate this checkout;
the [historical reference run](artifacts/validation/reference-run.log) records
the original bundle's execution. See [source provenance](docs/provenance.md)
for file mappings and historical validation context.

## Repository map

| Location | Purpose |
| --- | --- |
| [hunl_r1/](hunl_r1/) | [Reference kernel](hunl_r1/kernel.py), public game API, and CLI |
| [validation/](validation/) | [Full-suite runner](validation/__main__.py) and independent betting and card oracles |
| [data/](data/) | [Complete reference preflop adjacency](data/preflop-tree.json) |
| [artifacts/validation/](artifacts/validation/) | [Immutable historical run](artifacts/validation/reference-run.log) and Git-ignored current run logs |
| [docs/](docs/README.md) | [Governing game specification](docs/r1-game-specification.md), reading order, and [source provenance](docs/provenance.md) |
| [docs/dcfr/](docs/dcfr/README.md) | Shared request and comparison of four peer solver designs |
| [AGENTS.md](AGENTS.md) | Editing conventions, invariants, and required checks |
