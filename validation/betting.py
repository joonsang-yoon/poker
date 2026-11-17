#!/usr/bin/env python3
"""Independent exhaustive R1 betting/control validator; standard library only.

The oracle was authored from the frozen written R1 contract, without reading the
system-under-test implementation. It uses integer half-BB accounting, its own
state/actions, its own policy, and its own transitions. The frontier originates
from oracle successors, never from the implementation's offered actions.

Every reachable public mechanical/control state is visited without a depth
cutoff. Equal mechanical states reuse a transition check; this does not merge
histories or information sets in the EFG. Card-independent betting rules make
this finite quotient exhaustive for betting/control behavior on every deal.

All checks are explicit exceptions and remain enabled under python -O.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
from pathlib import Path
import platform
import sys

from hunl_r1 import kernel as sut


F = Fraction


class VerificationError(Exception):
    """A concrete independent expected/observed comparison failed."""


def require(condition, message, *detail):
    if not condition:
        suffix = "" if not detail else " | " + " | ".join(repr(x) for x in detail)
        raise VerificationError(message + suffix)


@dataclass(frozen=True, slots=True)
class Position:
    # All monetary fields below are integer half-BB units.
    street: int
    phase: str
    turn: int
    carried: int
    paid0: int
    paid1: int
    depth: int
    increment: int
    path: tuple[str, ...]
    unraised_limp: bool
    folded: int

    def paid(self, player):
        return self.paid0 if player == 0 else self.paid1


@dataclass(frozen=True, slots=True)
class Choice:
    kind: str
    units: int | None = None


ORIGIN = Position(0, "act", 0, 0, 1, 2, 1, 2, (), False, -1)

# Independently transcribed from the complete written preflop mapping.
PRE = {
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


def maximum(s):
    return 200 - s.carried


def bound(s):
    return 100 if s.street == 0 else maximum(s) // 2


def own_and_faced(s):
    return s.paid(s.turn), s.paid(1 - s.turn)


def can_increase(s):
    if s.phase != "act":
        return False
    _, faced = own_and_faced(s)
    return faced < maximum(s) and s.depth < bound(s)


def unopened(s):
    return s.street > 0 and s.depth == 0


def intentions(s):
    """Raw targets in BB, entirely independent of the SUT policy."""
    if not can_increase(s):
        return ()
    if s.street == 0:
        require(s.path in PRE, "Oracle preflop mapping is incomplete", s)
        return tuple(F(x) for x in PRE[s.path])
    C = F(s.carried, 2)
    P = 2 * C
    R = 100 - C
    if unopened(s):
        if s.street == 1:
            return (P / 2, P) if s.unraised_limp else (P / 3, 2 * P / 3)
        if s.street == 2:
            return (P / 2, P)
        return (P / 2, P, 3 * P / 2, R)
    f = F(s.paid(1 - s.turn), 2)
    d = F(s.increment, 2)
    Q = P + 2 * f
    raw = (f + d, f + Q / 2, f + Q)
    return raw + (R,) if s.street == 3 else raw


def rounded_up_at_half(value):
    require(isinstance(value, (int, F)) and not isinstance(value, bool),
            "Oracle received a nonexact raw amount", value)
    q = F(value)
    require(q >= 0, "Oracle received a negative raw amount", value)
    whole, rest = divmod(q.numerator, q.denominator)
    return whole + (2 * rest >= q.denominator)


def destination(s, raw):
    """Return a final target in half-BB units, with independent rule order."""
    f = s.paid(1 - s.turn)
    floor_units = 2 if unopened(s) else f + s.increment
    rounded_units = 2 * rounded_up_at_half(raw)
    candidate = rounded_units if rounded_units >= floor_units else floor_units
    total = s.carried + candidate
    hit = total >= 200
    if s.street == 0:
        hit = hit or candidate > 80
    elif s.street in (1, 2):
        hit = hit or 3 * total > 400
    return maximum(s) if hit else candidate


def available(s):
    if s.phase != "act":
        return ()
    own, faced = own_and_faced(s)
    if own == faced:
        result = [Choice("X")]
    else:
        require(own < faced, "Oracle actor unexpectedly leads the wager", s)
        result = [Choice("F"), Choice("C", faced)]
    kind = "B" if unopened(s) else "R"
    result.extend(Choice(kind, b) for b in sorted({destination(s, x) for x in intentions(s)}))
    return tuple(result)


def completed(s, matched, limped=None):
    total = s.carried + matched
    limp = s.unraised_limp if limped is None else limped
    if s.street == 3:
        phase, street = "showdown", 3
    else:
        phase, street = ("runout" if total == 200 else "deal"), s.street + 1
    return Position(street, phase, -1, total, 0, 0, 0, 0, (), limp, -1)


def after_choice(s, a):
    """Independent accounting transition; selected actions are checked above."""
    require(a in available(s), "Oracle was asked to play an absent action", s, a)
    actor = s.turn
    own, faced = own_and_faced(s)
    if a.kind == "F":
        return replace(s, phase="fold", turn=-1, folded=actor)
    if a.kind == "C":
        if s == ORIGIN:
            return replace(s, turn=1, paid0=2, path=("C",))
        return completed(s, faced)
    if a.kind == "X":
        if s.street == 0:
            return completed(s, 2, True)
        if actor == 1:
            return replace(s, turn=0)
        return completed(s, 0)
    require(a.units is not None, "Oracle aggressive action lacks an amount", a)
    path = s.path
    if s.street == 0:
        require(a.units % 2 == 0, "Oracle preflop aggression is fractional", a)
        path += ("R" + str(a.units // 2),)
    change = {"paid0" if actor == 0 else "paid1": a.units}
    return replace(s, turn=1 - actor, depth=s.depth + 1,
                   increment=a.units - faced, path=path, **change)


def after_reveal(s):
    require(s.phase in ("deal", "runout"), "Oracle reveal in wrong phase", s)
    if s.phase == "deal":
        return replace(s, phase="act", turn=1)
    if s.street == 3:
        return replace(s, phase="showdown")
    return replace(s, street=s.street + 1)


def kernel_state(s):
    return sut.Betting(street=s.street, mode=s.phase, actor=s.turn,
                       C=F(s.carried, 2), c=(F(s.paid0, 2), F(s.paid1, 2)),
                       level=s.depth, delta=F(s.increment, 2), route=s.path,
                       limped=s.unraised_limp, folder=s.folded)


def kernel_action(a):
    return sut.Action(a.kind, None if a.units is None else F(a.units, 2))


def decoded_state(b):
    values = (b.C, b.c[0], b.c[1], b.delta)
    require(all(isinstance(x, F) for x in values),
            "SUT monetary state must use Fraction", b)
    require(all((2 * x).denominator == 1 for x in values),
            "SUT monetary state is not on the half-BB grid", b)
    require(type(b.street) is type(b.actor) is type(b.level) is type(b.folder) is int,
            "SUT control fields must be integers", b)
    require(type(b.limped) is bool and type(b.route) is tuple and type(b.c) is tuple,
            "SUT state containers or context types differ from the contract", b)
    return Position(b.street, b.mode, b.actor, int(2 * b.C), int(2 * b.c[0]),
                    int(2 * b.c[1]), b.level, int(2 * b.delta), b.route,
                    b.limped, b.folder)


def decoded_actions(actions):
    require(type(actions) is tuple, "SUT actions must be a canonical tuple", actions)
    result = []
    for a in actions:
        if a.target is None:
            require(a.kind in ("F", "X"), "Missing target on an amount action", a)
            result.append(Choice(a.kind))
        else:
            require(isinstance(a.target, F), "SUT action amount must be Fraction", a)
            require(a.kind in ("C", "B", "R"), "Target on a passive no-amount action", a)
            q = 2 * a.target
            require(q.denominator == 1, "SUT action is not on the half-BB grid", a)
            result.append(Choice(a.kind, int(q)))
    require(len(result) == len(set(result)), "SUT returned duplicate resolved actions", actions)
    return tuple(result)


def equal_state(actual, expected, label, *context):
    got = decoded_state(actual)
    require(got == expected, label, context, expected, got)


def reject(callable_, label, accepted=(ValueError,)):
    try:
        callable_()
    except accepted:
        return
    except Exception as exc:
        raise VerificationError(label + ": wrong exception " + repr(exc)) from exc
    raise VerificationError(label + ": action was accepted")


def invariants(s):
    require(s.street in (0, 1, 2, 3), "Invalid street", s)
    require(s.phase in ("act", "deal", "runout", "fold", "showdown"), "Invalid phase", s)
    require(0 <= s.carried <= 200 and s.carried % 2 == 0, "Invalid carried commitment", s)
    require(0 <= s.paid0 <= maximum(s) and 0 <= s.paid1 <= maximum(s),
            "Commitment exceeds available stack", s)
    require(s.increment >= 0 and s.depth >= 0, "Negative wager tracking", s)
    if s.phase == "act":
        require(s.turn in (0, 1) and s.folded == -1 and s.carried < 200,
                "Invalid decision control state", s)
        own, faced = own_and_faced(s)
        require(own <= faced, "Acting player is ahead of wager", s)
        if s.street == 0:
            require(s.carried == 0 and s.depth >= 1 and s.increment >= 2,
                    "Invalid preflop accounting", s)
            if own == faced:
                require(s.turn == 1 and (s.paid0, s.paid1) == (2, 2)
                        and s.path == ("C",), "Invalid BB option", s)
        else:
            require(s.carried >= 2 and s.path == (), "Invalid postflop context", s)
            require(all(x % 2 == 0 for x in (s.paid0, s.paid1, s.increment)),
                    "Fractional voluntary postflop amount", s)
            require((s.depth == 0) == (s.paid0 == s.paid1 == 0),
                    "Unopened-state level mismatch", s)
            require((s.depth == 0) == (s.increment == 0),
                    "Unopened-state increment mismatch", s)
            if s.depth:
                require(2 * s.depth <= faced, "Natural wager bound failed", s)
        require(s.depth <= bound(s), "Wager bound exceeded", s)
        if faced < maximum(s):
            require(s.depth < bound(s), "A live discretionary cap appeared", s)
        for paid in (s.paid0, s.paid1):
            if paid < maximum(s):
                if s.street == 0:
                    require(paid <= 80, "Unsnapped preflop target above 40", s)
                if s.street in (1, 2):
                    require(3 * (s.carried + paid) <= 400,
                            "Unsnapped flop/turn commitment above boundary", s)
    else:
        require(s.turn == -1, "Nondecision has an acting player", s)
        if s.phase == "fold":
            require(s.folded in (0, 1), "Fold has no folder", s)
            require(s.paid(s.folded) < s.paid(1 - s.folded),
                    "Folder was not facing a wager", s)
        else:
            require((s.paid0, s.paid1, s.depth, s.increment, s.path, s.folded)
                    == (0, 0, 0, 0, (), -1), "Closure did not reset street accounting", s)
            require(s.street in (1, 2, 3), "Invalid board/terminal street", s)
            if s.phase == "deal":
                require(0 < s.carried < 200, "Ordinary deal after exhausted stack", s)
            elif s.phase == "runout":
                require(s.carried == 200, "Runout is not fully matched all-in", s)
            elif s.phase == "showdown":
                require(s.street == 3 and 0 < s.carried <= 200,
                        "Premature or empty showdown", s)


def terminal_check(s, b):
    if s.phase == "fold":
        amount = F(s.carried + s.paid(s.folded), 2)
        expected = (-amount, amount) if s.folded == 0 else (amount, -amount)
        board = (0, 9, 20, 29, 36)[:(0, 3, 4, 5)[s.street]]
        g = sut.Game(betting=b, holes=((48, 49), (44, 45)), board=board, history=())
        actual = sut.payoff(g)
        require(actual == expected and all(isinstance(x, F) for x in actual),
                "Independent fold settlement differs", s, expected, actual)
        # Remove uncalled excess, then return the winner's own matched investment.
        pot_units = 2 * s.carried + s.paid0 + s.paid1
        excess_units = abs(s.paid1 - s.paid0)
        require(pot_units - excess_units == 2 * (s.carried + s.paid(s.folded)),
                "Fold refund accounting failed", s)
        return
    amount = F(s.carried, 2)
    fixtures = (
        (((48, 49), (44, 45)), (0, 9, 20, 29, 36), (amount, -amount)),
        (((44, 45), (48, 49)), (0, 9, 20, 29, 36), (-amount, amount)),
        (((1, 6), (9, 14)), (32, 36, 40, 44, 48), (F(0), F(0))),
    )
    for holes, board, expected in fixtures:
        g = sut.Game(betting=b, holes=holes, board=board, history=())
        actual = sut.payoff(g)
        require(actual == expected and all(isinstance(x, F) for x in actual),
                "Independent showdown payoff differs", s, expected, actual)
        require(sum(actual) == 0, "Payoff is not zero-sum", s, actual)


def follow(sequence):
    s = ORIGIN
    b = sut.initial_betting()
    for kind, amount in sequence:
        while s.phase in ("deal", "runout"):
            s = after_reveal(s)
            b = sut.advance_board(b)
            equal_state(b, s, "Fixture chance scheduling differs")
        a = Choice(kind, None if amount is None else 2 * amount)
        s = after_choice(s, a)
        b = sut.step(b, kernel_action(a))
        equal_state(b, s, "Fixture betting transition differs", kind, amount)
    return s, b


def boundary_checks():
    probes = (
        (ORIGIN, F(1), 2),
        (ORIGIN, F(201, 5), 40),
        (ORIGIN, F(81, 2), 100),
        (ORIGIN, F(40), 40),
        (ORIGIN, F(41), 100),
        (Position(0, "act", 0, 0, 20, 60, 4, 40, (), False, -1), F(31), 100),
        (Position(1, "act", 1, 20, 0, 0, 0, 0, (), False, -1), F(56), 56),
        (Position(1, "act", 1, 20, 0, 0, 0, 0, (), False, -1), F(57), 90),
        (Position(2, "act", 1, 20, 0, 0, 0, 0, (), False, -1), F(113, 2), 90),
        (Position(3, "act", 1, 20, 0, 0, 0, 0, (), False, -1), F(57), 57),
        (Position(1, "act", 0, 60, 20, 50, 2, 30, (), False, -1), F(30), 70),
        (Position(3, "act", 0, 120, 0, 60, 1, 60, (), False, -1), F(60), 40),
    )
    for s, raw, expected_bb in probes:
        require(destination(s, raw) == 2 * expected_bb, "Independent boundary fixture is inconsistent", s, raw)
        actual = sut.resolve(kernel_state(s), raw)
        require(actual == F(expected_bb) and isinstance(actual, F),
                "Resolver order or strict boundary differs", s, raw, expected_bb, actual)
    reject(lambda: sut.resolve(kernel_state(ORIGIN), 2.5), "Floating-point raw target",
           (TypeError, ValueError))
    s, b = follow((("R", 2), ("R", 8), ("R", 22)))
    require(Choice("R", 72) in available(s) and Choice("R", 200) in available(s),
            "Written preflop 36/shove alternatives are absent")
    require(decoded_actions(sut.actions(b)) == available(s), "Preflop 36/shove alternatives differ")
    s, b = follow((("R", 2), ("R", 8), ("R", 22), ("R", 36)))
    require(tuple(x for x in available(s) if x.kind == "R") == (Choice("R", 200),),
            "Raise after preflop 36 must snap to all-in")
    s, b = follow((("R", 3), ("R", 11), ("R", 28), ("C", 28), ("B", 19)))
    expected = (Choice("F"), Choice("C", 38), Choice("R", 76), Choice("R", 144))
    require(available(s) == expected and decoded_actions(sut.actions(b)) == expected,
            "Minimum raise to total 66 must coexist with a snapped raise", s)
    s, b = follow((("C", 1), ("X", None), ("X", None), ("X", None),
                   ("X", None), ("X", None), ("B", 1)))
    expected_raises = {Choice("R", 4), Choice("R", 6), Choice("R", 10), Choice("R", 198)}
    require({a for a in available(s) if a.kind == "R"} == expected_raises,
            "Written river minimum/pot/jam raise alternatives are incomplete")
    require(decoded_actions(sut.actions(b)) == available(s), "River direct jam or raise alternatives differ")
    reject(lambda: sut.step(sut.initial_betting(), sut.Action("X")), "Checking into posted blind")
    reject(lambda: sut.step(sut.initial_betting(), sut.Action("R", F(5, 2))),
           "Unretained fractional raise")
    reject(lambda: sut.step(sut.initial_betting(), sut.Action("C", F(2))),
           "Call with wrong target")
    reject(lambda: sut.step(sut.initial_betting(), sut.Action("F", F(1))),
           "Fold carrying an amount")
    reject(lambda: sut.advance_board(sut.initial_betting()), "Board advance during player decision")


def exhaustive():
    require(decoded_state(sut.initial_betting()) == ORIGIN, "Initial state differs from written rules")
    frontier = [ORIGIN]
    visited = set()
    witnessed = set()
    while frontier:
        s = frontier.pop()
        if s in visited:
            continue
        visited.add(s)
        invariants(s)
        b = kernel_state(s)
        expected_menu = available(s)
        actual_menu = decoded_actions(sut.actions(b))
        require(actual_menu == expected_menu, "Complete action menu differs", s, expected_menu, actual_menu)
        if s.phase in ("fold", "showdown"):
            terminal_check(s, b)
            continue
        if s.phase in ("deal", "runout"):
            expected = after_reveal(s)
            actual = sut.advance_board(b)
            equal_state(actual, expected, "Board-control successor differs", s)
            frontier.append(expected)
            if s.phase == "runout":
                witnessed.add("runout_" + str(s.street))
                require(expected.phase in ("runout", "showdown"),
                        "Runout resumed betting", s, expected)
            continue
        raw = intentions(s)
        got_raw = sut.raw_targets(b)
        require(type(got_raw) is tuple and all(isinstance(x, F) for x in got_raw),
                "Raw candidate API must return exact Fraction tuple", s, got_raw)
        require(set(got_raw) == set(raw), "Complete raw policy differs", s, raw, got_raw)
        got_cap = sut.cap(b)
        require(isinstance(got_cap, F) and got_cap == bound(s), "Natural cap differs", s, got_cap)
        for x in raw:
            actual = sut.resolve(b, x)
            expected = F(destination(s, x), 2)
            require(isinstance(actual, F) and actual == expected,
                    "Resolved target differs", s, x, expected, actual)
        if len({destination(s, x) for x in raw}) < len(raw):
            witnessed.add("deduplication")
        own, faced = own_and_faced(s)
        if faced == maximum(s):
            require(expected_menu == (Choice("F"), Choice("C", faced)),
                    "Facing all-in must expose only fold/call", s)
            witnessed.add("allin_response")
        if s.path == ("R2", "R8", "R22"):
            witnessed.add("preflop_36_alternative")
        if s.unraised_limp and s.street == 1 and s.depth == 0:
            require(tuple(a for a in expected_menu if a.kind == "B")
                    == (Choice("B", 2), Choice("B", 4)), "Limped flop lost distinct openings", s)
            witnessed.add("limped_flop")
        if s.street == 3 and can_increase(s):
            jam = Choice("B" if unopened(s) else "R", maximum(s))
            require(jam in expected_menu, "River explicit jam disappeared", s)
            witnessed.add("river_open_jam" if unopened(s) else "river_raise_jam")
        for a in expected_menu:
            expected = after_choice(s, a)
            actual = sut.step(b, kernel_action(a))
            equal_state(actual, expected, "Independent betting successor differs", s, a)
            frontier.append(expected)
            if a.kind in ("B", "R"):
                target = a.units
                require(target is not None and target % 2 == 0 and faced < target <= maximum(s),
                        "Aggressive target violates integer/stack/strict-increase rules", s, a)
                require(can_increase(s), "Aggression bypassed its eligibility gate", s, a)
                if target < maximum(s):
                    minimum = 2 if a.kind == "B" else faced + s.increment
                    require(target >= minimum, "Non-all-in under-raise", s, a)
                    if s.street in (1, 2) and s.carried + target == 132 and a.kind == "R":
                        witnessed.add("retained_total_66_raise")
                    if s.street == 3 and s.carried + target > F(400, 3):
                        witnessed.add("river_above_early_snap_boundary")
                elif a.kind == "R" and target - faced < s.increment:
                    witnessed.add("short_allin")
                require(expected.increment == target - faced and expected.depth == s.depth + 1,
                        "Aggression did not update actual increment/level", s, a, expected)
                old_pot = 2 * s.carried + s.paid0 + s.paid1
                new_pot = 2 * expected.carried + expected.paid0 + expected.paid1
                require(new_pot - old_pot == target - own, "Aggressive chip payment differs", s, a)
            elif a.kind == "C":
                old_pot = 2 * s.carried + s.paid0 + s.paid1
                call_cost = faced - own
                require(old_pot + call_cost == 2 * (s.carried + faced),
                        "Call-completed pot identity failed", s)
                if s == ORIGIN:
                    witnessed.add("limp_option")
                    require(expected.phase == "act" and expected.turn == 1,
                            "Limp incorrectly closed preflop", expected)
                elif expected.phase == "act":
                    raise VerificationError("A non-root call failed to close betting")
            elif a.kind == "X":
                if expected.phase == "act":
                    witnessed.add("first_check")
                else:
                    witnessed.add("checkthrough")
    needed = {"runout_1", "runout_2", "runout_3", "deduplication", "allin_response",
              "preflop_36_alternative", "limped_flop", "river_open_jam", "river_raise_jam",
              "retained_total_66_raise", "river_above_early_snap_boundary", "short_allin",
              "limp_option", "first_check", "checkthrough"}
    require(needed <= witnessed, "Required reachable behavior was not encountered", sorted(needed - witnessed))


def run():
    boundary_checks()
    print("PASS independent exact-rounding, strict-snap, minimum-before-snap and action-rejection checks.", flush=True)
    exhaustive()
    print("PASS independent exhaustive oracle-reachable betting and control-state traversal.", flush=True)
    print("PASS complete preflop and recursive postflop menus, minimum raises, river jams and deduplication.", flush=True)
    print("PASS all reachable stack, wager-level, actual-increment, pot, closure and natural-cap invariants.", flush=True)
    print("PASS all reachable fold and showdown payoff algebra; all-in responses and chance-only runouts.", flush=True)


def main():
    print("START " + datetime.now(timezone.utc).isoformat(), flush=True)
    print("Python " + platform.python_version() + " " + platform.python_implementation(), flush=True)
    for filename in ("hunl_r1/__init__.py", "hunl_r1/kernel.py",
                     "validation/__init__.py", "validation/betting.py"):
        path = Path(__file__).resolve().parents[1] / filename
        print("SHA256 " + filename + " " + hashlib.sha256(path.read_bytes()).hexdigest(), flush=True)
    try:
        run()
    except Exception as exc:
        print("FAIL " + type(exc).__name__ + ": " + str(exc), flush=True)
        print("END " + datetime.now(timezone.utc).isoformat(), flush=True)
        return 1
    print("PASS betting/control validation completed.", flush=True)
    print("END " + datetime.now(timezone.utc).isoformat(), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
