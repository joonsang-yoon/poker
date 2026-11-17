"""Independent exact-card, information, and settlement validation for R1.

Only public APIs from hunl_r1.kernel are used. Expected ranks, chance supports,
probabilities, observable histories, and payoffs are implemented here, without
calling a kernel rule helper to obtain an expected result.

Coverage has three distinct meanings and must not be conflated:
* Every physical five-card hand is compared with an independent direct ranker.
* For six and seven cards, every feasible rank-multiplicity vector is tested
  without a flush and with every feasible flush rank subset. These are complete
  semantic ranking classes, not every physical six/seven-card holding. A hand
  of at most seven cards cannot have two different suits with five cards. With
  no flush, rank multiplicities determine its rank; with a flush, multiplicities
  plus that suit's rank subset determine its rank. Representatives are actual
  legal hands. This gives exhaustive semantic-class coverage, not a claim that
  black-box tests alone prove the implementation is invariant within classes.
* The kernel's specified evaluate contract is max(rank_five(S)) over ALL
  five-card subsets S. Combined with the exhaustive five-card result, that
  composition proves best-five correctness when the supplied implementation
  implements that composition. Source inspection of that composition is the
  enclosing review's responsibility; this file does not read kernel source.

Betting validation separately exhausts the card-independent transition graph.
The chance-support bijection and history construction explain its lifting to
all compatible exact-card histories; this is not literal enumeration of the
astronomical product of all betting and card histories.

All checks raise explicitly and remain active under python -O. No scores,
betting-tree counts, or quantitative policy comparisons are printed.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction as F
from itertools import combinations, combinations_with_replacement, permutations
from math import comb
from hunl_r1 import kernel as K


DECK = tuple(range(52))
ROOT_PUBLIC = (("blinds", F(1, 2), F(1)),)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def rejected(function, *args):
    try:
        function(*args)
    except (ValueError, TypeError):
        return
    raise RuntimeError("Invalid input accepted by " + function.__name__)


def padded(category, *breakers):
    return (category,) + tuple(breakers) + (0,) * (5 - len(breakers))


def straight_high(ranks):
    values = set(ranks)
    if 14 in values:
        values.add(1)
    for high in range(14, 4, -1):
        if all(value in values for value in range(high - 4, high + 1)):
            return high
    return 0


def independent_rank(cards):
    """Direct 5/6/7-card evaluator; no best-five subset loop and no kernel call."""
    ranks = [card // 4 + 2 for card in cards]
    multiplicity = Counter(ranks)
    groups = sorted(multiplicity, reverse=True)
    suited = [[card // 4 + 2 for card in cards if card % 4 == suit]
              for suit in range(4)]
    flushes = [sorted(values, reverse=True) for values in suited if len(values) >= 5]
    straight_flush = max((straight_high(values) for values in flushes), default=0)
    if straight_flush:
        return padded(8, straight_flush)
    quads = [rank for rank in groups if multiplicity[rank] == 4]
    if quads:
        return padded(7, quads[0], max(rank for rank in groups if rank != quads[0]))
    trips = [rank for rank in groups if multiplicity[rank] >= 3]
    if trips:
        pairs = [rank for rank in groups if rank != trips[0] and multiplicity[rank] >= 2]
        if pairs:
            return padded(6, trips[0], pairs[0])
    if flushes:
        return padded(5, *max(tuple(values[:5]) for values in flushes))
    straight = straight_high(groups)
    if straight:
        return padded(4, straight)
    if trips:
        kickers = [rank for rank in groups if rank != trips[0]][:2]
        return padded(3, trips[0], *kickers)
    pairs = [rank for rank in groups if multiplicity[rank] >= 2]
    if len(pairs) >= 2:
        high, low = pairs[:2]
        return padded(2, high, low, max(rank for rank in groups if rank not in (high, low)))
    if pairs:
        return padded(1, pairs[0], *[rank for rank in groups if rank != pairs[0]][:3])
    return padded(0, *groups[:5])


def cards(text):
    ranks = "23456789TJQKA"
    suits = "cdhs"
    return tuple(4 * ranks.index(token[0]) + suits.index(token[1])
                 for token in text.split())


def hand_fixtures():
    examples = (
        ("Ac Kd 9h 5s 3c", padded(0, 14, 13, 9, 5, 3)),
        ("Ac Ad Kh 5s 3c", padded(1, 14, 13, 5, 3)),
        ("Ac Ad Kh Ks 3c", padded(2, 14, 13, 3)),
        ("Ac Ad Ah Ks 3c", padded(3, 14, 13, 3)),
        ("Ac 2d 3h 4s 5c", padded(4, 5)),
        ("Ac Jc 9c 5c 3c", padded(5, 14, 11, 9, 5, 3)),
        ("Ac Ad Ah Ks Kc", padded(6, 14, 13)),
        ("Ac Ad Ah As Kc", padded(7, 14, 13)),
        ("Ac 2c 3c 4c 5c", padded(8, 5)),
        ("Ac Kc Qc Jc Tc", padded(8, 14)),
        ("7c 7d 7h 6c 6d 6h Ac", padded(6, 7, 6)),
        ("Ac Ad Kc Kd Qc Qd 2s", padded(2, 14, 13, 12)),
        ("Ac 2d 3h 4s 5c 6d Kc", padded(4, 6)),
        ("Ac Ad Ah As Kc Qd Jh", padded(7, 14, 13)),
        ("Ac Jc 9c 5c 3c Ad Ah", padded(5, 14, 11, 9, 5, 3)),
    )
    for notation, expected in examples:
        hand = cards(notation)
        require(independent_rank(hand) == expected, "Independent fixture rank: " + notation)
        require(K.evaluate(hand) == expected, "Kernel fixture rank: " + notation)
        if len(hand) == 5:
            require(K.rank_five(hand) == expected, "Kernel five-card fixture: " + notation)
        for suit_map in permutations(range(4)):
            relabeled = tuple(4 * (card // 4) + suit_map[card % 4] for card in reversed(hand))
            require(K.evaluate(relabeled) == expected, "Suit/order invariance: " + notation)

    # A diverse seven-card hand whose best five do not occupy a fixed prefix.
    hand = cards("Ac 2c 3c 4c 5c Kd Kh")
    expected = padded(8, 5)
    for ordering in permutations(hand):
        require(K.evaluate(ordering) == expected, "Seven-card subset/order invariance")

    invalid_hands = (
        (0, 1, 2, 3), tuple(range(8)), (0, 1, 2, 3, 3),
        (-1, 1, 2, 3, 4), (0, 1, 2, 3, 52), (False, 1, 2, 3, 4),
        (0, 1, 2, 3, 4.0), (0, 1, 2, 3, "4"),
    )
    for invalid in invalid_hands:
        rejected(K.evaluate, invalid)
    for invalid in invalid_hands + (tuple(range(6)), tuple(range(7))):
        rejected(K.rank_five, invalid)


def exhaustive_five_cards():
    for hand in combinations(DECK, 5):
        expected = independent_rank(hand)
        actual = K.rank_five(hand)
        if actual != expected:
            raise RuntimeError(f"Five-card exhaustive mismatch: {hand}: {actual} != {expected}")


def nonflush_representative(ranks):
    # The suit cursor advances globally. Each repeated rank receives distinct
    # suits; all suit totals differ by at most one, so no suit has five cards.
    return tuple(4 * (rank - 2) + (index % 4) for index, rank in enumerate(ranks))


def flush_representative(multiplicity, flush_ranks):
    flush_ranks = frozenset(flush_ranks)
    hand = []
    for rank in sorted(multiplicity):
        count = multiplicity[rank]
        if rank in flush_ranks:
            hand.append(4 * (rank - 2))
            count -= 1
        # At most two cards are outside the designated flush for n<=7;
        # thus all required nonsuit-zero copies can use the other suits.
        require(count <= 3, "Feasible designated flush representative")
        hand.extend(4 * (rank - 2) + suit for suit in range(1, count + 1))
    return tuple(hand)


def exhaustive_semantic_classes():
    for size in (5, 6, 7):
        for ranks in combinations_with_replacement(range(2, 15), size):
            multiplicity = Counter(ranks)
            if max(multiplicity.values()) > 4:
                continue
            representatives = [nonflush_representative(ranks)]
            distinct = tuple(multiplicity)
            for flush_size in range(5, len(distinct) + 1):
                for flush_ranks in combinations(distinct, flush_size):
                    representatives.append(flush_representative(multiplicity, flush_ranks))
            for hand in representatives:
                require(len(hand) == size and len(set(hand)) == size,
                        "Structural representative legality")
                expected = independent_rank(hand)
                actual = K.evaluate(hand)
                if actual != expected:
                    raise RuntimeError(f"Semantic-class mismatch: {hand}: {actual} != {expected}")
                # Independently verify the direct reference ranker agrees with
                # the rule defining Hold'em best-five composition.
                composed = max(independent_rank(subhand) for subhand in combinations(hand, 5))
                require(expected == composed, "Independent direct/best-five agreement")


def holes_game(sb=(0, 1), bb=(4, 5)):
    game = K.new_game()
    event = K.ChanceEvent("holes", tuple(sb) + tuple(bb))
    result = K.deal(game, event)
    require(result.holes == (tuple(sb), tuple(bb)), "Private hands stored exactly")
    require(result.board == () and result.history == ROOT_PUBLIC,
            "Private deal must not enter public history")
    return result


def apply(game, kind, target=None):
    action = K.Action(kind, None if target is None else F(target))
    expected_token = ("action", game.betting.street, game.betting.actor, kind, action.target)
    result = K.play(game, action)
    require(result.history == game.history + (expected_token,), "Exact action-history append")
    require(result.holes == game.holes and result.board == game.board,
            "Player action cannot alter dealt cards")
    return result


def reveal(game, stage, values):
    values = tuple(values)
    event = K.ChanceEvent(stage, values)
    result = K.deal(game, event)
    require(result.history == game.history + ((stage, values),), "Exact board-history append")
    require(result.holes == game.holes and result.board == game.board + values,
            "Public reveal appends only newly revealed cards")
    return result


def check_observation(game):
    for player in (0, 1):
        expected = (game.holes[player], game.board, game.history)
        require(K.observation(game, player) == expected, "Exact player observation")
    if K.node_kind(game) == "player":
        player = game.betting.actor
        expected = (player, game.holes[player], game.board, game.history)
        require(K.infoset_key(game) == expected, "Perfect-recall exact information key")
    else:
        rejected(K.infoset_key, game)


def check_chance_outcomes(game, stage, batch_size):
    used = set(game.holes[0] + game.holes[1] + game.board)
    remaining = tuple(card for card in DECK if card not in used)
    expected_support = set(combinations(remaining, batch_size))
    expected_probability = F(1, comb(len(remaining), batch_size))
    seen = set()
    total_probability = F(0)
    for event, probability in K.chance_events(game):
        require(event.kind == stage, "Chance event stage")
        require(event.cards in expected_support and event.cards not in seen,
                "Board chance legal, canonical, unique support")
        require(probability == expected_probability, "Exact board chance probability")
        require(K.chance_probability(game, event) == expected_probability,
                "Board probability lookup agrees independently")
        seen.add(event.cards)
        total_probability += probability
    require(seen == expected_support and total_probability == 1,
            "Exhaustive board chance support and normalization")


def exhaustive_private_chance():
    root = K.new_game()
    require(K.node_kind(root) == "chance" and root.holes is None,
            "Root is private-card chance")
    require(root.history == ROOT_PUBLIC and root.board == (), "Root public observations")
    support_size = comb(52, 2) * comb(50, 2)
    expected_probability = F(1, support_size)
    occupied = bytearray(support_size)
    for event, probability in K.chance_events(root):
        require(event.kind == "holes" and len(event.cards) == 4, "Private chance shape")
        a, b, c, d = event.cards
        require(all(type(value) is int and 0 <= value < 52 for value in event.cards)
                and a < b and c < d and len(set(event.cards)) == 4,
                "Private chance legal canonical support")
        sb_index = a * (103 - a) // 2 + b - a - 1
        c_index = c - (a < c) - (b < c)
        d_index = d - (a < d) - (b < d)
        bb_index = c_index * (99 - c_index) // 2 + d_index - c_index - 1
        index = sb_index * comb(50, 2) + bb_index
        require(0 <= index < support_size and not occupied[index],
                "Private chance no duplicate outcome")
        occupied[index] = 1
        require(probability == expected_probability, "Exact private outcome probability")
        require(K.chance_probability(root, event) == expected_probability,
                "Private probability lookup")
    require(all(occupied) and expected_probability * len(occupied) == 1,
            "Complete private chance support and normalization")


def invalid_chance(game, events):
    for stage, values in events:
        try:
            event = K.ChanceEvent(stage, tuple(values))
        except (TypeError, ValueError):
            continue
        require(K.chance_probability(game, event) == 0, "Illegal chance event has zero mass")
        rejected(K.deal, game, event)


def chance_and_history_paths():
    root = K.new_game()
    invalid_chance(root, (
        ("holes", (0, 1, 2)), ("holes", (1, 0, 2, 3)),
        ("holes", (0, 1, 3, 2)), ("holes", (0, 1, 1, 2)),
        ("holes", (-1, 1, 2, 3)), ("holes", (0, 1, 2, 52)),
        ("holes", (False, 1, 2, 3)), ("holes", (0, 1, 2, 3.0)),
        ("flop", (0, 1, 2)), ("bogus", (0, 1, 2, 3)),
    ))
    require(tuple(K.player_actions(root)) == (), "No player actions at private chance")
    rejected(K.play, root, K.Action("F"))
    rejected(K.infoset_key, root)
    rejected(K.payoff, root)

    game = holes_game()
    check_observation(game)
    same_sb = holes_game((0, 1), (6, 7))
    require(K.infoset_key(game) == K.infoset_key(same_sb), "Opponent hand hidden from SB")
    different_sb = holes_game((2, 3), (4, 5))
    require(K.infoset_key(game) != K.infoset_key(different_sb), "Own hand retained exactly")
    bb_one = apply(game, "C", 1)
    bb_two = apply(different_sb, "C", 1)
    require(K.infoset_key(bb_one) == K.infoset_key(bb_two), "Opponent hand hidden from BB")
    require(game.history == ROOT_PUBLIC, "Persistent histories do not mutate parents")

    # A complete check-through run reaches a board-playing tie at C=1.
    game = apply(bb_one, "X")
    require(K.node_kind(game) == "chance" and game.betting.street == 1,
            "Limp/check reaches flop chance")
    check_chance_outcomes(game, "flop", 3)
    invalid_chance(game, (
        ("flop", (8, 8, 12)), ("flop", (12, 8, 16)),
        ("flop", (0, 8, 12)), ("flop", (4, 8, 12)),
        ("flop", (8, 12)), ("turn", (8,)),
    ))
    rejected(K.play, game, K.Action("X"))
    require(K.runout_probability(game, (8, 12, 16, 20, 24)) == 0,
            "Ordinary board chance is not forced runout")
    game = reveal(game, "flop", (8, 12, 16))
    check_observation(game)
    game = apply(apply(game, "X"), "X")
    check_chance_outcomes(game, "turn", 1)
    invalid_chance(game, (("turn", (8,)), ("turn", (4,)), ("turn", (20, 24))))
    game = reveal(game, "turn", (20,))
    check_observation(game)
    game = apply(apply(game, "X"), "X")
    check_chance_outcomes(game, "river", 1)
    invalid_chance(game, (("river", (20,)), ("river", (1,)), ("river", (24, 28))))
    game = reveal(game, "river", (24,))
    check_observation(game)
    final = apply(apply(game, "X"), "X")
    require(K.node_kind(final) == "terminal" and final.betting.C == 1,
            "Complete check-through showdown")
    require(K.payoff(final) == (F(0), F(0)), "Board-playing tie payoff")
    require(K.runout_probability(final, ()) == 0, "Ordinary showdown is not an all-in runout")
    rejected(K.play, final, K.Action("X"))

    # Same final set, different turn/river observation order must stay distinct.
    def chronological(turn, river):
        item = apply(apply(holes_game(), "C", 1), "X")
        item = reveal(item, "flop", (8, 12, 16))
        item = reveal(apply(apply(item, "X"), "X"), "turn", (turn,))
        return reveal(apply(apply(item, "X"), "X"), "river", (river,))
    ordered = chronological(20, 24)
    swapped = chronological(24, 20)
    require(set(ordered.board) == set(swapped.board), "Order fixture same final set")
    require(K.infoset_key(ordered) != K.infoset_key(swapped), "Reveal chronology retained")

    # Different public paths reach the same public mechanical flop state.
    def entered(sequence):
        item = holes_game()
        for kind, target in sequence:
            item = apply(item, kind, target)
        return reveal(item, "flop", (8, 12, 16))
    open_path = entered((("R", 3), ("R", 11), ("R", 28), ("C", 28)))
    limp_path = entered((("C", 1), ("R", 4), ("R", 12), ("R", 28), ("C", 28)))
    require(open_path.betting == limp_path.betting, "Equal mechanical-state recall fixture")
    require(open_path.board == limp_path.board and open_path.holes == limp_path.holes,
            "Same card observations in recall fixture")
    require(K.infoset_key(open_path) != K.infoset_key(limp_path),
            "Distinct earlier own/public actions are never merged")
    check_observation(open_path)
    check_observation(limp_path)


def forced_runout_and_payoffs():
    root = holes_game()
    folded = apply(root, "F")
    require(K.payoff(folded) == (F(-1, 2), F(1, 2)), "Initial blind fold payoff")
    after_open = apply(root, "R", 3)
    require(K.payoff(apply(after_open, "F")) == (F(1), F(-1)), "Uncalled raise refund")

    game = root
    for kind, target in (("R", 2), ("R", 8), ("R", 22), ("R", 100)):
        game = apply(game, kind, target)
    require(K.node_kind(game) == "player", "Uncalled all-in retains response")
    require(tuple((a.kind, a.target) for a in K.player_actions(game)) == (("F", None), ("C", F(100))),
            "All-in has fold/call only")
    require(K.payoff(apply(game, "F")) == (F(-22), F(22)), "Fold after jam loses actual contribution")
    game = apply(game, "C", 100)
    require(game.betting.mode == "runout" and game.betting.C == 100,
            "Called preflop all-in enters chance-only runout")
    full_runout = (8, 12, 16, 20, 24)
    require(K.runout_probability(game, full_runout) == F(1, comb(48, 3) * 45 * 44),
            "Exact complete preflop all-in runout mass")
    for invalid in ((12, 8, 16, 20, 24), (8, 12, 16, 20, 20),
                    (0, 12, 16, 20, 24), (8, 12, 16, 20), (8, 12, 16, 20, 52)):
        require(K.runout_probability(game, invalid) == 0, "Invalid runout has zero mass")
    for stage, batch, rest, probability in (
        ("flop", (8, 12, 16), (20, 24), F(1, 45 * 44)),
        ("turn", (20,), (24,), F(1, 44)),
        ("river", (24,), (), F(1)),
    ):
        require(K.node_kind(game) == "chance" and tuple(K.player_actions(game)) == (),
                "Runout never resumes player decisions")
        rejected(K.play, game, K.Action("X"))
        check_chance_outcomes(game, stage, len(batch))
        game = reveal(game, stage, batch)
        require(K.runout_probability(game, rest) == probability, "Remaining all-in runout probability")
    require(K.node_kind(game) == "terminal" and game.betting.mode == "showdown",
            "All-in runout finishes at showdown")
    require(K.payoff(game) == (F(0), F(0)), "All-in board tie")

    # Test actual win/loss and ties through complete legal card paths at 100BB.
    scenarios = (
        ((48, 49), (44, 45), (0, 5, 10, 24, 32), (F(100), F(-100))),
        ((44, 45), (48, 49), (0, 5, 10, 24, 32), (F(-100), F(100))),
    )
    for sb, bb, board, expected in scenarios:
        item = holes_game(sb, bb)
        for kind, target in (("R", 2), ("R", 8), ("R", 22), ("R", 100), ("C", 100)):
            item = apply(item, kind, target)
        item = reveal(item, "flop", board[:3])
        item = reveal(item, "turn", board[3:4])
        item = reveal(item, "river", board[4:])
        require(K.payoff(item) == expected, "Actual-card all-in win/loss payoff")


def run():
    hand_fixtures()
    print("PASS: independent hand-rule fixtures, invalid-card rejection, suit symmetry and card-order invariance.", flush=True)
    exhaustive_five_cards()
    print("PASS: every physical five-card hand matches the independent direct hand ranker.", flush=True)
    exhaustive_semantic_classes()
    print("PASS: every feasible five/six/seven-card rank-multiplicity and flush-rank semantic class matches independent direct and best-five ranking.", flush=True)
    exhaustive_private_chance()
    print("PASS: complete root private-deal support, uniqueness, exact Fraction mass and normalization.", flush=True)
    chance_and_history_paths()
    print("PASS: complete conditional board supports on exercised residual decks, invalid outcomes, exact information keys, public-history separation and perfect-recall construction.", flush=True)
    forced_runout_and_payoffs()
    print("PASS: chance-only all-in runouts, exact suffix probabilities, card-evaluated wins/losses/ties and contribution-based settlement.", flush=True)


if __name__ == "__main__":
    run()
