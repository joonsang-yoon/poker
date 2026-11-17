# Agent guide

Exact 100 BB R1 HUNL reference kernel, independent validators, and four peer
DCFR derivations. No strategy trainer or computed equilibrium certificate is implemented.

## Sources and layout

The [R1 game specification](docs/r1-game-specification.md) governs. Derivations
A–D are equal peers and do not override it.

| Task | Start here |
| --- | --- |
| Game mechanics or API | Game specification and [public kernel](hunl_r1/kernel.py) |
| Validation | [Validation contract](docs/r1-game-specification.md#9-exhaustive-validation-contract-and-scope) and [independent suite](validation/) |
| Documentation | [Reading order](docs/README.md#reading-order) and [source provenance](docs/provenance.md) |
| DCFR design | [Peer comparison](docs/dcfr/README.md#peer-derivations), then the relevant derivation |

See the [repository map](README.md#repository-map) for file locations.

## Editing conventions

- Run Python and Git inside WSL from the repository root. Use Python 3.10+
  and the standard library; no installation is required.
- Check `git status` before and after edits. Preserve user changes and staging;
  stage or commit only when requested.
- Use snake_case for Python modules and lowercase kebab-case for documents and
  data. Keep `README.md` and `AGENTS.md`; separate code, validation, reference
  data, documentation, and run artifacts.
- During editorial edits, preserve equations, notation, numbered sections,
  technical claims, and the verbatim derivation request. Change mathematics
  only on explicit request.
- Label original hashes and reported runs historical; keep
  `artifacts/validation/reference-run.log` immutable.

## Game and validation invariants

- Preserve exact rational monetary amounts and chance probabilities.
- Keep complete public histories and private-hand information sets. A cached
  mechanics state is not an information-set identifier.
- Preserve sizing order: half-up rounding → minimum → all-in snap →
  deduplication. Formal caps remain redundant bounds.
- Preserve exact card support, labeled turn/river reveals, best-five ranking,
  chance-only called-all-in runouts, and net zero-sum payoffs.
- Keep validator expectations and exploration successors independent of the
  kernel; call kernel helpers only for actual results being checked.
- Use explicit exceptions to keep checks active under optimized Python.
  Never replace exhaustive validation with sampling or a shortened mode.

## Change verification

Use the canonical [quickstart](README.md#quickstart) and
[validation commands](README.md#validation).

| Change | Required verification |
| --- | --- |
| Documentation only | Check links, anchors, command examples, whitespace, and the diff. |
| Code, imports, filesystem paths, or game artifacts | Run the demo and full validation suite, including its comparison of the preflop export with the reference JSON. |

For full validation, require exit code zero and `RESULT=PASS`. Record current
source hashes, coverage, and results in a fresh, Git-ignored log. `--preflop`
only prints the export; the full suite performs the reference comparison.

Report checks actually run and their scope. Mechanics validation establishes
neither solver convergence nor exploitability.
