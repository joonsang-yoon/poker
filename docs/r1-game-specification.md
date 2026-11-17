# R1: complete 100 BB HUNL extensive-form game

[Documentation index](README.md) · [Project quickstart](../README.md#quickstart)

This document governs R1 and was originally supplied as `EFG.md`.
Its rules and section numbers are preserved. [Section 10](#10-runnable-artifacts)
describes this checkout's runnable artifacts; [source provenance](provenance.md)
explains the original filenames, historical hashes, and reported runs.

## Contents

1. [Normative contract](#1-normative-contract)
2. [Extensive-form definition and exact chance](#2-extensive-form-definition-and-exact-chance)
3. [Public mechanics and accounting](#3-public-mechanics-and-accounting)
4. [Exact sizing and postflop menus](#4-exact-sizing-and-postflop-menus)
5. [Full preflop tree](#5-full-preflop-tree)
6. [Complete recursive postflop grammar](#6-complete-recursive-postflop-grammar)
7. [Exact information sets and perfect recall](#7-exact-information-sets-and-perfect-recall)
8. [Showdown ranking and exact terminal payoffs](#8-showdown-ranking-and-exact-terminal-payoffs)
9. [Exhaustive validation contract and scope](#9-exhaustive-validation-contract-and-scope)
10. [Runnable artifacts](#10-runnable-artifacts)

## 1. Normative contract

R1 is a newly designed action abstraction. This document is its complete generative EFG specification; it does not list every card-expanded history individually. The preflop adjacency table and recursive postflop grammar below generate every permitted betting history. Exact chance expands each such history into its compatible private deals and public boards.

R1 fixes the conflicting source alternatives as follows: positive half-up rounding is authoritative; the preflop table in Section 5 is authoritative; postflop menus are those in Section 4; and no discretionary live raise cap applies. The formal cap parameters are redundant bounds. These choices preserve the shared accounting, integer target lattice, minimum-raise rules, mandatory all-in snaps, action order, and all-in closure. R1 is a qualitative design choice, with no claim of mathematical optimality or solved strategic superiority.

All amounts are in big blinds. Both players begin with 100, **including their posted blinds**. There is no ante, rake, fee, side pot, multiple board, or suit-based tie break. SB is the button and acts in position after the flop. SB posts \(1/2\); BB posts \(1\). Voluntary bet and raise targets are whole BB, while all accounting and probabilities use exact rational arithmetic.

Ordinary board dealing, best-five-card showdown, and full minimum raises are consistent with the [PokerStars Texas Hold’em rules](https://www.pokerstars.com/poker/games/texas-holdem/); the heads-up blind and action order is consistent with the [PokerStars poker-rules guide](https://www.pokerstars.com/help/articles/poker-rules-master/229151/). R1’s integer target lattice, mandatory snaps, and selected action menus are the explicit abstraction rules in this document.

The accompanying self-contained Python kernel, independent validator, and actual-run logs implement and check this contract. The validation scope is specified in Section 9; this specification makes no claim about results that have not been executed.

## 2. Extensive-form definition and exact chance

Define

\[
\Gamma_{R1}=(N,H,Z,\rho,\mathcal A,f_c,\mathcal I,u),\qquad
N=\{\mathrm{SB},\mathrm{BB}\}.
\]

Chance is a separate actor \(c\). The root history is \(\epsilon\), with the deterministic blind postings fixed as initial conditions. The public transcript starts with the blind-posting record. The root action belongs to chance and assigns the private hands. No player decision precedes that private deal.

### 2.1 Cards and representations

The deck is

\[
D=\{0,1,\ldots,51\},\qquad
x=4(r-2)+s,
\]

where rank \(r\in\{2,\ldots,14\}\), ace has rank 14, and suit \(s\in\{0,1,2,3\}\). Suit identifiers distinguish cards but never break a showdown tie.

A private hand is an unordered pair represented in increasing card order. The flop is an unordered triple represented in increasing card order. Turn and river retain their distinct street identities. Thus the public board is represented as

\[
B=(F_1,F_2,F_3,t,r)
\]

truncated to zero, three, four, or five cards at ordinary player decisions, with \(F_1<F_2<F_3\). The full board is **not** globally sorted. Sorting the flop is canonical serialization and does not add a chance event.

### 2.2 Private dealing

For disjoint two-card hands \(h_{\mathrm{SB}},h_{\mathrm{BB}}\), root chance chooses their assignment to the labeled seats with probability

\[
f_c(h_{\mathrm{SB}},h_{\mathrm{BB}})
=\frac{1}{\binom{52}{2}\binom{50}{2}}.
\]

Each player observes only their own pair. Overlapping, out-of-deck, wrong-length, or noncanonical events are not legal chance actions and receive probability zero. Root normalization is exact:

\[
\sum_{h_{\mathrm{SB}}\in\binom D2}
\sum_{h_{\mathrm{BB}}\in\binom{D\setminus h_{\mathrm{SB}}}2}
\frac{1}{\binom{52}{2}\binom{50}{2}}=1.
\]

The initial player decision follows with the blind state in Section 3.

### 2.3 Board dealing

At every board chance node, let

\[
U=D\setminus(h_{\mathrm{SB}}\cup h_{\mathrm{BB}}\cup B).
\]

The next flop is a uniformly chosen unordered triple from \(U\); the next turn or river is a uniformly chosen singleton. Every legal event has probability

\[
\Pr(S\mid h)=\binom{|U|}{k}^{-1},
\qquad k=3\text{ for flop},\quad k=1\text{ for turn or river}.
\]

Consequently the successive conditional probabilities for a standard complete board are

\[
\frac{1}{\binom{48}{3}},\qquad\frac1{45},\qquad\frac1{44}.
\]

These probabilities condition on the **full underlying history**, including both private hands. The players' information sets conceal the opponent's hand; this concealment does not change which cards the dealer must remove. Strategic posterior beliefs are obtained by summing compatible histories, not by replacing the dealer's remaining deck with a player's visible-card set.

For each legal remaining deck and required block size,

\[
\sum_{S\in\binom Uk}\binom{|U|}{k}^{-1}=1.
\]

No burn-card histories are represented. The specified chance law deals the public cards directly without replacement.

### 2.4 Called-all-in runouts

A called all-in before the river produces only the remaining board chance nodes, then showdown. Its remaining board distribution is exactly the product of the ordinary conditional kernels:

| Street on which all-in is called | Remaining labeled outcome | Conditional probability of that legal outcome |
| --- | --- | --- |
| Preflop | Unordered flop \(F\), turn \(t\), river \(r\) | \(1/[\binom{48}{3}\,45\,44]\) |
| Flop | Turn \(t\), river \(r\) | \(1/(45\,44)\) |
| Turn | River \(r\) | \(1/44\) |
| River | Empty remaining runout | \(1\), immediate showdown |

Sequential chance nodes are normative. A combined-runout iterator is equivalent if it preserves these labels and product probabilities. A set of all remaining cards without their street labels is a different representation and cannot be assigned these labeled-outcome probabilities without aggregation.

### 2.5 Histories, actors, actions, and terminals

\(H\) is the **smallest prefix-closed set** generated from \(\epsilon\) by the private deal, the preflop table, the postflop grammar, and the board chance rules. An underlying history records the private hand assignment, every public chance reveal with its street, and every finalized player action with its actor and street. It contains no strategy probabilities, card buckets, raw-size aliases, or off-tree actions.

At chance histories \(\rho(h)=c\); at player histories \(\rho(h)\) is the actor determined by the betting rules. The legal action set \(\mathcal A(h)\) is the appropriate exact chance support or deduplicated player menu. Terminals have no actor and no outgoing action.

\(Z\) consists precisely of:

- histories ending in a fold; and
- histories at a closed river or completed called-all-in runout, with a complete board, that proceed to showdown.

An uncalled all-in, its opponent's response node, and an incomplete runout are not terminal histories. A fold is terminal immediately and triggers no further dealing.

## 3. Public mechanics and accounting

At a player decision write

\[
\sigma=(s,p,P,C,(c_{\mathrm{SB}},c_{\mathrm{BB}}),i,\Delta),
\]

with streets \(s=0,1,2,3\) denoting preflop, flop, turn, river. Here \(p\) is the actor; \(C\) is each player's cumulative matched contribution on **all completed streets**; \(P=2C\) is the fixed street-start pot; \(c_q\) is player \(q\)'s current-street contribution; \(i\) is the aggression level; and \(\Delta\) is the last actual aggression increment used for the next minimum-size calculation.

Let

\[
a=c_p,\quad f=c_{1-p},\quad R=100-C,\quad Q=P+2f.
\]

The live pot is \(P+c_{\mathrm{SB}}+c_{\mathrm{BB}}\). An action to \(b\) pays \(b-a\), rather than \(b\) additional chips. The actor's uncommitted stack is \(R-a\); \(R\) itself is the maximum **street target**. The pot after a hypothetical call is \(Q\), not the unmatched live pot.

### 3.1 Initial state and contextual metadata

After the root private deal,

\[
\sigma_0=(0,\mathrm{SB},0,0,(1/2,1),1,1).
\]

The posted BB is aggression level 1. The initial minimum increment is 1, not the difference \(1-1/2\).

The preflop route records the root limp, if any, and the resolved raises taken so far. It distinguishes the finite lookup contexts in Section 5. It resets when preflop closes, while the complete public transcript remains intact.

A public flag \(L\) records whether preflop ended by SB limp followed by BB check. It is true only for that origin. The flop opening exception uses \(L\); all other menus ignore it. At a flop player state this condition is equivalently \(C=1\). The flag can be carried forward without affecting later menus.

Normal postflop entry is

\[
\sigma_s(C)=(s,\mathrm{BB},2C,C,(0,0),0,0),\quad s>0.
\]

This state becomes active only after the corresponding board block is dealt. A descriptor for a pending deal must not expose its future player actions before chance completes.

### 3.2 Passive actions

| Context | Passive action and result |
| --- | --- |
| Initial SB facing BB blind | Fold; or call to 1, leaving BB its option |
| BB option after the initial limp | Check, closing preflop at matched target 1 |
| BB at an unbet postflop street | Check, passing action to SB without closing |
| SB after the opening BB check | Check, closing the street at matched target 0 |
| Player facing \(f>a\), except root limp handling | Fold; or call to \(f\), closing the street |

There is no fold or call when a check is available. There is no extra decision for the prior aggressor after an ordinary call. Checks and calls add no aggression level and create no new wager size.

### 3.3 Aggression and caps

Before generating aggressive candidates require

\[
f<R,\qquad i<K_s,
\]

where

\[
K_0=100,\qquad K_s=R\quad(s>0).
\]

These bounds are not discretionary live restrictions. Starting from the blind or unopened state, each aggressive target is an integer and strictly increases the previous target by at least one. Therefore \(i\le f\) at every facing state. If the opponent is not all-in, \(f<R\), hence postflop \(i<R=K_s\), and preflop \(i<100=K_0\). A no-bet postflop state has \(i=0<R\). The caps cannot suppress a reachable raise that passes the stack guard.

After a finalized bet or raise to \(b\), update

\[
c_p'=b,\qquad c_{1-p}'=c_{1-p},\qquad
p'=1-p,\qquad i'=i+1,\qquad\Delta'=b-f.
\]

Keep \(C,P,s\) unchanged. Record the **actual finalized increment**, including a short all-in increment. In this equal-stack heads-up game a short all-in leaves no opponent able to raise against the all-in player; no additional reopening flag is needed.

### 3.4 Street closure and ledgers

If a street closes at matched current-street target \(x\), define

\[
C'=C+x.
\]

For calls \(x=f\); for postflop check-through \(x=0\); for the BB option check \(x=1\). The root SB call is the sole exception and does not close preflop.

- On river closure: showdown at matched commitment \(C'\).
- Before river, if \(C'=100\): chance-only runout to showdown at 100.
- Otherwise: deal the next board block, then start the next street with BB to act, \(C=C'\), \(P=2C'\), zero current-street contributions, and \(i=\Delta=0\).

The aggressive-target ledger starts preflop with \(B_{0,0}=1/2\), \(B_{0,1}=1\), and postflop with \(B_{s,0}=0\). Each aggressive action appends its final target; passive actions do not append a target. The final matched target of every completed street contributes to \(C\) exactly once. On a fold, the largest target is not the folder's contribution and must not be substituted for it.

For each betting street skipped after a called all-in, record \(k_s=0\) and \(B_{s,0}=0\). These are ledger zeros, not artificial check/check histories. The final matched contribution remains 100.

At every reachable decision,

\[
0\le C+c_q\le100,\qquad
P+c_{\mathrm{SB}}+c_{\mathrm{BB}}
=(C+c_{\mathrm{SB}})+(C+c_{\mathrm{BB}}).
\]

When facing a wager, the call-price ratio is

\[
\mathrm{PO}=\frac{f-a}{P+2f}.
\]

At the initial SB decision this equals \((1-1/2)/2=1/4\). It is an accounting ratio, not an equilibrium calling rule.

## 4. Exact sizing and postflop menus

### 4.1 Ordered resolver

For a nonnegative rational raw target \(x=n/d\), use exact positive half-up rounding

\[
\operatorname{hu}(x)=\left\lfloor x+\frac12\right\rfloor
=\left\lfloor\frac{2n+d}{2d}\right\rfloor.
\]

Do not use binary floating point or ties-to-even rounding.

After the eligibility guard, resolve every raw aggressive target independently:

\[
b_0=\operatorname{hu}(x),\qquad
m=\begin{cases}
1,&\text{unbet postflop opening},\\
f+\Delta,&\text{any raise, including BB's preflop option},
\end{cases}
\qquad b_1=\max(b_0,m).
\]

Let

\[
T(s,C,b_1)=
(C+b_1\ge100)
\lor(s=0\land b_1>40)
\lor(s\in\{1,2\}\land 3(C+b_1)>200).
\]

Then

\[
\operatorname{res}_{\sigma}(x)=
\begin{cases}
100-C,&T(s,C,b_1),\\
b_1,&\neg T(s,C,b_1).
\end{cases}
\]

Only after this pipeline are final targets deduplicated and sorted. The action identity is its kind and final target; raw aliases create no separate histories or strategy probability mass.

Every final aggressive target must exceed \(f\). If it is below \(R\), it must satisfy the ordinary minimum. If it equals \(R\), it is all-in and may be smaller than the full minimum. In particular, a minimum-clamped amount above \(R\) must be snapped back to \(R\), rather than prematurely rejected.

The preflop and flop/turn comparisons are strict. A hypothetical clamped preflop target 40 remains ordinary; 41 snaps. On flop or turn with \(C=30\), clamped target 36 remains ordinary and 37 snaps to 70. These illustrate the resolver and do not add candidates absent from the policy. River applies only the stack cap.

### 4.2 Raw postflop targets

The opening menu applies identically to BB's immediate lead and SB's bet after BB checks.

| Street/context | Raw opening targets |
| --- | --- |
| Flop after limp/check, \(L=\mathrm{true}\) | \(\{P/2,P\}\) |
| Every other flop origin | \(\{P/3,2P/3\}\) |
| Turn, every origin | \(\{P/2,P\}\) |
| River, every origin | \(\{P/2,P,3P/2,R\}\) |

At **every** eligible postflop responding raise or re-raise, use

\[
\mathcal X_{\mathrm{raise}}(s,C,f,\Delta)
=\{f+\Delta,\;f+Q/2,\;f+Q\}
\cup
\begin{cases}
\{R\},&s=3,\\
\varnothing,&s\in\{1,2\}.
\end{cases}
\]

Here \(Q=P+2f\). Thus the ordinary fractional raises are targets

\[
f+Q/2=C+2f,\qquad f+Q=2C+3f.
\]

The minimum full raise is a real candidate, not merely a clamp on larger candidates. Direct raises, check-raises, and subsequent re-raises use the same rule for either player. No initiative, seat-specific sizing restriction, hand-strength classifier, private card, or board-texture category changes the menu.

Each raw set passes through the entire resolver. Explicit river all-ins receive no exception to its guards or ordering. Earlier-street all-ins arise from the specified candidates and mandatory snaps; there is no additional earlier-street jam candidate.

### 4.3 Resolved target sets

Let \(\mathcal O_s(C,L)\) be the sorted set of resolved opening targets from the preceding opening table. Let

\[
\mathcal R_s(C,f,i,\Delta)
=\begin{cases}
\operatorname{sort}\!\left\{\operatorname{res}_{\sigma}(x):
x\in\mathcal X_{\mathrm{raise}}(s,C,f,\Delta)\right\},
&f<R\ \text{and}\ i<K_s,\\
\varnothing,&\text{otherwise}.
\end{cases}
\]

These sets, rather than the raw fractions, are the actual abstract actions. Their elements remain dependent on the exact current monetary state. No target is retained under two labels after rounding, minimum enforcement, or snapping merges it with another.

## 5. Full preflop tree

### 5.1 Notation and chance exits

The following adjacency table is complete after the private deal. All rows have \(C=P=0\). Contributions are ordered \((\mathrm{SB},\mathrm{BB})\). The public prefix shown is the entire preflop action prefix, omitting only the fixed blinds and private deal. Actors are determined by the corresponding rows.

- \(L\): root SB call to 1.
- \(X\): check.
- \(C_b\): call to the final street target \(b\).
- \(R_b\): raise to the final street target \(b\).
- \(F_v\): fold terminal with utilities \((u_{\mathrm{SB}},u_{\mathrm{BB}})=(v,-v)\).
- \(E_{\alpha}(C)\): deal the flop with its exact chance kernel, then start the flop at \(\sigma_1(C)\), retaining the complete prefix \(\alpha\).
- \(U_{\alpha}\): called-preflop-all-in chance runout, retaining prefix \(\alpha\), with no subsequent betting and showdown at matched commitment 100.

Every occurrence of an exit denotes a separate history under its displayed prefix and private deal. The shared notation is a generation template, not an information-set or history merger.

### 5.2 Complete adjacency table

| Node | Complete public prefix | Actor | Contributions | \(i\) | \(\Delta\) | Fold | Call or check | All raise successors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Empty | SB | \((1/2,1)\) | 1 | 1 | \(F_{-1/2}\) | \(L\to L0\) | \(R_2\to O2;\ R_3\to O3\) |
| L0 | \(L\) | BB | \((1,1)\) | 1 | 1 | — | \(X\to E_{LX}(1)\) | \(R_4\to L4\) |
| L4 | \(L,R_4\) | SB | \((1,4)\) | 2 | 3 | \(F_{-1}\) | \(C_4\to E_{L4C}(4)\) | \(R_{12}\to L12\) |
| L12 | \(L,R_4,R_{12}\) | BB | \((12,4)\) | 3 | 8 | \(F_{+4}\) | \(C_{12}\to E_{L12C}(12)\) | \(R_{28}\to L28\) |
| L28 | \(L,R_4,R_{12},R_{28}\) | SB | \((12,28)\) | 4 | 16 | \(F_{-12}\) | \(C_{28}\to E_{L28C}(28)\) | \(R_{100}\to LJ\), raw 60 |
| LJ | \(L,R_4,R_{12},R_{28},R_{100}\) | BB | \((100,28)\) | 5 | 72 | \(F_{+28}\) | \(C_{100}\to U_{LJ}\) | — |
| O2 | \(R_2\) | BB | \((2,1)\) | 2 | 1 | \(F_{+1}\) | \(C_2\to E_{2C}(2)\) | \(R_8\to O8\) |
| O8 | \(R_2,R_8\) | SB | \((2,8)\) | 3 | 6 | \(F_{-2}\) | \(C_8\to E_{8C}(8)\) | \(R_{22}\to O22\) |
| O22 | \(R_2,R_8,R_{22}\) | BB | \((22,8)\) | 4 | 14 | \(F_{+8}\) | \(C_{22}\to E_{22C}(22)\) | \(R_{36}\to O36;\ R_{100}\to O2J\), respective raws 36, 50 |
| O36 | \(R_2,R_8,R_{22},R_{36}\) | SB | \((22,36)\) | 5 | 14 | \(F_{-22}\) | \(C_{36}\to E_{36C}(36)\) | \(R_{100}\to O36J\), raw 50 |
| O2J | \(R_2,R_8,R_{22},R_{100}\) | SB | \((22,100)\) | 5 | 78 | \(F_{-22}\) | \(C_{100}\to U_{O2J}\) | — |
| O36J | \(R_2,R_8,R_{22},R_{36},R_{100}\) | BB | \((100,36)\) | 6 | 64 | \(F_{+36}\) | \(C_{100}\to U_{O36J}\) | — |
| O3 | \(R_3\) | BB | \((3,1)\) | 2 | 2 | \(F_{+1}\) | \(C_3\to E_{3C}(3)\) | \(R_{11}\to O11\) |
| O11 | \(R_3,R_{11}\) | SB | \((3,11)\) | 3 | 8 | \(F_{-3}\) | \(C_{11}\to E_{11C}(11)\) | \(R_{28}\to O28\) |
| O28 | \(R_3,R_{11},R_{28}\) | BB | \((28,11)\) | 4 | 17 | \(F_{+11}\) | \(C_{28}\to E_{O28C}(28)\) | \(R_{100}\to O3J\), raw 60 |
| O3J | \(R_3,R_{11},R_{28},R_{100}\) | SB | \((28,100)\) | 5 | 72 | \(F_{-28}\) | \(C_{100}\to U_{O3J}\) | — |

An em dash means that the action is absent. All non-jam raise targets in the table equal their raw targets. Raw 50 and 60 targets snap to 100 after rounding and minimum enforcement. In particular, \(R_{36}\) after \(R_{22}\) is a full raise with increment 14; its following raw 50 meets the full minimum 50 and then snaps.

Every fold value uses the folding player's existing contribution, not the faced target. Every call except the initial limp closes preflop. A jam is followed by its explicit response row; only its call enters the corresponding runout.

### 5.3 Ordinary flop entries

Every entry has BB to act after the flop deal, \((c_{\mathrm{SB}},c_{\mathrm{BB}})=(0,0)\), \(i=\Delta=0\), and \(P=2C\). These are the exact resolved opening menus for either the immediate BB action or SB after a BB check; check is also available.

| Exit | Exact completed preflop history | \(C\) | \(P\) | \(R\) | Limp/check flag | Resolved flop opening targets |
| --- | --- | --- | --- | --- | --- | --- |
| \(E_{LX}(1)\) | \(L,X\) | 1 | 2 | 99 | True | \(\{1,2\}\) |
| \(E_{L4C}(4)\) | \(L,R_4,C_4\) | 4 | 8 | 96 | False | \(\{3,5\}\) |
| \(E_{L12C}(12)\) | \(L,R_4,R_{12},C_{12}\) | 12 | 24 | 88 | False | \(\{8,16\}\) |
| \(E_{L28C}(28)\) | \(L,R_4,R_{12},R_{28},C_{28}\) | 28 | 56 | 72 | False | \(\{19,37\}\) |
| \(E_{2C}(2)\) | \(R_2,C_2\) | 2 | 4 | 98 | False | \(\{1,3\}\) |
| \(E_{8C}(8)\) | \(R_2,R_8,C_8\) | 8 | 16 | 92 | False | \(\{5,11\}\) |
| \(E_{22C}(22)\) | \(R_2,R_8,R_{22},C_{22}\) | 22 | 44 | 78 | False | \(\{15,29\}\) |
| \(E_{36C}(36)\) | \(R_2,R_8,R_{22},R_{36},C_{36}\) | 36 | 72 | 64 | False | \(\{24,64\}\) |
| \(E_{3C}(3)\) | \(R_3,C_3\) | 3 | 6 | 97 | False | \(\{2,4\}\) |
| \(E_{11C}(11)\) | \(R_3,R_{11},C_{11}\) | 11 | 22 | 89 | False | \(\{7,15\}\) |
| \(E_{O28C}(28)\) | \(R_3,R_{11},R_{28},C_{28}\) | 28 | 56 | 72 | False | \(\{19,37\}\) |

The two histories ending at matched 28 remain distinct. They share a monetary continuation template but have different preflop transcripts, hence different information sets even when the player's private hand and public board agree.

## 6. Complete recursive postflop grammar

The grammar is parametrized by the actual dealt hands, revealed board, and complete public transcript \(h\). Every transition appends its exact actor, street, action kind and final target, or its public chance reveal. The parameters below abbreviate mechanics only; they never replace \(h\).

Let:

- \(U_s(C,L,h)\) be an unopened street with BB to act.
- \(V_s(C,L,h)\) be that street after BB checks, with SB to act.
- \(W_s(C,L,p,a,f,i,\Delta,h)\) be a facing-wager decision for player \(p\), whose current contribution is \(a<f\) and whose opponent has contributed \(f\).
- \(\operatorname{Close}_s(C,L,x,h)\) be the forced closure operation after matching current-street target \(x\).
- \(\operatorname{SD}(C,h)\) be showdown at matched total \(C\), requiring the complete board.

### 6.1 Unopened street

For \(s\in\{1,2,3\}\),

\[
U_s(C,L,h)\;\longrightarrow\;
\begin{cases}
X:\ V_s(C,L,h\cdot(s,\mathrm{BB},X)),\\
B_b:\ W_s(C,L,\mathrm{SB},0,b,1,b,
 h\cdot(s,\mathrm{BB},B_b)),
&b\in\mathcal O_s(C,L).
\end{cases}
\]

After BB checks,

\[
V_s(C,L,h)\;\longrightarrow\;
\begin{cases}
X:\ \operatorname{Close}_s(C,L,0,h\cdot(s,\mathrm{SB},X)),\\
B_b:\ W_s(C,L,\mathrm{BB},0,b,1,b,
 h\cdot(s,\mathrm{SB},B_b)),
&b\in\mathcal O_s(C,L).
\end{cases}
\]

No fold, call, third consecutive check, or different opening menu is added to either production.

### 6.2 Facing a wager

For every reachable facing state,

\[
W_s(C,L,p,a,f,i,\Delta,h)\;\longrightarrow\;
\begin{cases}
F:\ \operatorname{Fold}(p,C+a,h\cdot(s,p,F)),\\
C_f:\ \operatorname{Close}_s(C,L,f,h\cdot(s,p,C_f)),\\
R_b:\ W_s(C,L,1-p,f,b,i+1,b-f,
 h\cdot(s,p,R_b)),
&b\in\mathcal R_s(C,f,i,\Delta).
\end{cases}
\]

The raise production applies recursively after every permitted raise, including a check-raise. It has no extra endpoint imposed by a live aggression cap. When \(f=R\), \(\mathcal R_s\) is empty and the response is precisely fold/call.

The fold outcome gives player \(p\) utility \(-(C+a)\) and the opponent \(C+a\). Calling matches \(f\); it does not retain a player node with equal contributions on the same street.

### 6.3 Closure and next street

Put \(C'=C+x\). Then

\[
\operatorname{Close}_s(C,L,x,h)=
\begin{cases}
\operatorname{SD}(C',h),&s=3,\\
\operatorname{Run}_{s+1}(100,h),&s<3\ \land\ C'=100,\\
\operatorname{Deal}_{s+1}(C',L,h),&s<3\ \land\ C'<100.
\end{cases}
\]

At \(\operatorname{Deal}_{s+1}\), chance chooses the legal next block under Section 2, appends its street-labeled public reveal, and enters \(U_{s+1}(C',L,h')\). The ordinary preflop exits in Section 5 similarly use \(\operatorname{Deal}_1\), with the flop block size three.

At \(\operatorname{Run}_j(100,h)\), chance chooses the next block under the same kernel. If \(j<3\), proceed to \(\operatorname{Run}_{j+1}(100,h')\); if \(j=3\), proceed to \(\operatorname{SD}(100,h')\). No \(U,V,W\) production is instantiated inside a runout.

This recursion expands every ordinary postflop entry and every all-in continuation. It covers check-throughs, leads, checked-to bets, calls, folds, direct raises, check-raises, re-raises, short all-ins, and all remaining chance outcomes without relying on representative paths.

### 6.4 Finiteness

Within a street, every aggressive target is an integer strictly above the previous target and no greater than \(R\). Thus aggression cannot continue indefinitely. Passive sequences close the street, end the hand, or make the single permitted initial transition from limp to BB option. Ordinary street closure moves strictly forward, and the game has only the specified streets. Each chance node has finite support. Therefore every generated history is finite and \(\Gamma_{R1}\) is a finite EFG.

## 7. Exact information sets and perfect recall

Let \(\operatorname{pub}(h)\) contain the initial blind record, every publicly revealed board block with its street, and every public action with its street, actor, kind, and finalized target. It excludes both private hand assignments and all unobserved chance data.

At a decision for player \(p\), define

\[
I_p(h)=
\bigl(p,\operatorname{sort}(h_p),B(h),\operatorname{pub}(h)\bigr).
\]

Two player-decision histories belong to the same information set **if and only if** these keys agree. The opponent's private hand may vary over compatible disjoint possibilities. Future board events are not observed or inserted into the key. The board preserves the unordered flop followed by the individually labeled turn and river; no card abstraction or suit canonicalization merges physical observations.

The complete public transcript reconstructs the current street, actor, contributions, prior matched commitment, aggression sequence, preflop route when relevant, and limp/check origin. Therefore all histories in one information set have the same legal action menu. The policy's card independence is sufficient for this consistency and does not imply that strategy is card-independent.

**Perfect-recall proof.** A player retains its own private pair throughout the hand. Every later public transcript contains every earlier public observation and the player's own earlier actions as an ordered prefix. Equality of the above keys at two later decision histories therefore implies equality of the sequences of earlier information observations and of the player's own actions. Canonicalizing the unordered private pair and unordered flop loses no information because their internal ordering is not an observation in this game. Hence the information partition satisfies perfect recall.

The monetary state, a pot label, a current board alone, or an opening-route label is never an information-set identifier. In particular, \(E_{L28C}(28)\) and \(E_{O28C}(28)\), or a lead-call and a check-bet-call reaching equal amounts, remain distinct histories and information sets.

## 8. Showdown ranking and exact terminal payoffs

### 8.1 Five-card ordering

For five distinct cards, compute a lexicographically comparable rank tuple. The first component is the category below; subsequent components are the indicated ranks in descending significance, padded with zeros to a common length. Larger tuples win.

| Category | Value | Tie-breaking components |
| --- | --- | --- |
| High card | 0 | All five ranks, descending |
| One pair | 1 | Pair rank; three distinct kickers, descending |
| Two pair | 2 | Higher pair rank; lower pair rank; kicker |
| Three of a kind | 3 | Trip rank; two kickers, descending |
| Straight | 4 | Highest rank of the straight |
| Flush | 5 | All five ranks, descending |
| Full house | 6 | Trip rank; pair rank |
| Four of a kind | 7 | Quad rank; kicker |
| Straight flush | 8 | Highest rank of the straight |

Ace is high except in \(A,2,3,4,5\), whose straight high card is 5. No other wraparound straight is valid. A royal flush is the ace-high straight flush within category 8. Suits have no ranking precedence.

For a player's two hole cards and the five-card board, define

\[
\operatorname{rank}_7(h_p,B)
=\max_{S\subseteq h_p\cup B,\ |S|=5}\operatorname{rank}_5(S).
\]

Using zero, one, or both hole cards is permitted. A shared best board hand can tie. The kernel also evaluates five- and six-card inputs by the same best-five definition; terminal hold'em comparisons use seven cards.

### 8.2 Fold terminals

If player \(p\) folds from current contribution \(c_p\), let

\[
L=C+c_p.
\]

Then

\[
u_p=-L,\qquad u_{1-p}=L.
\]

The survivor's unmatched wager is returned economically. It is not additional profit. An SB open-fold therefore pays \((-1/2,+1/2)\), and a BB fold to either root opening raise pays \((+1,-1)\).

### 8.3 Showdown terminals

Let \(C_*\) be the final matched contribution per player, after adding the last closed street exactly once. Define

\[
w_{\mathrm{SB}}=
\begin{cases}
1,&\operatorname{rank}_7(h_{\mathrm{SB}},B)>
\operatorname{rank}_7(h_{\mathrm{BB}},B),\\
1/2,&\operatorname{rank}_7(h_{\mathrm{SB}},B)=
\operatorname{rank}_7(h_{\mathrm{BB}},B),\\
0,&\operatorname{rank}_7(h_{\mathrm{SB}},B)<
\operatorname{rank}_7(h_{\mathrm{BB}},B).
\end{cases}
\]

Utilities are net changes from the stacks before posting blinds:

\[
u_{\mathrm{SB}}=(2w_{\mathrm{SB}}-1)C_*,\qquad
u_{\mathrm{BB}}=-u_{\mathrm{SB}}.
\]

A split gives exactly zero net utility to each player. Called-all-in showdowns use \(C_*=100\), regardless of which betting streets were skipped. Utilities are rational, zero-sum, and bounded by the initial stack. Final stacks \(100+u_p\) sum to 200 at every terminal.

## 9. Exhaustive validation contract and scope

The independent validator must construct its own initial state, policy lookup, raw menus, rounding, minima, snap predicates, deduplication, transition function, chance scheduler, and exploration frontier. It may call the kernel only for **actual** outputs being checked. Expected values and frontier successors must not be obtained from the kernel's rule or transition helpers.

For each reachable public mechanics state in that independently generated closure, the comparison must check both directions of menu equality, every legal successor, accounting, actor and street progression, aggressive levels and increments, all-in responses, closures, and terminal utility obligations. A legal-action subset check is insufficient because it can miss omitted branches. States reused for continuation validation must retain all fields affecting future behavior, including preflop route and the public limp/check flag.

The validation quotient is not the EFG's information partition. A single mechanics continuation may represent many full transcripts, private deals, and boards solely for checking identical rules. History append operations, observations, and information-set separation require their own checks and the perfect-recall argument in Section 7.

The exhaustive finite factorization is:

1. Independently exhaust the reachable card-independent public mechanics closure and compare every outgoing rule and transition.
2. Verify the exact chance event supports, their conditional rational probabilities, no replacement, canonical representations, and sequential runout scheduling. The combinatorial identities in Section 2 establish normalization for every compatible remaining deck; reduced fixtures alone do not constitute enumeration of the physical-deal space.
3. Verify the complete hand-ranking and payoff functions independently, with the precise scope of executed evaluator checks stated in the log.
4. Lift the public-rule checks to every compatible exact-card history by induction: a private deal starts with the same checked mechanics; a checked player action has its independently checked successor; every legal public card reveal leaves the same mechanics continuation; utilities then follow from the actual cards and final matched contribution.

The supplied betting oracle uses its own integer half-BB representation, separately authored menus and resolver, and its own transitions. Its frontier starts from its own initial state and follows its own successors. It compares the kernel's entire menu and every successor, including terminal and pending-chance states. No depth limit, sample, or kernel-generated exploration frontier is used.

The card validator enumerates every root private deal and every physical five-card hand. It also enumerates every feasible rank-multiplicity and flush-rank semantic class for five, six and seven cards, comparing a separately written direct evaluator with the kernel and an independent best-five construction. The latter semantic-class checks do not claim literal enumeration of every physical six- or seven-card holding. In the supplied kernel, `evaluate` visibly returns the maximum of `_rank_five_unchecked` over `combinations(cards, 5)` after checking distinct valid cards; `rank_five` calls that same five-card function. Therefore correctness of every physical five-card evaluation, together with this exact best-five composition, establishes the seven-card showdown evaluator for every legal holding.

For conditional board chance, the validator compares the complete generated support against an independently built support on the residual decks exercised by its paths. Universality follows from the supplied implementation's construction: for any legal remaining deck, each next block is exactly an increasing index subset of that sorted deck. The order-preserving map from indices to actual remaining cards is a bijection. Its support is consequently every legal block exactly once, with mass `Fraction(1, comb(len(remaining), k))`. This construction has no branch on the identity of a particular unremoved card. The independently checked public scheduler supplies the block size and ensures the remaining-deck sizes in Section 2. Changing the private hands or earlier board changes the bijection, not this proof.

This is exhaustive validation of reachable betting transitions with exact-card factorization. It does not materialize the full product of private deals, boards and betting histories, and it is not an equilibrium certificate. The actual-run logs identify the checked file hashes, invoked validation command, and pass/fail outcomes. No results from an earlier source-package log substitute for a fresh run of these deliverables.

## 10. Runnable artifacts

The [reference kernel](../hunl_r1/kernel.py) is independently runnable with Python 3.10 or later and only the standard library. It contains the full betting engine, lazy exact chance support, card-aware immutable game histories, information-set keys, complete best-five evaluator, and terminal utilities. No embedding solver, external evaluator, data download, or dependency installation is required.

The validator consists of the [suite entry point](../validation/__main__.py), [betting oracle](../validation/betting.py), and [card oracle](../validation/cards.py). It resolves the specification and reference data relative to its source location. The entry point runs the entire suite; it has no shortened or sampled mode. Explicit exceptions keep every check enabled under optimized Python as well.

Follow the [quickstart](../README.md#quickstart) to run an exact-card check-through
hand and print every preflop public decision and exit as JSON. Use the
[validation guide](../README.md#validation) to record the full suite in a new,
Git-ignored log. Both give commands to run from the repository root.

The validation log records the actual command, Python version, timestamps,
source/specification hashes, individual pass/fail results, and overall result;
the process exits nonzero on failure. The [reference preflop tree](../data/preflop-tree.json)
is the kernel's complete preflop export, and the validator checks that it
contains the same JSON data as a fresh expansion. The
[historical reference run](../artifacts/validation/reference-run.log) retains
the original bundle's execution record.

For integration, use `from hunl_r1 import kernel`. Its functions `new_game`, `node_kind`, `chance_events`, `chance_probability`, `deal`, `player_actions`, `play`, `infoset_key`, and `payoff` provide the full EFG interface. `chance_events` is lazy, and each chance edge carries an exact `Fraction` probability. Strategies are optional consumers of these interfaces and are not inputs needed to define or execute a hand. A caller-supplied unoffered player action or illegal card event is rejected.
