# DCFR derivations

[Documentation index](../README.md) · [R1 game specification](../r1-game-specification.md)

The four peers answer the [same derivation request](derivation-request.md):
exact R1 vectorized tabular DCFR and best-response certification requirements
in river → turn → flop → preflop order. Start with the
[documentation reading order](../README.md#reading-order), then use the
comparison tables below.

These are solver designs. No strategy trainer or computed equilibrium
certificate is implemented in this repository.

## Peer derivations

| Peer derivation | Organization |
| --- | --- |
| [Derivation A](derivation-a.md) | Certificate-first street dependencies and implementation proof obligations |
| [Derivation B](derivation-b.md) | Street requirements with continuation interfaces and a source register |
| [Derivation C](derivation-c.md) | Shared tensor contract, street derivations, and separate error/composition proofs |
| [Derivation D](derivation-d.md) | Shared monetary compiler, street hierarchies, and a collected execution specification |

Each peer retains its own notation, equations, and technical claims.
None is preferred or overrides the game specification.

## Compare by street

Use the table to open the same street in each peer. Each chapter links to
the other peers and back to its reading map.

| Street | Derivation A | Derivation B | Derivation C | Derivation D |
| --- | --- | --- | --- | --- |
| River | [A](derivation-a.md#river) | [B](derivation-b.md#river) | [C](derivation-c.md#river) | [D](derivation-d.md#river) |
| Turn | [A](derivation-a.md#turn) | [B](derivation-b.md#turn) | [C](derivation-c.md#turn) | [D](derivation-d.md#turn) |
| Flop | [A](derivation-a.md#flop) | [B](derivation-b.md#flop) | [C](derivation-c.md#flop) | [D](derivation-d.md#flop) |
| Preflop | [A](derivation-a.md#preflop) | [B](derivation-b.md#preflop) | [C](derivation-c.md#preflop) | [D](derivation-d.md#preflop) |

## Validation and provenance

See [source provenance](../provenance.md) for historical source identities,
current paths, and validation context. Use the
[validation guide](../../README.md#validation) for fresh mechanics checks;
these do not certify an equilibrium strategy.
