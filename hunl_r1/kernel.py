#!/usr/bin/env python3
"""R1: exact-card, perfect-recall, 100BB heads-up no-limit Hold'em EFG.

Python 3.10+; standard library only. All monetary quantities and probabilities
are fractions.Fraction. No strategy, card bucketing, or external evaluator is
needed. Chance is lazy: iterating the complete game is deliberately not the
default command. Read docs/r1-game-specification.md for the normative game
and complete grammar. Run these commands from the repository root:

    python3 -m hunl_r1 --demo
    python3 -m hunl_r1 --preflop

The complete reference export is data/preflop-tree.json.

The Betting summary is a public transition cache key, NEVER an information set.
Game.history retains every public action and reveal, including own actions.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import combinations
from math import comb
from typing import Iterator

VERSION = "R1"
F = Fraction
SB, BB = 0, 1
DECK = tuple(range(52))
STREETS = ("preflop", "flop", "turn", "river")


def money(value: int | Fraction) -> Fraction:
    """Accept exact integers/Fractions only; reject floats and booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise TypeError("amount must be int or Fraction")
    return Fraction(value)


@dataclass(frozen=True)
class Betting:
    street: int = 0
    mode: str = "act"
    actor: int = SB
    C: Fraction = F(0)
    c: tuple[Fraction, Fraction] = (F(1, 2), F(1))
    level: int = 1
    delta: Fraction = F(1)
    route: tuple[str, ...] = ()
    limped: bool = False
    folder: int = -1

    def __post_init__(self) -> None:
        object.__setattr__(self, "C", money(self.C))
        object.__setattr__(self, "c", tuple(money(x) for x in self.c))
        object.__setattr__(self, "delta", money(self.delta))
        if self.street not in range(4) or self.mode not in {
            "act", "deal", "runout", "fold", "showdown"
        }:
            raise ValueError("invalid street or mode")
        if len(self.c) != 2 or not 0 <= self.C <= 100:
            raise ValueError("invalid contributions")
        if any(x < 0 or self.C + x > 100 for x in self.c):
            raise ValueError("contribution outside stack")
        if self.delta < 0 or self.level < 0:
            raise ValueError("negative increment or level")
        if self.actor != -1 and self.actor not in (SB, BB):
            raise ValueError("invalid actor")
        if (self.mode == "act") != (self.actor in (SB, BB)):
            raise ValueError("actor and mode disagree")


@dataclass(frozen=True)
class Action:
    kind: str
    target: Fraction | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"F", "C", "X", "B", "R"}:
            raise ValueError("unknown action")
        if self.kind in {"F", "X"}:
            if self.target is not None:
                raise ValueError("fold/check has no target")
        else:
            if self.target is None:
                raise ValueError("missing target")
            object.__setattr__(self, "target", money(self.target))
            if self.target <= 0:
                raise ValueError("nonpositive target")

    def token(self) -> str:
        return self.kind if self.target is None else self.kind + str(self.target)


def initial_betting() -> Betting:
    return Betting()


def cap(b: Betting) -> Fraction:
    """Redundant commitment bound, not a discretionary live raise endpoint."""
    return F(100) if b.street == 0 else 100 - b.C


_PREFLOP_RAW: dict[tuple[str, ...], tuple[int, ...]] = {
    (): (2, 3),
    ("C",): (4,),
    ("C", "R4"): (12,),
    ("C", "R4", "R12"): (28,),
    ("C", "R4", "R12", "R28"): (60,),
    ("R2",): (8,),
    ("R2", "R8"): (22,),
    ("R2", "R8", "R22"): (36, 50),
    ("R2", "R8", "R22", "R36"): (50,),
    ("R3",): (11,),
    ("R3", "R11"): (28,),
    ("R3", "R11", "R28"): (60,),
}


def raw_targets(b: Betting) -> tuple[Fraction, ...]:
    if b.mode != "act":
        return ()
    f = b.c[1 - b.actor]
    R = 100 - b.C
    if f >= R or b.level >= cap(b):
        return ()
    if b.street == 0:
        try:
            return tuple(F(x) for x in _PREFLOP_RAW[b.route])
        except KeyError as exc:
            raise ValueError("unrecognized preflop route") from exc
    P = 2 * b.C
    if b.c == (F(0), F(0)):
        if b.street == 1:
            return (P / 2, P) if b.limped else (P / 3, 2 * P / 3)
        if b.street == 2:
            return (P / 2, P)
        return (P / 2, P, 3 * P / 2, R)
    Q = P + 2 * f
    targets = (f + b.delta, f + Q / 2, f + Q)
    return targets + ((R,) if b.street == 3 else ())


def resolve(b: Betting, raw: int | Fraction) -> Fraction:
    """Half-up -> minimum -> mandatory snap. Eligibility lives in raw_targets."""
    if b.mode != "act":
        raise ValueError("resolver requires an acting state")
    x = money(raw)
    if x < 0:
        raise ValueError("negative raw size")
    f = b.c[1 - b.actor]
    opening = b.street > 0 and b.c == (F(0), F(0))
    minimum = F(1) if opening else f + b.delta
    rounded = (2 * x.numerator + x.denominator) // (2 * x.denominator)
    target = max(F(rounded), minimum)
    if (b.C + target >= 100
            or (b.street == 0 and target > 40)
            or (b.street in (1, 2) and 3 * (b.C + target) > 200)):
        target = 100 - b.C
    return target


def actions(b: Betting) -> tuple[Action, ...]:
    if b.mode != "act":
        return ()
    own, f = b.c[b.actor], b.c[1 - b.actor]
    if own > f:
        raise ValueError("actor already leads the wager")
    passive = (Action("F"), Action("C", f)) if own < f else (Action("X"),)
    kind = "B" if b.street > 0 and b.c == (F(0), F(0)) else "R"
    targets = sorted({resolve(b, x) for x in raw_targets(b)})
    if any(t <= f or t > 100 - b.C or t.denominator != 1 for t in targets):
        raise ValueError("invalid resolved aggression")
    return passive + tuple(Action(kind, t) for t in targets)


def _settle(b: Betting, matched: Fraction, *, limped: bool | None = None) -> Betting:
    total = b.C + matched
    mode = "showdown" if b.street == 3 else ("runout" if total == 100 else "deal")
    return Betting(
        street=min(3, b.street + 1), mode=mode, actor=-1, C=total,
        c=(F(0), F(0)), level=0, delta=F(0), route=(),
        limped=b.limped if limped is None else limped, folder=-1,
    )


def step(b: Betting, a: Action) -> Betting:
    """Apply one offered player action; reject omitted/off-tree actions."""
    if a not in actions(b):
        raise ValueError("action is not offered")
    p, f = b.actor, b.c[1 - b.actor]
    if a.kind == "F":
        return replace(b, mode="fold", actor=-1, folder=p)
    if a.kind == "X":
        if b.street == 0:
            return _settle(b, F(1), limped=True)
        if p == BB:
            return replace(b, actor=SB)
        return _settle(b, F(0))
    if a.kind == "C":
        if b.street == 0 and b.route == ():
            return replace(b, actor=BB, c=(F(1), F(1)), route=("C",))
        return _settle(b, f)
    if a.target is None:  # defensive; Action already prevents this
        raise ValueError("missing aggressive target")
    contributions = list(b.c)
    contributions[p] = a.target
    route = b.route + (a.token(),) if b.street == 0 else ()
    return replace(b, actor=1-p, c=tuple(contributions), level=b.level+1,
                   delta=a.target-f, route=route)


def advance_board(b: Betting) -> Betting:
    """Advance the public control state after one correctly scheduled reveal."""
    if b.mode == "deal":
        return replace(b, mode="act", actor=BB)
    if b.mode == "runout":
        if b.street == 3:
            return replace(b, mode="showdown")
        return replace(b, street=b.street + 1)
    raise ValueError("no public-card deal is pending")


@dataclass(frozen=True)
class ChanceEvent:
    kind: str
    cards: tuple[int, ...]


@dataclass(frozen=True)
class Game:
    betting: Betting
    holes: tuple[tuple[int, int], tuple[int, int]] | None = None
    board: tuple[int, ...] = ()
    history: tuple[tuple, ...] = (("blinds", F(1, 2), F(1)),)


def new_game() -> Game:
    return Game(initial_betting())


def node_kind(g: Game) -> str:
    if g.holes is None or g.betting.mode in {"deal", "runout"}:
        return "chance"
    return "player" if g.betting.mode == "act" else "terminal"


def _cards_ok(cards: tuple[int, ...]) -> bool:
    return (isinstance(cards, tuple)
            and all(type(x) is int and 0 <= x < 52 for x in cards)
            and len(set(cards)) == len(cards))


def _remaining(g: Game) -> tuple[int, ...]:
    if g.holes is None:
        return DECK
    used = set(g.holes[0] + g.holes[1] + g.board)
    return tuple(c for c in DECK if c not in used)


def chance_probability(g: Game, event: ChanceEvent) -> Fraction:
    """Return exact edge probability, or zero for an illegal represented event."""
    if node_kind(g) != "chance" or not isinstance(event, ChanceEvent):
        return F(0)
    cards = event.cards
    if not _cards_ok(cards):
        return F(0)
    if g.holes is None:
        if (event.kind != "holes" or len(cards) != 4
                or cards[0] >= cards[1] or cards[2] >= cards[3]):
            return F(0)
        return F(1, comb(52, 2) * comb(50, 2))
    street = g.betting.street
    need = 3 if street == 1 else 1
    if (street not in (1, 2, 3) or event.kind != STREETS[street]
            or len(cards) != need or (need == 3 and cards != tuple(sorted(cards)))
            or any(c not in _remaining(g) for c in cards)
            or len(g.board) != {1: 0, 2: 3, 3: 4}[street]):
        return F(0)
    return F(1, comb(len(_remaining(g)), need))


def chance_events(g: Game) -> Iterator[tuple[ChanceEvent, Fraction]]:
    """Lazy exact support. It is never a list of all future complete histories."""
    if node_kind(g) != "chance":
        raise ValueError("not a chance node")
    if g.holes is None:
        probability = F(1, comb(52, 2) * comb(50, 2))
        for sb in combinations(DECK, 2):
            remainder = tuple(x for x in DECK if x not in sb)
            for bb in combinations(remainder, 2):
                yield ChanceEvent("holes", sb + bb), probability
        return
    remaining = _remaining(g)
    street = g.betting.street
    need = 3 if street == 1 else 1
    probability = F(1, comb(len(remaining), need))
    for cards in combinations(remaining, need):
        yield ChanceEvent(STREETS[street], cards), probability


def deal(g: Game, event: ChanceEvent) -> Game:
    if chance_probability(g, event) == 0:
        raise ValueError("illegal chance event")
    if event.kind == "holes":
        cards = event.cards
        return replace(g, holes=(cards[:2], cards[2:]))
    return replace(g, betting=advance_board(g.betting), board=g.board+event.cards,
                   history=g.history+((event.kind, event.cards),))


def player_actions(g: Game) -> tuple[Action, ...]:
    return actions(g.betting) if node_kind(g) == "player" else ()


def play(g: Game, a: Action) -> Game:
    if node_kind(g) != "player":
        raise ValueError("not a player node")
    b = g.betting
    successor = step(b, a)
    token = ("action", b.street, b.actor, a.kind, a.target)
    return replace(g, betting=successor, history=g.history+(token,))


def observation(g: Game, player: int) -> tuple:
    if player not in (SB, BB) or g.holes is None:
        raise ValueError("no such player's dealt observation")
    return g.holes[player], g.board, g.history


def infoset_key(g: Game) -> tuple:
    if node_kind(g) != "player":
        raise ValueError("information sets belong to player decisions")
    p = g.betting.actor
    return (p,) + observation(g, p)


def runout_probability(g: Game, missing_board: tuple[int, ...]) -> Fraction:
    """Probability of one street-labelled complete forced runout.

    The first three elements form an unordered/sorted flop if none is revealed;
    later elements are turn then river. No betting event is collapsed into this
    calculation. Folds and ordinary betting/deal nodes have probability zero.
    """
    if (g.holes is None or g.betting.C != 100
            or g.betting.mode not in {"runout", "showdown"}
            or len(missing_board) != 5-len(g.board)
            or not _cards_ok(missing_board)
            or any(x not in _remaining(g) for x in missing_board)):
        return F(0)
    if len(g.board) == 0 and missing_board[:3] != tuple(sorted(missing_board[:3])):
        return F(0)
    n = len(_remaining(g))
    probability = F(1)
    if len(g.board) == 0:
        probability /= comb(n, 3)
        n -= 3
        probability /= n * (n-1)
    elif len(g.board) == 3:
        probability /= n * (n-1)
    elif len(g.board) == 4:
        probability /= n
    elif len(g.board) != 5:
        return F(0)
    return probability


def _rank_five_unchecked(cards: tuple[int, ...]) -> tuple[int, ...]:
    ranks = sorted((c // 4 + 2 for c in cards), reverse=True)
    groups = sorted(((n, r) for r, n in Counter(ranks).items()), reverse=True)
    flush = len({c % 4 for c in cards}) == 1
    unique = sorted(set(ranks), reverse=True)
    straight = 0
    if len(unique) == 5:
        if unique[0]-unique[-1] == 4:
            straight = unique[0]
        elif unique == [14, 5, 4, 3, 2]:
            straight = 5
    if flush and straight:
        result = (8, straight)
    elif groups[0][0] == 4:
        result = (7, groups[0][1], groups[1][1])
    elif groups[0][0] == 3 and groups[1][0] == 2:
        result = (6, groups[0][1], groups[1][1])
    elif flush:
        result = (5, *ranks)
    elif straight:
        result = (4, straight)
    elif groups[0][0] == 3:
        result = (3, groups[0][1], *sorted((r for n, r in groups[1:]), reverse=True))
    elif groups[0][0] == 2 and groups[1][0] == 2:
        result = (2, max(groups[0][1], groups[1][1]),
                  min(groups[0][1], groups[1][1]), groups[2][1])
    elif groups[0][0] == 2:
        result = (1, groups[0][1], *sorted((r for n, r in groups[1:]), reverse=True))
    else:
        result = (0, *ranks)
    return result + (0,) * (6-len(result))


def rank_five(cards: tuple[int, ...]) -> tuple[int, ...]:
    cards = tuple(cards)
    if len(cards) != 5 or not _cards_ok(cards):
        raise ValueError("rank_five needs five distinct deck cards")
    return _rank_five_unchecked(cards)


def evaluate(cards: tuple[int, ...]) -> tuple[int, ...]:
    """Exact best-five value; comparable category/kicker tuple, no suit tiebreak."""
    cards = tuple(cards)
    if len(cards) not in (5, 6, 7) or not _cards_ok(cards):
        raise ValueError("evaluate needs five, six, or seven distinct deck cards")
    return max(_rank_five_unchecked(hand) for hand in combinations(cards, 5))


def payoff(g: Game) -> tuple[Fraction, Fraction]:
    b = g.betting
    if b.mode == "fold":
        loss = b.C + b.c[b.folder]
        return (-loss, loss) if b.folder == SB else (loss, -loss)
    if b.mode != "showdown" or g.holes is None or len(g.board) != 5:
        raise ValueError("payoff requires a terminal complete history")
    left, right = (evaluate(h + g.board) for h in g.holes)
    sb = b.C * ((left > right) - (left < right))
    return sb, -sb


def preflop_tree() -> list[dict]:
    """Every distinct preflop public decision prefix; no monetary-state merging."""
    rows: list[dict] = []
    todo = [((), initial_betting())]
    while todo:
        path, b = todo.pop()
        row = {"prefix": list(path), "actor": ("SB", "BB")[b.actor],
               "commitments": [str(x) for x in b.c], "level": b.level,
               "delta": str(b.delta), "edges": []}
        pending = []
        for a in actions(b):
            after = step(b, a)
            edge: dict = {"action": a.token()}
            nextpath = path+(a.token(),)
            if after.mode == "act":
                edge["next_prefix"] = list(nextpath)
                pending.append((nextpath, after))
            elif after.mode == "fold":
                edge["terminal"] = "fold"
                edge["payoff_SB_BB"] = [str(x) for x in payoff(Game(after))]
            else:
                edge["next_mode"] = after.mode
                edge["C"] = str(after.C)
                edge["pot"] = str(2*after.C)
                edge["next_street"] = STREETS[after.street]
            row["edges"].append(edge)
        rows.append(row)
        todo.extend(reversed(pending))
    return rows


def demo() -> dict:
    """A complete legal check-through hand, including all exact chance events."""
    g = new_game()
    chance_product = F(1)
    event = ChanceEvent("holes", (0, 1, 4, 5))
    chance_product *= chance_probability(g, event)
    g = deal(g, event)
    g = play(g, Action("C", F(1)))
    g = play(g, Action("X"))
    for kind, cards in (("flop", (8, 12, 16)), ("turn", (20,)), ("river", (24,))):
        event = ChanceEvent(kind, cards)
        chance_product *= chance_probability(g, event)
        g = deal(g, event)
        g = play(g, Action("X"))
        g = play(g, Action("X"))
    return {"version": VERSION, "status": "PASS", "mode": g.betting.mode,
            "board": list(g.board), "chance_product": str(chance_product),
            "payoff_SB_BB": [str(x) for x in payoff(g)]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflop", action="store_true", help="emit complete preflop JSON")
    group.add_argument("--demo", action="store_true", help="play an exact complete demo")
    args = parser.parse_args()
    print(json.dumps(preflop_tree() if args.preflop else demo(), indent=2))


if __name__ == "__main__":
    main()
