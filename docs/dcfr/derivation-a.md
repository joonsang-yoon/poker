# Exact R1 vectorized tabular DCFR — derivation A

[DCFR index](README.md) · [Derivation request](derivation-request.md) · [R1 game specification](../r1-game-specification.md)

**Status:** One of [four peer solver designs](README.md#peer-derivations); none is preferred.

**Provenance:** Source-audit filenames, hashes, and reported runs are historical
records of the original bundle. See [source provenance](../provenance.md) for
current paths and the [validation guide](../../README.md#validation) for fresh
mechanics checks.

## Reading map

- [Contract and notation](#contract-scope-and-how-to-read-this-derivation)
- [River](#river) → [Turn](#turn) → [Flop](#flop) → [Preflop](#preflop)
- [Implementation and proof obligations](#implementation-and-proof-obligations-at-each-street-root)
- [Historical source notes and validation status](#source-binding-and-validation-status)

## Contract, scope, and how to read this derivation

**Required result.** For a specified street-entry public history $e$, compatible boundary distribution $\mu_e$, and returned behavioral profile $\bar\sigma$, prove

$$
\boxed{\operatorname{Expl}_e(\bar\sigma)\le 0.005P_e.}
$$

The proof must use two information-set-consistent best responses in the original R1 continuation game, with a certified numerical and continuation-error allowance. For an ordinary postflop entry, $P_e=2C_e$. At preflop, $P_e=1.5$ BB, so the threshold is **$0.0075$ BB**. The kernel's preflop field $P=2C=0$ is an accounting field, not this entry-pot denominator.

This document derives an algorithm and its certification conditions. It does **not** report a computed equilibrium, a completed full-game training run, or a measured exploitability. No particular postflop boundary ranges were supplied. Consequently, a postflop solver is specified as a function of its explicitly supplied ranges; a certificate is tied to those ranges and that complete public history. An entire continuum of boundary-range queries is not represented by one solved table.

**Authority.** The [R1 game specification](../r1-game-specification.md) governs every rule. The [reference kernel](../../hunl_r1/kernel.py) is its executable interface and the [preflop tree](../../data/preflop-tree.json) its complete preflop export. References [E2], [E4], etc. below mean the corresponding numbered section of that specification; [K] names a kernel function. External sources are used only to identify CFR/DCFR and the imperfect-information decomposition issue. All game-specific operators and error bounds are derived here.

**Dependency order.** Each street has one root claim, followed by its dependencies in strict top-down order:

| Root | First dependency | Recursive dependencies |
|---|---|---|
| River R0 | Certified exploitability | Boundary game → BR values → counterfactual recursion → reaches and exact terminals → cards, ranking, blockers; candidate profile → DCFR and averaging |
| Turn T0 | Certified exploitability including river continuation | Same BR/DCFR structure → ordinary river entries or forced runouts → river evaluation/BR kernels |
| Flop F0 | Certified exploitability including turn and river | Same structure → ordinary turn entries or forced runouts → turn and river kernels |
| Preflop P0 | Certified exploitability at $0.0075$ BB | Exact preflop automaton → flop continuations/runouts → all preceding kernels; numerical and local-to-global proof |

A named earlier kernel is a reference to its fully expanded derivation, not an unspecified solver. In particular, **Evaluate**, **BestResponse**, and **Solve** are different operations. Evaluating an already fixed profile is a backward reduction. Solving a continuation game requires repeated forward reaches, backward values, regret updates, and independent certification.

### Premises and notation

The premises are a finite two-player zero-sum EFG, perfect recall, exactly the physical-card information partition of [E7], and the fixed 100 BB stacks of [E1]. There is no rake, ante, fee, side pot, suit tie break, card bucket, board abstraction, action alias, or additional raise cap. Arithmetic for game generation, card validity, and terminal accounting is exact. Floating-point strategy calculations approximate computations in this fixed EFG; their error is explicitly bounded.

| Symbol | Definition and units |
|---|---|
| $i\in\{0,1\}$, $j=1-i$ | SB is 0, BB is 1 |
| $s=0,1,2,3$ | Preflop, flop, turn, river |
| $n,e,z$ | A public-history node, a fixed entry node, a terminal node |
| $h_x,h_y$ | Physical unordered two-card hands, stored in increasing card order; $x$ is always SB's index and $y$ BB's index in pair tensors |
| $B_n$, $b_n=|B_n|$ | Street-labeled board; sorted flop followed by distinct turn and river positions |
| $C,c_0,c_1$ | Per-player matched commitment on completed streets; current-street contributions, in BB |
| $P=2C$, $R=100-C$ | Fixed street-start pot; maximum current-street target |
| $a=c_p$, $f=c_{1-p}$ | Acting player's existing target and faced target |
| $\ell,\Delta$ | Aggression level and last actual finalized increment; $\ell$ avoids collision with player index $i$ |
| $A(n)$, $L[n,a]$ | Deduplicated legal action set and its padded mask |
| $\sigma_i(n,h,a)$ | Behavioral action probability at one full-history infoset |
| $b_i(h)$ | Fixed nonnegative boundary range factor; distinguished from board size $b_n$ by its subscript and argument |
| $\rho_i(n,h)$ | Product of player $i$'s action probabilities after entry and before $n$; no chance or opponent factors |
| $q_n(x,y)$ | Entry private-deal mass times all subsequent chance factors before $n$; no player action factors |
| $U_i(n,x,y)$ | Conditional future payoff given both hands and public node, excluding all past reach |
| $F_i(n,h)$ | Unnormalized counterfactual continuation value, in probability-mass times BB |
| $m_i(n,h)$ | Counterfactual mass corresponding to $F_i$ |
| $D^t,S^t$ | Discounted regret table and discounted average-strategy numerator after iteration $t$ |
| $v_i$, $B_i$, $g_i$ | Profile value, best-response value, and unilateral improvement, in BB |
| $\varepsilon_e=0.005P_e$ | Requested half-NashConv exploitability tolerance |

The notation $a$ in an action tensor is an action-slot index; in monetary formulas it denotes the actor's contribution. These uses are kept in separate formulas.

---

<a id="river"></a>

## River root R0 — certify $\operatorname{Expl}_e(\bar\sigma)\le0.005(2C_e)$

Compare this street: A · [B](derivation-b.md#river) · [C](derivation-c.md#river) · [D](derivation-d.md#river) · [Reading map](#reading-map)

An ordinary river entry has a five-card board, $C_e<100$, no current-street contributions, BB to act, and the entire earlier public transcript. Its subtree has no future board chance. A river reached during a called-all-in runout is a chance-only/showdown case, not an ordinary river solving problem.

### R1. The certificate requires two best-response values in a defined boundary game

For the normalized boundary game $G(e,\mu_e)$, define

$$
\begin{aligned}
v_i(\sigma)&=\mathbb E_{\mu_e,\sigma}[u_i],\\
B_i(\sigma_j)&=\max_{\tau_i\in\Sigma_i(e)}
                    \mathbb E_{\mu_e,(\tau_i,\sigma_j)}[u_i],\\
g_i(\sigma)&=B_i(\sigma_j)-v_i(\sigma)\ge0,\\
\operatorname{NC}_e(\sigma)&=g_0(\sigma)+g_1(\sigma)
                              =B_0(\sigma_1)+B_1(\sigma_0),\\
\operatorname{Expl}_e(\sigma)&=\tfrac12\operatorname{NC}_e(\sigma).
\end{aligned}
$$

Here $\Sigma_i(e)$ contains only strategies constant on the EFG's actual infosets. Since $v_0+v_1=0$, the profile values cancel from the certificate. A computed profile value is nevertheless useful as a diagnostic.

This fixes the factor-of-two convention: $\operatorname{Expl}\le\varepsilon$ implies $\operatorname{NC}\le2\varepsilon$ and each $g_i\le2\varepsilon$. It does not imply each unilateral improvement is at most $\varepsilon$. To implement this document's $\operatorname{Expl}\le0.005P_e$ using a NashConv evaluator, check $\operatorname{NC}\le0.01P_e$. If the requested convention instead means $\operatorname{NC}\le0.005P_e$, check $\operatorname{Expl}\le0.0025P_e$.

Suppose an independently evaluated BR pass returns rigorous upper bounds $B_i^+$. The stopping rule is

$$
\boxed{\frac{B_0^++B_1^+}{2}\le0.005P_e.}
\tag{R-cert}
$$

Numerical uncertainty belongs inside $B_i^+$; it is not an informal tolerance added after stopping. The river has no continuation-model error when all its betting histories and exact terminal payoffs are retained.

#### R1.1. The boundary game requires compatible ranges and preserved information

Let $H=\binom{52}{2}=1326$ and enumerate its physical hands lexicographically. For every board define

$$
\begin{aligned}
v_B(x)&=\mathbf1[h_x\cap B=\varnothing],\\
M_B(x,y)&=v_B(x)v_B(y)\mathbf1[h_x\cap h_y=\varnothing].
\end{aligned}
$$

A boundary game is a synthetic initial chance draw of the pair $(h_x,h_y)$ from $\mu_e$, followed by the **unchanged** continuation rooted at the full public prefix $e$. Each player sees its own hand, not the pair. This is an induced Bayesian continuation game; the public entry does not reveal the underlying private state.

For boundary factors $b_0,b_1\ge0$, the compatible joint law is

$$
W_e(x,y)=M_{B_e}(x,y)b_0(x)b_1(y),\qquad
Z_e=\sum_{x,y}W_e(x,y)>0,\qquad
\mu_e(x,y)=W_e(x,y)/Z_e.
\tag{boundary}
$$

Each factor is finite and zero for hands intersecting the board. Scaling either entire factor by a positive constant leaves $\mu_e$ unchanged. Normalizing each factor to sum to one is permitted for numerical convenience, but **the joint normalizer $Z_e$ is still necessary**.

These factors are not automatically the posterior marginals. The actual marginal and conditional opponent distribution are

$$
\mu_{e,0}(x)=\frac{b_0(x)\sum_yM_{B_e}(x,y)b_1(y)}{Z_e},
\qquad
\Pr(h_y\mid h_x,e)=
\frac{M_{B_e}(x,y)b_1(y)}
     {\sum_{y'}M_{B_e}(x,y')b_1(y')},
\tag{posterior}
$$

when the denominators are positive. The expression for BB is the transposed contraction. Treating the two normalized marginal ranges as independent would redeal colliding cards and change the game.

**Why reachable ranges have this form.** Fix one complete public prefix and one behavioral trunk profile. For every compatible pair, the root deal and that particular sequence of board reveals have the same chance factor $\kappa_e$. The probability of the action prefix factors into $r_0(e,x)r_1(e,y)$ because a player's action probabilities depend only on its own physical hand and the public prefix. Hence

$$
\Pr(e,x,y)=\kappa_eM_{B_e}(x,y)r_0(e,x)r_1(e,y).
$$

Conditioning on $e$ gives (boundary). Across multiple exits, compatibility additionally means that these range factors arise from **one common trunk strategy**: at a player edge its factor is multiplied by the matching behavioral probability, sibling action probabilities sum to one, and chance applies the physical-card masks. Arbitrarily chosen ranges at different exits need not be mutually realizable.

A supplied general correlated prior $\mu_e$ can also be handled by the pair-weight formulas below, provided it is nonnegative, normalized, and supported on $M_{B_e}=1$. It must not be replaced by a product unless the factorization is justified.

If $Z_e=0$, no normalized conditional game is defined. Record “zero-probability boundary,” retain the individual boundary factors and original trunk counterfactual reaches, and do not invent a uniform posterior. Retaining only the zero joint on-policy matrix is insufficient: a deviator's own zero prefix action factor must be omitted when considering its earlier deviation. An upstream player can sometimes reach a boundary by deviating even when the current profile gives it probability zero.

##### R1.1.1. Information preservation requires an injective public-history index

The actual infoset is

$$
I_i=(i,h_i,B_n,\operatorname{pub}(n)).
\tag{infoset}
$$

The public record includes the blinds and every action's street, actor, kind, and final target, plus every observed board block and its street. It retains the player's own earlier actions. It excludes the opponent's private hand, future board cards, raw-size aliases, and strategy probabilities. [E2.5, E7; K: Game, play, deal, infoset_key.]

Give every complete public prefix its own node ID. A parent pointer plus an exact appended event is a lossless representation; a hash requires collision checking. The following are different IDs even if all monetary fields match:

- The two preflop call histories ending at matched 28.
- A lead/call and a check/bet/call reaching equal commitments.
- Physically different suit permutations of a board.
- Boards with the same five-card set but exchanged turn and river.

Private opponent hands are summed within one infoset. They do not create separate strategy rows. Mechanical transition templates and card/rank caches may be shared read-only; regret, policy, and average rows remain keyed by (infoset).

Perfect recall follows directly: equality of later keys implies equality of own hand and every earlier public observation and own action. Thus neither the strategy table nor a BR is allowed to condition on an opponent hand, and no own observation is forgotten.

##### R1.1.2. Exact public-history generation requires the ordered monetary compiler

Maintain exact $C,c_0,c_1,\ell,\Delta$, the street, the actor, the preflop route while relevant, and the limp/check origin flag. A half-BB integer accounting representation is sufficient for commitments; raw fractions still use exact integer numerators and denominators. A target $t$ costs $t-c_p$, not $t$ additional chips.

The actor's uncommitted stack is $R-c_p$, the live pot is $P+c_0+c_1$, and the pot after a hypothetical call is $Q=P+2f$. All reachable states obey $0\le C+c_i\le100$ and $P+c_0+c_1=(C+c_0)+(C+c_1)$. A completed street adds its matched target to $C$ once. The initial aggression ledger is $(0.5,1)$ preflop and $(0)$ postflop; only finalized aggressive targets append to it, and passive actions do not create wagers.

For every candidate, eligibility is checked first:

$$
f<R,\qquad \ell<K_s,\qquad
K_0=100,\quad K_s=R\ (s>0).
$$

Then execute, in this exact order,

$$
\begin{aligned}
b_0&=\left\lfloor\frac{2n+d}{2d}\right\rfloor
 &&\text{for raw }n/d\ge0,\\
m&=\begin{cases}1,&\text{unbet postflop opening},\\
f+\Delta,&\text{raise, including the preflop BB option},\end{cases}\\
b_1&=\max(b_0,m),\\
t&=\begin{cases}
100-C,&C+b_1\ge100\\
     &\quad{}\lor(s=0\land b_1>40)\\
     &\quad{}\lor(s\in\{1,2\}\land3(C+b_1)>200),\\
b_1,&\text{otherwise}.
\end{cases}
\end{aligned}
\tag{resolver}
$$

Only after resolving **every** raw candidate do a sorted unique reduction on final targets. Action identity is (kind, final target). No raw alias gets a probability slot. Every output must be an integer with $f<t\le R$; if $t<R$ it meets the full minimum. A minimum-clamped amount above $R$ is snapped down to $R$, not rejected. A short all-in can therefore be below the full minimum. [E3–E4; K: raw_targets, resolve, actions.]

River openings, at BB's lead or SB's action after BB checks, have raw targets

$$
\{P/2,\ P,\ 3P/2,\ R\}.
$$

Every eligible river responding raise, including every re-raise, has raw targets

$$
\{f+\Delta,\ f+Q/2,\ f+Q,\ R\},
\qquad Q=P+2f.
$$

The minimum raise is itself a candidate. Explicit river jams pass the same resolver. River snapping uses only the stack predicate $C+b_1\ge100$.

An unbet node offers check plus its resolved bets. BB's check passes action to SB; SB's following check closes the street. A facing node offers fold, call, and its resolved raises. No fold/call is offered when a check is available. A call closes immediately; there is no subsequent decision for the prior aggressor.

A finalized aggression to $t$ changes only

$$
c_p\leftarrow t,\quad p\leftarrow1-p,\quad
\ell\leftarrow\ell+1,\quad\Delta\leftarrow t-f.
$$

The actual snapped increment is recorded. A facing all-in has only fold/call. Closing at matched current-street target $x$ sets $C_*=C+x$ exactly once and, on the river, goes to showdown.

**Redundant-cap proof.** At a facing state, $\ell\le f$: initially preflop $\ell=f=1$; an opening postflop bet has $\ell=1\le f$; each later integer target increases $f$ by at least one while increasing $\ell$ by one. If $f<R$, then $\ell<R$ postflop and $\ell<100$ preflop. An unopened postflop state has $\ell=0<R$. The displayed caps cannot remove a reachable eligible raise. Imposing a smaller live cap changes the EFG. Strictly increasing integer targets also prove finite within-street aggression. [E3.3, E6.4.]

#### R1.2. BR values require counterfactual rather than omniscient backward recursion

We derive a compact hand-vector recursion from the full pair formulation. This derivation fixes where each probability factor belongs.

##### R1.2.1. The recursion requires exact indices, masks, and forward reaches

Use a fixed global hand axis, or a compact axis with explicit physical-hand maps:

| Revealed cards | Board-compatible hands | Opponent hands compatible with each valid own hand |
|---:|---:|---:|
| 0 | 1326 | 1225 |
| 3 | 1176 | 1081 |
| 4 | 1128 | 1035 |
| 5 | 1081 | 990 |

Let $N$ be the number of distinct public prefixes in the selected solve scope and $N_d$ its decision prefixes. $N$ denotes histories, not the much smaller number of monetary states. A universal action padding size is $A_{\max}=6$: river facing nodes have fold/call plus at most four distinct aggressive targets.

| Tensor/index | Logical shape | Type and meaning |
|---|---|---|
| hole cards; hole bitmasks | $[H,2]$; $[H]$ | Small integers; 64-bit card masks |
| public metadata | $[N]$ records | Parent, street, actor/mode, board, exact accounting, full-prefix identity |
| action mask and child map | $[N_d,6]$ | Boolean legality; child IDs; invalid slots have no child |
| $D,\sigma,S$ | $[N_d,H,6]$ each | Signed regret, policy, average numerator; the row belongs to that node's actor |
| $\rho$ | $[2,N,H]$ | Player-only realization reach |
| $F,m$ | $[2,N,H]$ | Counterfactual values and masses |
| action CF values | $[N_d,H,6]$ | Gathered child $F$ for the acting player |
| pair masks | $[H,H]$ per board tile | Computed or cached; never an infoset quotient |
| optional $U,q$ | $[N,H,H]$ logically | Reference semantics; normally streamed/factorized |
| seven-card ranks | $[B_{\rm batch},H]$ | Integer ranks for a batch of complete physical boards |
| chance edges | CSR offsets and labeled outcomes | Ragged; streamed if necessary |

Use float64 for the default training/value/reach arrays and signed 32-bit integers for packed ranks; exact compilation and 64-bit card masks do not use floating point. This is a concrete default, not a claim that float64 alone certifies accuracy: R1.3 still supplies the enclosure, and its precision may need to increase.

The masks are distinct: public action legality $L[n,a]$, own-hand board validity $v_{B_n}(h)$, pair compatibility $M_{B_n}(x,y)$, and chance-event compatibility. An impossible hand row has zero values and zero stored probabilities. A physically valid but zero-probability hand row remains allocated with a defined legal strategy.

Initialize at the normalized boundary:

$$
q_e(x,y)=\mu_e(x,y),\qquad \rho_i(e,h)=1
$$

on physically valid hands. At a player-$p$ edge $n\to na$,

$$
q_{na}=q_n,\qquad
\rho_p(na,h)=\rho_p(n,h)\sigma_p(n,h,a),\qquad
\rho_{1-p}(na,h)=\rho_{1-p}(n,h).
\tag{reach-player}
$$

At a chance edge with kernel $c(n,S,x,y)$,

$$
q_{nS}(x,y)=q_n(x,y)c(n,S,x,y),\qquad
\rho_i(nS,h)=\rho_i(n,h)
\tag{reach-chance}
$$

followed by the new board-validity mask. River has no such future edge; this equation is required by its earlier-street callers.

The full joint reach is $q_n\rho_0\rho_1$. Player $i$'s counterfactual weight and mass are

$$
w_i(n,x,y)=q_n(x,y)\rho_j(n,h_j),\qquad
m_i(n,h_i)=\sum_{h_j}w_i(n,x,y).
\tag{cf-weight}
$$

There is **no own within-scope strategic reach** in $w_i$. The fixed boundary prior, including any own-hand probability it assigns, is chance and remains in $q_e$.

For factorized boundary inputs, explicit pair storage is unnecessary:

$$
q_n(x,y)=\frac{\kappa_n}{Z_e}
 M_{B_n}(x,y)b_0(x)b_1(y),\qquad\kappa_e=1.
\tag{q-factor}
$$

$\kappa$ is unchanged at player edges and multiplied by the exact board-chance scalar at a reveal. The entire prefix remains part of $n$ even if several nodes use the same scalar and board mask.

##### R1.2.2. The hand-vector recursion follows by contracting hidden hands

For a fixed profile, the pair continuation is

$$
U_i(n,x,y)=
\begin{cases}
u_i(n,x,y),&n\text{ terminal},\\
\sum_S c(n,S,x,y)U_i(nS,x,y),&n\text{ chance},\\
\sum_a\sigma_0(n,x,a)U_i(na,x,y),&0\text{ acts},\\
\sum_a\sigma_1(n,y,a)U_i(na,x,y),&1\text{ acts}.
\end{cases}
\tag{pair-eval}
$$

It excludes all past chance and player probabilities. Now contract

$$
F_i(n,h_i)=\sum_{h_j}w_i(n,x,y)U_i(n,x,y).
\tag{F-definition}
$$

Distributing the finite sums gives the exact compact recursion:

$$
F_i(n,h)=
\begin{cases}
\sum_{h_j}w_i(n,x,y)u_i(n,x,y),&n\text{ terminal},\\
\sum_a\sigma_i(n,h,a)F_i(na,h),&i\text{ acts},\\
\sum_a F_i(na,h),&j\text{ acts},\\
\sum_S F_i(nS,h),&n\text{ chance}.
\end{cases}
\tag{CF-eval}
$$

At an opponent node its action probability is already in the child's $\rho_j$. At chance its probability is already in the child's $q$. Multiplying either probability again is an error. At own nodes the child's counterfactual weight is unchanged, so its action probability is introduced by the displayed mixture.

With compact hand axes, child values are scattered to the identical physical parent-hand index before summing. Hands blocked by a reveal contribute zero. This is an indexing operation, not a reweighting or a new private deal.

To compute a BR for $i$, fix the opponent's **returned average strategy**, recompute its forward reaches, and replace only the own-node line by

$$
F_i^{\rm BR}(n,h)=
\max_{a\in A(n)}F_i^{\rm BR}(na,h).
\tag{CF-BR}
$$

Terminal contractions, opponent sums, and chance sums remain unchanged. At entry,

$$
B_i=\sum_hF_i^{\rm BR}(e,h),\qquad
v_i=\sum_hF_i^{\sigma}(e,h).
\tag{entry-value}
$$

**Proof of infoset consistency and optimality.** Descendant public histories never reconverge into a merged infoset because the full transcript is retained. At an own decision, all histories sharing $(n,h_i)$ differ only in the hidden opponent hand. Their contributions have already been summed into the action vector. One maximizing action is therefore selected for that entire infoset. At an opponent or chance node there is no responding-player choice, so their weighted alternatives add. Backward induction over this finite, perfect-recall information structure proves (CF-BR). Own earlier action probabilities are absent, allowing choices at all counterfactually reachable infosets.

Use a stable first-legal-action tie rule if a deterministic BR policy is exported. Illegal action slots are $-\infty$ for max, never zero. If $m_i=0$, every legal action has value zero; the same tie rule applies.

For contrast, in two equiprobable hidden states with action payoffs $(1,-1)$ and $(-1,1)$, a legal decision is worth zero, while averaging the two statewise maxima gives one. Thus $\sum_yw_y\max_aU_a(y)$ is an omniscient upper bound, not the required $\max_a\sum_yw_yU_a(y)$.

##### R1.2.3. Terminal contractions require net payoffs, exact blockers, and best-five rank

If player $p$ folds, its accumulated investment is $L_f=C+c_p$. Therefore

$$
u_p=-L_f,\qquad u_{1-p}=L_f.
\tag{fold}
$$

The winner's unmatched wager is economically returned and is not profit. Root SB fold is $(-0.5,+0.5)$; a BB fold to a root raise is $(+1,-1)$. No future board is dealt after a fold.

At a closed river with final matched contribution $C_*=C+x$,

$$
u_0(x,y)=C_*\operatorname{sgn}(K(B,h_x)-K(B,h_y)),
\qquad u_1=-u_0.
\tag{showdown}
$$

A tie pays zero. A called-all-in showdown uses $C_*=100$. These are full-hand net changes from before blind posting, not gross pot shares or future-street-only profits. Hence $|u_i|\le100$, and final stacks $100+u_i$ sum to 200. [E8; K: payoff.]

For factorized ranges the terminal GPU contraction is

$$
F_i(n,h)=\frac{\kappa_n}{Z_e}b_i(h)
\sum_{h_j}M_{B_n}(h,h_j)
       b_j(h_j)\rho_j(n,h_j)u_i(n,h,h_j),
\tag{terminal-contraction}
$$

with the pair axes transposed when $i=1$. It is a tiled matrix-vector contraction; only terminal tiles need pair payoffs. Accumulate signed values in a stated precision, with the error enclosure derived in R1.3.

###### R1.2.3.a. Best-five ranking expands into integer GPU operations

Card $c\in\{0,\ldots,51\}$ has rank $2+\lfloor c/4\rfloor$ and suit $c\bmod4$. For each valid seven-card holding $h\cup B$:

1. Use a fixed $[21,5]$ index table of all $\binom75=21$ five-card subsets. Gather a tensor $[B_{\rm batch},H,21,5]$.
2. For each five-card subset, compare its five ranks with each rank $2,\ldots,14$ and sum indicators. This produces rank counts $[B_{\rm batch},H,21,13]$. Do the same for four suits.
3. Set flush if a suit count is 5. For every straight high card $d=5,\ldots,14$, test the five required rank-presence bits. At $d=5$ they are $\{14,2,3,4,5\}$; otherwise they are $\{d-4,\ldots,d\}$. The highest successful $d$, or zero, is the straight high. There is no other wraparound.
4. Select the first matching category in descending priority. The exact predicates are: flush and positive straight high; some rank count equals 4; some rank count equals 3 and another equals 2; flush; positive straight high; some rank count equals 3; exactly two rank counts equal 2; exactly one rank count equals 2; otherwise high card. Obtain the tie digits in the following table by masking ranks to the required multiplicity and sorting those ranks descending; select the required number of kickers from the other ranks. Unavailable tie slots are zero.

| Category | Code | Ordered tie digits |
|---|---:|---|
| Straight flush | 8 | Straight high |
| Four of a kind | 7 | Quad rank, kicker |
| Full house | 6 | Trip rank, pair rank |
| Flush | 5 | Five ranks descending |
| Straight | 4 | Straight high |
| Three of a kind | 3 | Trip rank, two kickers descending |
| Two pair | 2 | Higher pair, lower pair, kicker |
| One pair | 1 | Pair rank, three kickers descending |
| High card | 0 | Five ranks descending |

The masked rank selection in step 4 can itself use only indicators and scans. Traverse the fixed rank axis $14,13,\ldots,2$ with a Boolean eligibility mask for the requested multiplicity or kicker class, prefix-sum that mask, and scatter each eligible rank to its resulting ordinal slot. The first required slots are exactly the descending tie digits. The subset table in step 1 is generated by enumerating $0\le j_0<j_1<j_2<j_3<j_4<7$; there are exactly 21 rows. Neither operation relies on an external poker evaluator.

5. Pad the tie digits to five and pack the six-digit lexicographic tuple into

$$
K_5=c_{\rm category}15^5+t_1 15^4+t_2 15^3+t_3 15^2+t_4 15+t_5.
$$

Every digit is in $0,\ldots,14$. If two tuples first differ at a digit, its base-15 place value exceeds the sum of all possible lower-place differences. Integer comparison is therefore exactly the EFG's lexicographic comparison. $K_5<15^6=11{,}390{,}625$, so signed 32-bit storage suffices.

6. Set $K_7=\max_{\ell=1}^{21}K_5[\ell]$.

This maximum proves best-five semantics, including using zero, one, or both hole cards, a shared-board tie, and multiple possible full houses. Suits appear in the flush test and card masks, never in tie digits. A royal flush is simply category 8, high 14. Invalid duplicated-card holdings are masked before evaluation and never acquire payoff mass. [E8.1; K: _rank_five_unchecked, evaluate.]

###### R1.2.3.b. Blocker contractions expand into Boolean masks and reductions

Store each hand as two card IDs or the bitset $(1\ll c_1)\lor(1\ll c_2)$. Compatibility is a bitwise-AND-zero test against the board mask and the other hand. No probabilistic blocker heuristic is needed.

For fold values and counterfactual masses, let $v(h)=b_j(h)\rho_j(n,h)$ after board masking. Define

$$
T=\sum_hv(h),\qquad
S[c]=\sum_{h:c\in h}v(h).
$$

For own hand $h=(a,b)$, inclusion-exclusion gives

$$
\sum_{h_j}M_B(h,h_j)v(h_j)
=T-S[a]-S[b]+v(h).
\tag{blocker-reduce}
$$

The added term corrects the double subtraction of the intersection, which consists of the identical hand. That colliding hand's net coefficient remains $1-1-1+1=0$. This formula requires own hand board validity; otherwise output zero. Multiply the result by the fold payoff and $\kappa_nb_i(h)/Z_e$.

For showdown, a fully explicit implementation tiles all $(h,h_j)$, compares $K_7(h)$ and $K_7(h_j)$, applies the pair mask, multiplies by $v(h_j)C_*$, and sums. This is exact vectorization with $O(H^2)$ work per distinct terminal board/range contraction and no all-node pair storage.

An optional exact optimization sorts hands by integer rank and performs inclusive group sums and exclusive prefix scans. The unblocked result for rank $k$ is the weight strictly below $k$ minus the weight strictly above $k$. Subtract the corresponding below-minus-above sums for each of the own hand's two cards. The intersection is the identical hand and has equal rank, so its sign contribution is zero. Equal-rank groups contribute to neither side. Grouping here is a temporary arithmetic reduction: every physical hand keeps its separate strategy row.

#### R1.3. The BR certificate requires numerical enclosures

The mass invariant underlying all error bounds is

$$
\begin{cases}
m_i(na,h)=m_i(n,h)&\text{at own-player edges},\\
\sum_a m_i(na,h)=m_i(n,h)&\text{at opponent nodes},\\
\sum_S m_i(nS,h)=m_i(n,h)&\text{at chance nodes}.
\end{cases}
\tag{mass-invariant}
$$

The first equality follows because $w_i$ excludes own actions. The other two follow from exact normalization of opponent action probabilities and physical chance probabilities. Also $\sum_hm_i(e,h)=1$.

**Terminal-error theorem.** If every terminal payoff is approximated with absolute error at most $\delta$, and all probability weights are exact, then both fixed-profile and BR recursions satisfy

$$
|\widehat F_i(n,h)-F_i(n,h)|\le m_i(n,h)\delta.
$$

At terminals this is the triangle inequality. At own nodes, a convex combination or a maximum is 1-Lipschitz in the sup norm; all children have the same mass. At opponent/chance nodes, child errors sum and their masses partition the parent mass. Induction proves the claim and $|\widehat B_i-B_i|\le\delta$ at entry. With uniform error bounds $\delta_0,\delta_1$, the half-NashConv error is at most $(\delta_0+\delta_1)/2$.

For nonuniform local arithmetic errors, carry an absolute radius $E_i(n,h)$. If $\eta_i(n,h)$ bounds the local operation's rounding and input-weight error, use

$$
E_i(n,h)=
\begin{cases}
\eta_i(n,h),&\text{terminal contraction},\\
\eta_i(n,h)+\sum_a\sigma_i(n,h,a)E_i(na,h),&\text{own fixed-profile mixture},\\
\eta_i(n,h)+\max_a E_i(na,h),&\text{own BR maximum},\\
\eta_i(n,h)+\sum_{\rm child}E_i({\rm child},h),
   &\text{opponent or chance}.
\end{cases}
\tag{error-recursion}
$$

The root radius is $\sum_hE_i(e,h)$ plus root-reduction error. Thus

$$
\operatorname{Expl}_e(\bar\sigma)\le
\frac{\widehat B_0+\widehat B_1+E_{B_0}+E_{B_1}}2.
\tag{numerical-cert}
$$

Equivalently, propagate outward-rounded intervals. Terminal dot products start with enclosures; own BR nodes use $[\max_a L_a,\max_a U_a]$; opponent/chance nodes sum interval endpoints. Root endpoints sum over own hands. This encloses the **legal** BR value without an illegal pairwise maximum. If an exact BR action cannot be distinguished numerically, refine its scores or return a feasible tie-resolved candidate together with the certified upper value. A feasible approximate BR's payoff alone is a lower bound and cannot certify low exploitability.

For a floating-point sum or dot product with round-to-nearest unit roundoff $u$, no overflow, and no unaccounted underflow, the standard operation model is $\mathrm{fl}(a\circ b)=(a\circ b)(1+\theta)$, $|\theta|\le u$. Expanding a chain of at most $k$ rounded operations gives an accumulated relative factor bounded by

$$
\gamma_k=\frac{ku}{1-ku}\quad(ku<1).
$$

Indeed, expanding the product of the factors $(1+\theta)$ bounds its deviation by the geometric majorant $ku+(ku)^2+\cdots$. Therefore a dot reduction has absolute rounding error at most $\gamma_k\sum_\ell|x_\ell y_\ell|$, with $k$ chosen for its actual multiply/reduction path. For a balanced tree, $k$ can use one multiplication plus the maximum reduction depth; use the larger sequential bound if execution order is not controlled.

Input interval errors must also be included: for $|\Delta x|\le e_x$, $|\Delta y|\le e_y$,

$$
|\Delta(xy)|\le |x|e_y+|y|e_x+e_xe_y.
$$

Apply this to chance ratios, reaches, normalization, and terminal weights before applying the reduction bound. A second run in higher precision is a diagnostic, not by itself an error proof.

The safest certification treats the saved legal policy as the exact strategy being certified, with each probability interpreted by its saved representation and a precisely defined row normalization. Evaluate its reaches and BR using rational arithmetic, outward intervals, or a proved floating-point enclosure. Enclose the normalization itself; reject nonfinite values or nonpositive row totals. Include a positive lower bound on $Z_e$ when dividing. If intervals are too wide, increase precision or improve the reduction. Never silently flush a tiny positive reach to zero.

### R2. A candidate for R0 requires a reach-weighted average of tabular DCFR iterates

Certification can be applied to any legal profile. The selected method for producing one is full-traversal tabular $\mathrm{DCFR}_{3/2,0,2}$, using simultaneous frozen-profile updates. The parameters are an algorithm choice, not a consequence of poker rules. Brown and Sandholm define separate positive/negative regret discounts and a separate strategy-averaging discount [D].

#### R2.1. The returned policy requires own-realization-weighted averaging

For positive temporal weights $w_t=t^2$, the output at one valid infoset is

$$
\bar\sigma_i^T(n,h,a)=
\frac{\sum_{t=1}^Tt^2\rho_i^t(n,h)\sigma_i^t(n,h,a)}
     {\sum_{t=1}^Tt^2\rho_i^t(n,h)}.
\tag{average}
$$

If the denominator is zero, define the output as uniform over the legal actions. There is no division by zero and no arbitrary epsilon added to the denominator.

**Why the own reach is necessary.** In a perfect-recall game, let $x_i^t(q)$ be player $i$'s realization weight for an own action sequence $q$. Its extension through action $a$ has weight $x_i^t(q)\sigma_i^t(I,a)$. The weighted mixture of these sequence weights has conditional action probability equal to their ratio, exactly (average). Induction on a player's sequence length proves that (average) realizes the weighted mixture of its realization plans. An ordinary arithmetic average of behavioral probabilities generally does not.

Chance and opponent reaches are not part of that ratio. Accumulate once per infoset, not once for every compatible opponent hand. In a fixed-boundary solve a fixed positive boundary own-hand factor would cancel, so it is omitted. A zero boundary own-hand factor must not erase a physically valid strategy row.

A numerically smaller recurrence, with the discount applied **after adding** iteration $t$'s contribution, is

$$
S^0=0,\qquad
S^t=\left(\frac{t}{t+1}\right)^2
       \left[S^{t-1}+\rho_i^t\sigma_i^t\right].
\tag{average-update}
$$

Repeated substitution gives

$$
S^T(n,h,a)=\frac1{(T+1)^2}
\sum_{t=1}^Tt^2\rho_i^t(n,h)\sigma_i^t(n,h,a),
$$

because $\prod_{k=t}^T(k/(k+1))^2=(t/(T+1))^2$. Normalizing $S^T$ over legal actions therefore gives exactly (average). The common factor cancels; no large explicit $t^2$ accumulator is required.

#### R2.2. Each current policy requires regret matching on discounted action regrets

At iteration $t$, freeze the complete policy $\sigma^t$. At an actor-$i$ infoset, gather the action CF values from the already derived backward pass:

$$
Q_i^t(n,h,a)=F_i^t(na,h),\qquad
F_i^t(n,h)=\sum_a\sigma_i^t(n,h,a)Q_i^t(n,h,a).
$$

The immediate counterfactual regret is

$$
r_i^t(n,h,a)=Q_i^t(n,h,a)-F_i^t(n,h).
\tag{instant-regret}
$$

It compares taking action $a$ now and following the current strategy thereafter with following the current strategy now as well. All opponent/private/chance weighting is already in $Q_i^t$. Do not multiply by $\rho_i^t$, divide by $m_i^t$, or renormalize the hidden-hand distribution at this step. A varying division by counterfactual reach changes the weighting of iterations.

From a discounted regret row $D$, regret matching uses

$$
D_+(a)=L[n,a]\max(D(a),0),\qquad d=\sum_aD_+(a),
$$

$$
\mathrm{RM}(D)(a)=
\begin{cases}
D_+(a)/d,&d>0,\\
L[n,a]/|A(n)|,&d=0.
\end{cases}
\tag{RM}
$$

Only positive regret influences the present choice; negative memory remains stored for future updates. The identity $\sum_a\sigma^t(a)r^t(a)=0$ follows from (instant-regret) and checks the action-value baseline. This is an arithmetic diagnostic, not a convergence certificate.

Initialize $D^0=S^0=0$, so $\sigma^1$ is uniform over each deduplicated legal menu. For a valid zero-reach infoset this fallback is still well defined.

##### R2.2.1. The discount rule requires explicit sign and iteration timing

Use end-of-iteration storage. First form

$$
Y^t=D^{t-1}+r^t.
$$

Then store

$$
D^t(a)=
\begin{cases}
\dfrac{t^\alpha}{t^\alpha+1}Y^t(a),&Y^t(a)>0,\\[6pt]
\dfrac{t^\beta}{t^\beta+1}Y^t(a),&Y^t(a)<0,\\
0,&Y^t(a)=0,
\end{cases}
\quad
(\alpha,\beta,\gamma)=(3/2,0,2).
\tag{DCFR}
$$

Thus the negative multiplier is $1/2$, and the positive multiplier is $t\sqrt t/(t\sqrt t+1)$. The sign is the sign **after** adding the immediate regret. Compute $\sigma^{t+1}=\mathrm{RM}(D^t)$.

This convention discounts iteration $t$'s new contribution before storage for the next iteration. A convention storing the undiscounted end-of-iteration sum is equivalent only when the next iteration discounts that stored sum with index $t$ before adding its new regret, and policy extraction is aligned. Writing “discount then add” without specifying those indices leaves a different algorithm possible.

All positive coordinates of a row receive the same multiplier, so that particular end discount does not alter their immediate normalized ratios. It does alter the magnitude carried into the next addition. Negative regrets are also discounted, never clipped to zero. Clipping would define a different regret minimizer.

The averaging discount (average-update) is independent of the sign-dependent regret discount. The latter is not representable as one common polynomial weight on all historical action regrets when signs can change.

##### R2.2.2. One complete iteration requires a frozen forward/backward/update schedule

~~~text
Compile the exact public-history scope and its physical-card masks.
Set D = 0 and S = 0 on all valid infoset/action entries.
Set current policy to uniform over legal actions; t = 1.

Repeat:
    1. Freeze current policy sigma for EVERY infoset in this solve scope.
    2. Forward pass:
           rho_i(entry, hand) = 1;
           propagate player-only reaches with reach-player;
           propagate entry/chance mass with reach-chance or q-factor.
    3. Backward fixed-profile pass:
           compute both players' terminal contractions;
           compute CF-eval in reverse topological order;
           gather each acting infoset's child action values.
    4. For every acting infoset, from that same frozen profile:
           r = action_value - sum_a(sigma[a] * action_value[a]);
           Y = D + r;
           D_next = sign-dependent end discount of Y;
           S_next = (t/(t+1))^2 * (S + rho_actor * sigma).
    5. Commit both players' D_next and S_next together.
       Force padded/invalid entries to exact zero.
    6. At a requested checkpoint:
           bar_sigma = legal row normalization of S;
           freeze this candidate;
           recompute BOTH BR passes against bar_sigma from the entry;
           enclose their numerical error;
           if R-cert passes, return that exact saved candidate and certificate.
    7. sigma = regret_matching(D_next); t = t + 1.
~~~

R2.2.2 is an algorithm specification, not a call to a hidden equilibrium oracle: every operation named in it has an explicit formula above. If a checkpoint fails, continue iterations; there is no claim that an arbitrary fixed iteration count reaches the target. Save the iteration clock with $D,S$ when checkpointing. Restarting a descendant street's clock independently while retaining other tables changes the algorithm.

The frozen simultaneous convention avoids mixing old and newly updated players inside one value computation. Alternating updates are possible but require a separately stated sweep and averaging schedule; they are not silently substituted here.

##### R2.2.3. Zero-reach and normalization rules are part of the algorithm

| Condition | Required behavior |
|---|---|
| Illegal action slot | Policy, regret, and average numerator stay zero; use $-\infty$ only in a legal-action max |
| Hand overlaps current board | Row masked out; values and stored probabilities zero |
| Own $\rho_i=0$ but $m_i>0$ | Compute normal CF regrets; add zero to the strategy average |
| Opponent/chance mass $m_i=0$ | Immediate CF regrets are zero; old regrets and averages still receive the scheduled discounts |
| Positive-regret sum is zero | Uniform over the deduplicated legal actions |
| Average numerator sum is zero | Uniform legal output; retain this policy in later BR certification |
| Boundary $Z_e=0$ | No conditional-game certificate; preserve original factors and parent CF information |
| Conditional opponent mass for one hand is zero | CF value is zero; conditional EV is tagged undefined, or displayed as zero with an explicit invalid flag |
| A probability is tiny but positive | Keep it, rescale with tracked units, or bound any discarded mass; no unproved pruning |

Use BB as the default value unit. One may divide **all** payoffs in a solve by its fixed positive $P_e$, in which case the stopping threshold is $0.005$, and convert values/errors back to BB on export. Never mix values normalized by different child pots in an unconverted parent sum. Regret-row scaling by a positive constant preserves current regret matching only if future regret additions are expressed in the same scaled units; a one-time rescaling without that bookkeeping changes later iterates.

#### R2.3. Why training diagnostics do not replace the BR gate

For any sequence of realization plans and common weights $w_t$, define actual weighted external regrets

$$
\mathcal R_i^{w,T}=
\max_{\tau_i}\sum_{t=1}^Tw_t
\left[u_i(\tau_i,\sigma_j^t)-u_i(\sigma_i^t,\sigma_j^t)\right].
$$

Let $W_T=\sum_tw_t$. The realization-plan mixture proved in R2.1 and linearity against a fixed opposing strategy give

$$
B_i(\bar\sigma_j)
=\frac{\mathcal R_i^{w,T}+
 \sum_tw_tu_i(\sigma_i^t,\sigma_j^t)}{W_T}.
$$

Summing over the players cancels the self-play terms, so

$$
\operatorname{Expl}(\bar\sigma)
=\frac{\mathcal R_0^{w,T}+\mathcal R_1^{w,T}}{2W_T}.
\tag{external-regret-identity}
$$

Counterfactual regret decomposition bounds each external regret by the sum of positive local cumulative action regrets: expand a deviation at its first differing infoset, multiply by the deviating player's own realization weight, and recurse into its descendant infosets; perfect recall ensures each own sequence is counted consistently. Each such realization weight is between zero and one, giving

$$
\mathcal R_i^{w,T}
\le\sum_{I\in\mathcal I_i}
\max\!\left(0,\max_a\sum_tw_tr_i^t(I,a)\right).
\tag{CF-decomposition}
$$

This explains why local counterfactual learning can control equilibrium error. It does not identify the sign-discounted $D^T$ with the common-weight sums on the right. The stored DCFR table is not the external regret in (external-regret-identity). Therefore neither small positive $D$, stable policies, self-play value, nor a training-loss plateau proves R0. The independent BR gate is decisive. [C] gives the CFR framework; [D] identifies the particular discount family.

#### R2.4. Training error can be bounded without claiming trajectory stability

If all action CF values at an infoset are wrong by at most $m_i\delta$, subtracting their current-policy mixture gives immediate-regret error at most $2m_i\delta$, plus rounding.

The scalar sign-discount map $f_t(z)=d_t^+z$ for $z\ge0$, $d_t^-z$ otherwise, has slopes in $[0,1]$ and is continuous at zero. It is therefore 1-Lipschitz, including across a sign change. For the **same frozen policy sequence**, regret error satisfies

$$
\|\widehat D^t-D^t\|_\infty
\le\|\widehat D^{t-1}-D^{t-1}\|_\infty+
\|\widehat r^t-r^t\|_\infty+\eta_t.
$$

This is not a proof that two finite-precision training runs stay close. For positive vectors $x,y$ with sums at least $s>0$,

$$
\left\|\frac{x}{\|x\|_1}-\frac{y}{\|y\|_1}\right\|_1
\le\frac{2\|x-y\|_1}{s}.
$$

Apply the triangle inequality after adding/subtracting $y/\|x\|_1$ to prove it. As $s\to0$, the bound becomes arbitrarily large; regret matching can change sharply near its fallback boundary. The final saved average is certified directly, regardless of its training trajectory.

### R3. River outputs required by an earlier-street caller

For a fixed continuation profile $\pi_e$, define its pair payoff kernel and its unnormalized boundary CF vector:

$$
W_{i,e}^{\pi}(x,y)
=\mathbb E[u_i\mid e,x,y,\pi_e],\qquad
\mathcal C_{i,e}^{\pi}(h;b_j)
=\sum_{h_j}M_{B_e}(h,h_j)b_j(h_j)W_{i,e}^{\pi}(h,h_j).
\tag{continuation-CF}
$$

$W^\pi$ is computed by (pair-eval) and is independent of ranges **when the profile is fixed**. The scalar and conditional per-hand values are

$$
v_i(e,\mu_e,\pi)=
\frac{\sum_hb_i(h)\mathcal C_{i,e}^{\pi}(h;b_j)}{Z_e},
\qquad
v_i(h\mid e)=
\frac{\mathcal C_{i,e}^{\pi}(h;b_j)}
     {\sum_{h_j}M_{B_e}(h,h_j)b_j(h_j)}
\tag{continuation-EV}
$$

on positive denominators.

Also expose $\mathcal C_{i,e}^{\rm BR}(h;b_j,\pi_j)$ against the fixed opponent continuation. Compute it using the same CF-BR sweep with entry weights $M_{B_e}(h,h_j)b_j(h_j)$, **no own boundary factor and no joint normalization**. The sweep is linear in positive weight scale and works with this unnormalized mass. It computes one legal BR for each own hand, including hands whose current own prefix probability is zero.

An earlier-street caller receives: the full-history entry identifier; both fixed range factors and their scale convention; the selected continuation policy; $\mathcal C_i^\pi$ and $\mathcal C_i^{\rm BR}$ or the ability to recompute them; and the local normalized BR certificate and error bounds. No scalar “river equity” can replace this interface.

For an equilibrium selection $\pi_e^\star=\mathrm{SolveRiver}(e,b_0,b_1)$,

$$
(b_0,b_1)\longmapsto
\left(\pi_e^\star,\mathcal C_{0,e}^{\pi^\star},
 \mathcal C_{1,e}^{\pi^\star},\text{certificate}\right)
\tag{range-oracle}
$$

depends on both ranges. The response to a bet depends on the opponent's betting range, which changes bluffing incentives and therefore both strategies. Reusing an equilibrium found for another range pair is a model change requiring a bound. A fixed-profile evaluation cache is not an equilibrium cache.

---

<a id="turn"></a>

## Turn root T0 — certify $\operatorname{Expl}_e(\bar\sigma)\le0.005(2C_e)$

Compare this street: A · [B](derivation-b.md#turn) · [C](derivation-c.md#turn) · [D](derivation-d.md#turn) · [Reading map](#reading-map)

An ordinary turn entry has four revealed cards, BB to act, matched completed commitment $C_e<100$, zero current contributions, and a complete distinct transcript. The root claim concerns the **entire turn-plus-river continuation** under a fixed compatible $\mu_e$.

### T1. The certificate requires turn BRs that can also deviate on the river

Use (R-cert), now over the complete turn subtree. Its two BRs must retain all turn choices and all legal river choices. A BR in a truncated turn tree that freezes the responding player's river strategy is insufficient.

There are exactly three kinds of turn leaves before recursion:

1. A fold, with the exact contribution-based payoff (fold).
2. An ordinary closed turn with $C'=C+x<100$, followed by the next river reveal and an ordinary river game.
3. A called all-in with $C'=100$, followed by one river reveal and immediate showdown, with no river player nodes.

The river evaluation/BR kernels derived under R1–R3 provide each required continuation. The numerical intervals are propagated into the turn BR rather than treated as exact values.

#### T1.1. River continuation requires the correct card kernel and range transport

##### T1.1.1. Card support and probability

For board $B=(F_1,F_2,F_3,t)$ and compatible holes, the physical remaining deck is

$$
U=D\setminus(h_x\cup h_y\cup B),\qquad |U|=44.
$$

The next river $r$ has

$$
c_r(x,y)=\frac{\mathbf1[r\notin B\cup h_x\cup h_y]}{44}.
\tag{turn-chance}
$$

A public implementation may enumerate all 48 cards outside the visible board; the hand-pair mask makes incompatible outcomes zero. For each pair exactly 44 entries survive, proving $\sum_rc_r(x,y)=1$. Neither $1/48$ nor $1/46$ is the dealer's probability.

The child's board is $(F_1,F_2,F_3,t,r)$; do not sort all five cards. The turn and river remain separately observed events even when showdown rank ignores their temporal order. There are 1128 board-compatible hands at turn and 1081 at river, with explicit gather/scatter if compacted. [E2.1–E2.4.]

##### T1.1.2. Fixed-profile backward evaluation

At a closed turn node $n$ before the river reveal,

$$
U_i^\sigma(n,x,y)
=\frac1{44}\sum_{\substack{r\notin B\cup h_x\cup h_y}}
U_i^\sigma(e_r,x,y).
\tag{turn-pair-backup}
$$

For ordinary $C'<100$, $U^\sigma(e_r)$ evaluates the saved river policy. For $C'=100$ it is the immediate $100\operatorname{sgn}(K_7(x)-K_7(y))$ payoff, with the appropriate player's sign. No river bet, check, fold, or artificial check/check history is inserted into a runout.

In the compact representation, propagate $q_{e_r}=q_n c_r$ first and then use $F_i(n,h)=\sum_rF_i(e_r,h)$. Do not insert another $1/44$ into this compact sum.

##### T1.1.3. Compatible transport requires scales as well as normalized ranges

Suppose $n$ is reached from parent solve entry $e$ with player reaches $\rho_i(n,h)$. For revealed river $r$, set

$$
g_i^{\,r}(h)=b_i(h)\rho_i(n,h)v_{B\cup\{r\}}(h),\qquad
Z_r=\sum_{x,y}M_{B\cup\{r\}}(x,y)g_0^{\,r}(x)g_1^{\,r}(y).
$$

For $Z_r>0$, the river conditional game has prior

$$
\mu_r(x,y)=M_{B\cup\{r\}}(x,y)g_0^{\,r}(x)g_1^{\,r}(y)/Z_r.
$$

Let $Z_n=\sum_{x,y}M_Bb_0b_1\rho_0(n,x)\rho_1(n,y)$. If $Z_n>0$, conditional on reaching $n$,

$$
\Pr(r\mid n,\sigma)=\frac{Z_r}{44Z_n}.
\tag{public-posterior-chance}
$$

The posterior reveal probabilities need not be uniform: strategy-dependent ranges have blockers. Their sum is one because every compatible hole pair admits 44 rivers. If $Z_n=0$, leave this conditional law undefined and use the unnormalized counterfactual calculation below. This posterior law is derived from, and never substituted for, the pairwise dealer kernel. The analogous conditional laws on flop and preflop also require their own $Z_n>0$.

For an earlier-street counterfactual calculation, do not reconstruct $F_i$ by dividing a normalized child result by the deviator's own reach. Such a division fails at zero own reach. Instead use the exported unnormalized vector (continuation-CF). With parent chance scale $\kappa_n$,

$$
F_i(e_r,h)=\frac{\kappa_n}{44Z_e}\,
b_i(h)\,
\mathcal C_{i,e_r}^{\pi}(h;g_j^{\,r}).
\tag{CF-glue}
$$

For BR, replace $\mathcal C^\pi$ by the correctly recomputed $\mathcal C_i^{\rm BR}$ against the fixed opponent. The parent **entry** factor $b_i$ remains; the player's own intervening reach $\rho_i(n,h)$ does not. This identity follows directly by substituting (q-factor) into (F-definition).

When $Z_r=0$, the normalized child query is absent, but the expression in (CF-glue) may still be nonzero for a player whose own prefix reach was zero. Preserve individual range factors and opponent CF reach, not merely the all-zero joint on-policy weight.

#### T1.2. The turn error budget requires river-value error, not river exploitability as a substitute

Let $E_{i,r}(h)$ bound each inherited river CF result in the units of (CF-glue). The river-deal node contributes

$$
E_i(n,h)\le \eta_i(n,h)+\sum_rE_{i,r}(h).
\tag{turn-error}
$$

Turn player nodes then propagate these radii with (error-recursion). If each river conditional BR/evaluation result is uniformly accurate within $\delta$ BB for every relevant own hand and incoming opponent range, the mass-invariant proof reduces the aggregate bound to $m_i(n,h)\delta$, not $48\delta$. At entry the BR error is at most $\delta$, plus turn arithmetic error.

A statement “the river profile has exploitability at most $0.005P_r$” is a bound on strategy quality for a particular normalized river prior. It is not a numerical value-error bound and does not certify all opponent ranges encountered by upstream deviations. For exact T0, use complete river BRs with the inherited counterfactual ranges. Conditions under which local strategy-error bounds can replace those BRs are proved under P3.

### T2. A turn candidate requires a turn-wide DCFR loop

Instantiate R2 on every infoset in the turn-plus-river scope. One iteration freezes **both** turn and river policies, computes turn reaches followed by compatible river reaches, evaluates river then turn, and updates both streets' regrets using their current values. Every average contribution uses the same iteration's full own reach from the turn entry and the same temporal weight.

This implementation reuses the river arithmetic kernels; it does not independently solve each river to equilibrium inside a turn regret update. The latter would change the continuation policy as a function of current ranges and would need its own equilibrium-preserving decomposition theorem.

An independently queried SolveRiver remains useful for a specified range pair, warm starts, or a separately certified refinement. Its local average cannot simply replace the globally weighted river average. When a descendant is refined, recertify the assembled turn profile or prove the sufficient conditions in P3.

#### T2.1. Exact turn betting supplies the masks and transitions

The raw opening menu is $\{P/2,P\}$ for both BB's immediate bet and SB after BB checks. Every eligible responding raise is

$$
\{f+\Delta,\ f+Q/2,\ f+Q\},\qquad Q=P+2f.
$$

There is no extra direct jam candidate. Resolve with half-up → minimum → the stack predicate or strict turn predicate $3(C+b_1)>200$ → deduplication. A clamped total equal to $200/3$ would not satisfy the strict predicate; integer commitments make the comparison exact without decimal rounding. At $C=30$, clamped target 36 remains 36, while 37 snaps to $R=70$.

All passive actions, actual-increment updates, and redundant-cap proofs are the R1.1.2 rules. Closing at $x$ adds $x$ once to $C$, then chooses ordinary river dealing versus forced runout by whether $C'=100$. In the kernel, the pending descriptor's street already names the scheduled next reveal; the last action's transcript retains its original street. [E3–E4, E6; K: _settle, advance_board.]

### T3. Turn export is a range-dependent continuation object

The same formulas (continuation-CF)–(range-oracle) now integrate turn actions and the river. Export the selected full suffix policy, both unnormalized evaluation and BR vectors, range/scale metadata, and a normalized T0 certificate. This object is the exact dependency required by a flop caller.

There is no board-only or pot-only turn value. Even identical $C$, board, and legal actions have different infosets under different prior public histories; a fixed-policy numeric cache can be reused only when all of its actual inputs agree, without sharing learned table rows.

---

<a id="flop"></a>

## Flop root F0 — certify $\operatorname{Expl}_e(\bar\sigma)\le0.005(2C_e)$

Compare this street: A · [B](derivation-b.md#flop) · [C](derivation-c.md#flop) · [D](derivation-d.md#flop) · [Reading map](#reading-map)

An ordinary flop entry has its sorted three-card flop, BB to act, $C_e<100$, zero current contributions, the full preflop transcript, and the exact limp/check origin flag. Its boundary prior is (boundary). The claim concerns the **whole flop-turn-river continuation**, not a flop-only game with fixed future strategies.

### F1. The certificate requires complete-suffix BRs and the turn continuation interface

Apply (R-cert) to this entire scope. After flop action closure, distinguish fold, ordinary next-street entry, and called-all-in runout exactly as at turn. Each ordinary continuation uses T1–T3 with its own complete prefix and transported ranges. A flop BR must be free to change all of its subsequent turn and river actions against the fixed opposing profile.

#### F1.1. Future-card dependencies expand into two labeled kernels

At flop board $F=(F_1,F_2,F_3)$, compatible holes leave $45$ physical cards. The next turn $t$ obeys

$$
c_t(x,y)=\frac{\mathbf1[t\notin F\cup h_x\cup h_y]}{45}.
\tag{flop-chance}
$$

Enumerate all 49 public candidates outside $F$, mask each pair, and give every surviving outcome mass $1/45$. The next ordinary turn entry stores $(F_1,F_2,F_3,t)$. Its 1128 valid hand slots are gathered from the flop's 1176 valid slots, or handled by the fixed 1326-axis masks.

After an ordinary flop closure at $C'=C+x<100$,

$$
U_i^\sigma(n,x,y)
=\frac1{45}\sum_{t\notin F\cup h_x\cup h_y}
U_i^\sigma(e_t,x,y).
\tag{flop-backup}
$$

Here $U(e_t)$ is a turn-plus-river **evaluation** of the frozen profile. The corresponding compact sum is $\sum_tF_i(e_t,h)$ after $1/45$ has entered the child's chance weight. To certify a BR, use the full turn BR continuation, not this fixed-player evaluation leaf.

The range transport and CF glue are exactly T1.1.3 with $r\mapsto t$ and $44\mapsto45$:

$$
g_i^{\,t}=b_i\rho_i(n,\cdot)v_{F\cup\{t\}},\quad
\Pr(t\mid n)=\frac{Z_t}{45Z_n},\quad
F_i(e_t,h)=\frac{\kappa_n}{45Z_e}b_i(h)
\mathcal C_{i,e_t}(h;g_j^{\,t}).
$$

All sums retain physical card identities and full prefixes.

##### F1.1.1. A called flop all-in is a forced chance expectation

If $C'=100$, the turn and river are dealt without intervening player decisions:

$$
U_0^{\rm allin}(F,x,y)=
\frac{100}{45\cdot44}
\sum_{\substack{t\notin F\cup h_x\cup h_y\\
                 r\notin F\cup h_x\cup h_y\cup\{t\}}}
\operatorname{sgn}
\left(K_7(h_x,F,t,r)-K_7(h_y,F,t,r)\right),
\quad U_1=-U_0.
\tag{flop-runout}
$$

There are $45\cdot44$ legal **ordered, street-labeled** $(t,r)$ outcomes per private pair, each with this mass. This is two successive ordinary chance kernels. Its sum is one because the first kernel has 45 possibilities and each child has 44.

Streaming the paired chance loops and reducing their terminal contractions is exact. Assigning the same probability to an unordered two-card set would lose its multiplicity and change the chance measure. No turn/river regret or strategy rows exist on this forced branch. Skipped streets have the EFG's zero ledgers, not artificial checks. The jam's preceding fold/call response remains an ordinary decision node; a jam itself is not terminal. [E2.4, E3.4, E6.3.]

#### F1.2. The flop error budget recursively inherits certified turn errors

At every turn-deal node, add the inherited turn CF error intervals over legal public outcomes, then propagate through flop mixtures/maxima exactly as in (error-recursion). The mass invariant prevents multiplication of a uniform BB error by the number of possible cards or complete runouts.

If a complete turn continuation interface has worst-case conditional value/BR error $\delta_T$ over the required ranges, its aggregate contribution to each flop BR error is at most $\delta_T$. If its river error has already been included in $\delta_T$, it is not a new independent error source. For an implementation with separately bounded turn and river residuals, use the distinct additive residuals in P3.1.

A local turn exploitability certificate is still a strategy-error statement under its own boundary prior. It can enter a global error budget only through the extra coverage/conditional-range assumptions proved in P3.2.

### F2. A flop candidate requires one coherent flop-through-river DCFR iteration

Instantiate R2 over all three remaining streets. The forward order is flop → turn → river; the frozen-profile value order is river → turn → flop. Regret updates use all current action values and one simultaneous commit. The average at every descendant infoset uses its own realization reach from the flop entry, including the player's earlier flop and turn decisions.

Calling turn **evaluation** recursively is exact dynamic programming for the current profile. Calling an independently solved turn equilibrium at changing ranges is a different nonlinear procedure. It does not become standard tabular DCFR merely because its outputs are stored in a tensor.

#### F2.1. Exact flop menus require the preflop-origin distinction

The opening raw targets, for either immediate BB lead or SB after BB checks, are

$$
\begin{cases}
\{P/2,P\},&\text{preflop was exactly SB limp, BB check},\\
\{P/3,2P/3\},&\text{every other origin}.
\end{cases}
$$

The flag is true only for that complete origin. At an ordinary flop entry it is equivalently $C=1$, but it is retained as explicit public metadata. It does not affect later-street menus.

Every eligible responding raise/re-raise has raw targets

$$
\{f+\Delta,\ f+Q/2,\ f+Q\},\qquad Q=P+2f.
$$

Resolve by (resolver), including the strict flop predicate $3(C+b_1)>200$, then deduplicate. No extra earlier-street jam, seat-specific size rule, initiative restriction, board-texture adjustment, or hand-strength classification is added.

As a direct half-up example, the ordinary flop entry with $C=4$ has $P=8$ and raw openings $8/3,16/3$, resolving to $3,5$. With $C=36$, raw openings are $24,48$; the second is snapped to $R=64$ because $3(36+48)>200$. These values agree with the complete preflop exit table below. [E4, E5.3.]

### F3. Flop export retains all suffix policies, ranges, and error units

Export the same complete continuation object as R3/T3, now including all flop, turn, and river strategies. Unnormalized vectors are in BB times the opponent boundary factor's units, while the normalized local certificate is in BB. Preserve both labels so a preflop caller can apply its own initial chance scale and counterfactual reaches exactly once.

---

<a id="preflop"></a>

## Preflop root P0 — certify $\operatorname{Expl}_{\rm pre}(\bar\sigma)\le0.0075$ BB

Compare this street: A · [B](derivation-b.md#preflop) · [C](derivation-c.md#preflop) · [D](derivation-d.md#preflop) · [Reading map](#reading-map)

The initial stacks are 100 BB including the posted blinds. The deterministic blind record is SB $0.5$, BB $1$, followed by private-deal chance and then the SB decision. The entry pot used for certification is the live posted pot $1.5$ BB:

$$
\varepsilon_{\rm pre}=\frac1{200}\frac32
=\frac3{400}=0.0075\ {\rm BB}.
\tag{pre-target}
$$

The exact initial public mechanics are

$$
(s,p,C,P,c_0,c_1,\ell,\Delta)
=(0,\mathrm{SB},0,0,\tfrac12,1,1,1).
$$

The initial minimum increment is one, not the half-BB difference between the blinds. Root chance, not a player, acts first.

### P1. The root certificate requires full-game BRs from the original private-deal law

At the public preflop root after private dealing, use

$$
\mu_{\rm pre}(x,y)=
\frac{M_{\varnothing}(x,y)}
     {\binom{52}{2}\binom{50}{2}}
=\frac{M_{\varnothing}(x,y)}{1{,}624{,}350}.
\tag{private-chance}
$$

This enumerates unordered private pairs assigned to **labeled** seats. It is normalized because each of 1326 SB hands has 1225 compatible BB hands. There are no ordered-within-hand duplicates and no seat-exchange quotient. Wrong lengths, out-of-deck cards, overlaps, or noncanonical pairs have zero chance probability. [E2.1–E2.2; K: chance_events, chance_probability.]

Both full BR sweeps use (CF-BR), with every later ordinary street and forced runout present. For a candidate profile, stop only if

$$
\boxed{B_0^++B_1^+\le0.015\ {\rm BB}.}
\tag{pre-cert}
$$

Negative individual BR values are possible and must not be clipped to zero. Their sum is nonnegative in exact arithmetic. A negative total upper bound signals a faulty enclosure or normalization, not “better than equilibrium.”

#### P1.1. The preflop dependency is the exact finite automaton

Use the following full decision table, equivalent to [E5.2] and the supplied JSON. In this table $F_v$ is a fold with SB payoff $v$ and BB payoff $-v$; $E(C)$ means ordinary flop chance after the displayed complete prefix; $U$ means a called-all-in runout. Every occurrence is a separate history.

| Node | Complete public action prefix | Actor | $(c_0,c_1)$ | $\ell,\Delta$ | Fold | Passive successor | Aggressive successors |
|---|---|---|---|---|---|---|---|
| P0 | empty | SB | $(0.5,1)$ | $1,1$ | $F_{-0.5}$ | $C1\to L0$ | $R2\to O2;\ R3\to O3$ |
| L0 | C1 | BB | $(1,1)$ | $1,1$ | absent | $X\to E(1)$ | $R4\to L4$ |
| L4 | C1 R4 | SB | $(1,4)$ | $2,3$ | $F_{-1}$ | $C4\to E(4)$ | $R12\to L12$ |
| L12 | C1 R4 R12 | BB | $(12,4)$ | $3,8$ | $F_{+4}$ | $C12\to E(12)$ | $R28\to L28$ |
| L28 | C1 R4 R12 R28 | SB | $(12,28)$ | $4,16$ | $F_{-12}$ | $C28\to E(28)$ | raw 60 $\to R100\to LJ$ |
| LJ | C1 R4 R12 R28 R100 | BB | $(100,28)$ | $5,72$ | $F_{+28}$ | $C100\to U$ | absent |
| O2 | R2 | BB | $(2,1)$ | $2,1$ | $F_{+1}$ | $C2\to E(2)$ | $R8\to O8$ |
| O8 | R2 R8 | SB | $(2,8)$ | $3,6$ | $F_{-2}$ | $C8\to E(8)$ | $R22\to O22$ |
| O22 | R2 R8 R22 | BB | $(22,8)$ | $4,14$ | $F_{+8}$ | $C22\to E(22)$ | $R36\to O36$; raw 50 $\to R100\to O2J$ |
| O36 | R2 R8 R22 R36 | SB | $(22,36)$ | $5,14$ | $F_{-22}$ | $C36\to E(36)$ | raw 50 $\to R100\to O36J$ |
| O2J | R2 R8 R22 R100 | SB | $(22,100)$ | $5,78$ | $F_{-22}$ | $C100\to U$ | absent |
| O36J | R2 R8 R22 R36 R100 | BB | $(100,36)$ | $6,64$ | $F_{+36}$ | $C100\to U$ | absent |
| O3 | R3 | BB | $(3,1)$ | $2,2$ | $F_{+1}$ | $C3\to E(3)$ | $R11\to O11$ |
| O11 | R3 R11 | SB | $(3,11)$ | $3,8$ | $F_{-3}$ | $C11\to E(11)$ | $R28\to O28$ |
| O28 | R3 R11 R28 | BB | $(28,11)$ | $4,17$ | $F_{+11}$ | $C28\to E(28)$ | raw 60 $\to R100\to O3J$ |
| O3J | R3 R11 R28 R100 | SB | $(28,100)$ | $5,72$ | $F_{-28}$ | $C100\to U$ | absent |

The raw targets not marked 50 or 60 equal their final targets. All candidates still follow (resolver). Preflop's strict snap is $b_1>40$; 40 itself would not snap. In O22, 36 is a full minimum raise because $22+14=36$. O36's next raw 50 meets its minimum and then snaps.

Only the initial SB call fails to close the street: it gives BB the option. The BB option has check, not fold/call. Every other call closes; each jam has an explicit response row. The kernel's internal preflop route token for the root limp is C, while the public action token and JSON are C1. Route metadata never replaces the full public transcript.

There are exactly **16** public decision prefixes, **11** ordinary flop exits, and **4** distinct called-all-in exits in this automaton. These are public control counts, not the full card-expanded node count.

##### P1.1.1. Ordinary flop exits retain distinct histories and exact opening masks

After the flop reveal each exit has BB acting, zero current contributions, and $\ell=\Delta=0$:

| Complete closed preflop prefix | $C$ | $P=2C$ | $R$ | Limp/check | Resolved flop opening targets |
|---|---:|---:|---:|---|---|
| C1 X | 1 | 2 | 99 | true | $\{1,2\}$ |
| C1 R4 C4 | 4 | 8 | 96 | false | $\{3,5\}$ |
| C1 R4 R12 C12 | 12 | 24 | 88 | false | $\{8,16\}$ |
| C1 R4 R12 R28 C28 | 28 | 56 | 72 | false | $\{19,37\}$ |
| R2 C2 | 2 | 4 | 98 | false | $\{1,3\}$ |
| R2 R8 C8 | 8 | 16 | 92 | false | $\{5,11\}$ |
| R2 R8 R22 C22 | 22 | 44 | 78 | false | $\{15,29\}$ |
| R2 R8 R22 R36 C36 | 36 | 72 | 64 | false | $\{24,64\}$ |
| R3 C3 | 3 | 6 | 97 | false | $\{2,4\}$ |
| R3 R11 C11 | 11 | 22 | 89 | false | $\{7,15\}$ |
| R3 R11 R28 C28 | 28 | 56 | 72 | false | $\{19,37\}$ |

The two $C=28$ entries share a read-only monetary template but not any infoset, regret table, strategy row, or average accumulator. Future board reveals append to each distinct prefix.

##### P1.1.2. Flop chance requires unordered triples from the deck excluding both hands

For each compatible pair, the flop is a uniformly chosen increasing triple from the 48 remaining cards:

$$
c_F(x,y)=
\frac{\mathbf1[F_1<F_2<F_3,\ F\cap(h_x\cup h_y)=\varnothing]}
     {\binom{48}{3}},
\qquad\binom{48}{3}=17{,}296.
\tag{pre-flop-chance}
$$

A public implementation may enumerate the $\binom{52}{3}=22{,}100$ sorted triples and pair-mask each one; exactly 17,296 survive per pair. Enumerating only triples from a pair's remaining deck is also exact, provided those events are routed to the same physical public-history IDs. Sorting the flop is representation canonicalization, not an extra chance event.

At an ordinary preflop exit,

$$
U_i^\sigma(n,x,y)
=\frac1{\binom{48}{3}}
\sum_{\substack{F\subset D\setminus(h_x\cup h_y)\\|F|=3}}
U_i^\sigma(e_F,x,y).
\tag{pre-backup}
$$

Range transport is again T1.1.3, replacing its denominator by $\binom{48}{3}$ and its board mask by the revealed flop mask. This gives

$$
g_i^F=b_i\rho_i(n,\cdot)v_F,\qquad
\Pr(F\mid n)=\frac{Z_F}{\binom{48}{3}Z_n}.
$$

At the original full-game root $b_0=b_1=1$ and $Z_e=1{,}624{,}350$. The child's inherited CF factor is $b_i/[\binom{48}{3}Z_e]$, multiplied by the exported opponent-weighted flop vector. The counterfactual calculation still excludes the responding player's intervening preflop action reach.

##### P1.1.3. Called preflop all-ins retain all three labeled chance stages

For a called jam, use the exact forced runout:

$$
\begin{aligned}
U_0^{\rm allin}(x,y)
={}&\frac{100}{\binom{48}{3}\,45\,44}
\sum_{\substack{F\subset D\setminus(h_x\cup h_y),\ |F|=3\\
                 t\notin F\cup h_x\cup h_y\\
                 r\notin F\cup h_x\cup h_y\cup\{t\}}}
\operatorname{sgn}\!\left(K_7(h_x,F,t,r)-K_7(h_y,F,t,r)\right),\\
U_1^{\rm allin}={}&-U_0^{\rm allin}.
\end{aligned}
\tag{pre-runout}
$$

Each legal labeled outcome has mass $1/[\binom{48}{3}45\cdot44]$. The normalizing count is the product of the three conditional support sizes. There are no future betting nodes, and skipped streets have only ledger zeros. The four called-jam prefixes stay separate in the history structure even if a pure card-equity tensor is reused for their identical forced-payoff calculation.

The complete forced-runout interface is:

| Street of called all-in | Remaining labeled chance | Probability per legal outcome |
|---|---|---|
| Preflop | Sorted flop, turn, river | $1/[\binom{48}{3}45\cdot44]$ |
| Flop | Turn, river | $1/(45\cdot44)$ |
| Turn | River | $1/44$ |
| River | Empty; immediate showdown | $1$ |

An incomplete runout is not terminal, and a fold ends immediately without entering this interface. No burn-card state is introduced. [E2.3–E2.5.]

### P2. A preflop candidate requires full-history DCFR across all four streets

Apply the exact R2 loop from the original private-deal distribution. Compile the preflop automaton and recursively instantiate all ordinary postflop grammar branches, physical board reveals, and forced runouts.

For one iteration:

1. Freeze the complete four-street strategy.
2. Propagate private-deal/chance masses and both players' own action reaches from preflop through river.
3. Evaluate terminal ranks and net payoffs, then reduce river → turn → flop → preflop.
4. Compute every actor's action CF regret using the same frozen profile.
5. Add that profile to every infoset's average using its **full-game own realization reach** and the common $t^2$ weight.
6. Commit both players' discounted regrets simultaneously and form the next policy.
7. Periodically recompute full-game BRs of the saved average and apply (pre-cert).

This is the exact meaning of using later-street solvers as dependencies: their arithmetic, continuation interfaces, and optional local query routines are established first; the full-game learning process remains coherent. A single backwards sweep computes values of the current profile. It does not find equilibrium.

#### P2.1. Practical vectorization preserves tabular identity

Bucket work by street, depth, actor, action count, and board for execution only. Use reverse topological reductions with a barrier before a parent consumes child values. Independent board/hand tiles may run in parallel. Full-history IDs remain separate even within one batch.

The principal GPU primitives are gather/scatter, integer arithmetic, Boolean masks, fixed small-axis sorting, histogram/indicator sums, masked sum/max, prefix scans, and tiled matrix-vector contractions. Their dependencies have all been expanded above. Postflop betting menus can be compiled from exact rational/integer metadata on the host and uploaded as immutable action masks and child maps.

Storage is at least proportional to the number of distinct infosets and their legal actions, not merely to pots or boards. With a padded dense layout, each of $D,\sigma,S$ needs $N_dH A_{\max}$ numeric entries; $F$ and $\rho$ need $2NH$ logical entries each. At 8 bytes per numeric entry these counts give their respective byte budgets directly. Ragged legal-action storage removes padding; board-specific hand lists remove invalid slots. Neither removes a legal infoset. Values/reaches can be tiled, recomputed, or streamed out of core. All learned tabular rows must still be retained or reproduced exactly from a checkpoint.

There is no claim that the exact full-history R1 tree fits on one GPU, or that its solution is inexpensive. Monte Carlo sampling, suit canonicalization, card buckets, state merging, extra raise limits, or pruning without a proved error allowance would be different implementation/approximation choices. They are not part of this derivation.

#### P2.2. Local certificates and the global certificate are distinct deliverables

A standalone SolveRiver, SolveTurn, or SolveFlop query accepts a fixed compatible boundary distribution and returns its scope's BR-certified policy. The final preflop policy is separately certified from the original private-deal law.

If a deployment additionally requires the **same assembled profile** to satisfy all specified positive-probability street-entry tests, evaluate each requested entry using the posterior induced by that assembled profile and enforce those tests as an additional conjunction. A low root error can hide a larger conditional error in a rare subtree. If one refines that subtree to repair its local test, recertify the root after the change.

A zero-probability entry has no unique on-policy posterior. A separately chosen reference-range test must be labeled as such and does not by itself constrain deviations that change the entry range.

---

### P3. A valid preflop claim requires proved numerical and continuation composition

This branch supplies the conditions under which the preceding local certificates imply anything about a larger game. Full-game BR certification is the direct sufficient condition. The alternatives below explain exactly what must be proved when a continuation or local solve is substituted.

#### P3.1. Numerical and continuation-value error propagate through expectations and legal maxima

##### P3.1.1. Uniform perturbations on an unchanged strategy space

Suppose two payoff models have the same histories, chance law, infosets, and legal strategies. If, for every terminal,

$$
|u_i(z)-\widehat u_i(z)|\le\delta_i,
$$

then for every fixed profile,

$$
|u_i(\sigma)-\widehat u_i(\sigma)|\le\delta_i.
$$

This follows by integrating the pointwise bound over a probability distribution. Taking maxima over the **same** strategy set preserves the bound:

$$
|B_i(\sigma_j)-\widehat B_i(\sigma_j)|\le\delta_i.
$$

For two zero-sum models,

$$
\left|\operatorname{Expl}_{G}(\sigma)
      -\operatorname{Expl}_{\widehat G}(\sigma)\right|
\le\frac{\delta_0+\delta_1}{2}.
\tag{model-error}
$$

In the symmetric case this is $\delta$, while the NashConv allowance is $2\delta$. Thus an $\epsilon$ half-NashConv certificate in the surrogate implies an $\epsilon+\delta$ certificate in the original model, subject to the stated uniformity and unchanged-strategy-space assumptions.

More generally, it suffices that for each fixed opposing profile,

$$
\sup_{\tau_i\in\Sigma_i}
\left|u_i(\tau_i,\sigma_j)
      -\widehat u_i(\tau_i,\sigma_j)\right|\le D_i.
\tag{deviation-uniform-error}
$$

Then $\operatorname{Expl}_G(\sigma)\le
(\widehat B_0+\widehat B_1+D_0+D_1)/2$.
Uniform accuracy only at the current joint profile does not meet this assumption.

##### P3.1.2. Disjoint boundary errors are weighted by deviation reach

Let $\mathcal E$ be a frontier of disjoint public subtrees: a play reaches at most one of its entries. Suppose the relevant continuation **evaluation/BR functional** at $e$ has an error bounded by nonnegative $\delta_{i,e}$, uniformly over the hidden states and incoming ranges needed by the larger BR. Then

$$
D_i\le
\sup_{\tau_i}\sum_{e\in\mathcal E}
\Pr_{\tau_i,\sigma_j}(e)\,\delta_{i,e}.
\tag{frontier-error}
$$

Proof: for each fixed deviation, condition its payoff error on the first frontier entry; apply the conditional bound; then maximize. A simple valid bound is $\max_e\delta_{i,e}$ when no earlier arithmetic error occurs. A tighter bound can be computed by the same infoset-consistent max/sum recursion, with $\delta_{i,e}$ as nonnegative frontier rewards and zero elsewhere.

If the error varies by own hand or private pair, use the corresponding hand-dependent terminal contraction; do not take an omniscient action maximum. This preserves the same legal strategy set.

For a multistreet implementation with distinct residuals on successive cuts, telescope the value replacements. If the maximum accumulated residual along any legal play is $D$, every fixed-profile or BR value is perturbed by at most $D$. Expectations average residuals and legal maxima cannot exceed the largest attainable total. An explicit sum $\delta_F+\delta_T+\delta_R$ is a conservative bound when those quantities bound separate stage residuals. A turn-tail error that already includes river error must not be described as a new one-street residual.

When using globally scaled CF vectors, apply (error-recursion) directly instead of repeatedly normalizing them. Their masses already contain the appropriate chance/opponent factors, and their own-action maxima select the relevant deviation reach.

##### P3.1.3. Errors in ranges and chance kernels require separate allowances

For normalized boundary laws $\mu,\nu$ and $|u_i|\le100$,

$$
|u_i^\mu(\sigma)-u_i^\nu(\sigma)|
\le100\|\mu-\nu\|_1
=200\,\operatorname{TV}(\mu,\nu).
\tag{range-error}
$$

The same bound holds for a BR value: use the bound for every responding strategy, then take maxima. It also holds for half-NashConv and for the zero-sum minimax scalar, by successive maxima/minima over the same strategy space. It does **not** imply continuity of a selected equilibrium policy.

For nonnegative masked weights $W,\widehat W$ with positive totals $Z,\widehat Z$, let $\Delta_W=\|W-\widehat W\|_1$. Adding and subtracting $\widehat W/Z$ gives

$$
\left\|\frac WZ-\frac{\widehat W}{\widehat Z}\right\|_1
\le\frac{\Delta_W+|Z-\widehat Z|}{Z}
\le\frac{2\Delta_W}{Z}
\le\frac{2\Delta_W}{\min(Z,\widehat Z)}.
\tag{range-normalization-error}
$$

For factored weights, a usable bound is

$$
\Delta_W\le
\|b_0-\widehat b_0\|_1\|b_1\|_1+
\|\widehat b_0\|_1\|b_1-\widehat b_1\|_1,
$$

since the compatibility mask has entries at most one. A small $Z$ can make normalization ill-conditioned. Keep an interval lower bound on it; adding a numerical epsilon to $Z$ changes the prior.

If an implementation deliberately replaces exact normalized chance kernels by normalized kernels with total-variation error at most $\theta_k$ at successive stages, couple the two processes to agree until a mismatch. Their mismatch probability is at most $\min(1,\sum_k\theta_k)$, even with subsequent history-dependent strategies. On matched paths utility is identical; on mismatched paths its difference is at most 200. Therefore

$$
D_i\le200\min\!\left(1,\sum_k\theta_k\right).
\tag{chance-error}
$$

The same uniform bound passes through the BR maximum. This is a proof for normalized stochastic kernels. Rounded unnormalized weights require the direct interval treatment instead. The intended implementation keeps exact chance supports and rational denominators and encloses their floating-point evaluation; it does not introduce a new chance model.

##### P3.1.4. Fixed-tail evaluation accuracy is not a tail-deviation bound

Suppose a pair matrix $\widehat W_e$ approximates the fixed-policy kernel $W_e^\sigma$ to within $\delta_e$. This controls evaluation of that fixed tail and a trunk game in which both players' tail policies are frozen. It does not bound the improvement from choosing a different tail policy. Even $\delta_e=0$ may describe an exploitable continuation exactly.

To certify the full game one must therefore do at least one of the following:

- Retain the tail and run its full legal BR.
- Supply the exact or enclosed tail BR vector against the fixed opponent, with the inherited CF range and scale.
- Add a separately proved tail-deviation residual as in P3.2.

These are distinct proof obligations. An approximate equilibrium's small local gap cannot be substituted for a pointwise value-error bound, and a good value approximation cannot be substituted for a local equilibrium gap.

#### P3.2. Local strategy gaps imply a global gap only with deviation coverage

We now prove a sufficient local-to-global bound without assuming that ordinary self-play reach controls deviations.

##### P3.2.1. Define the fixed-tail trunk and per-hand tail deviation gains

Fix one full candidate profile $\sigma$ and a disjoint frontier $\mathcal E$. Replace each continuation by its exact fixed-policy pair kernel $W_e^\sigma$ to obtain a trunk game. In this trunk game only the responding player's actions **before** the frontier may change. Let its half-NashConv be $\operatorname{Expl}_{\rm trunk}$.

For player $i$, boundary $e$, and own hand $h$, define

$$
d_{i,e}(h)=
\max_{\tau_i^e}
\mathbb E[u_i\mid e,h;\tau_i^e,\sigma_j^e]
-
\mathbb E[u_i\mid e,h;\sigma_i^e,\sigma_j^e]\ge0.
\tag{tail-gain}
$$

The opponent's conditional hand law is the one induced by original chance and its fixed deployed prefix strategy. For positive conditional mass, an upstream unilateral deviation by $i$ cannot change that law **at fixed $(e,h)$**: its own prefix action likelihood is a common factor across the hidden opponent hands and cancels. Full-history infosets make this cancellation legitimate. Only the likelihood of reaching $(e,h)$ changes.

The $d_{i,e}$ vector is computed from the difference between the exported unnormalized BR and profile vectors, divided by the compatible opponent mass when positive. A zero opponent mass means $(e,h)$ is unreachable against that fixed opponent and contributes zero to the global calculation.

Let

$$
p_i^\beta(e,h)=
\Pr_{\beta_i,\sigma_j}(\text{first frontier entry is }e,\ h_i=h)
$$

for an arbitrary upstream unilateral deviation. Define its worst possible tail gain

$$
\Delta_i=
\sup_{\beta_i}\sum_{e,h}p_i^\beta(e,h)d_{i,e}(h).
\tag{tail-residual}
$$

##### P3.2.2. Decompose a full deviation into trunk and tails

For a fixed deviating trunk strategy $\beta_i$, replacing its prescribed tails by optimal tails improves its value by the sum in (tail-residual): condition on the disjoint first frontier entry and own hand. Full-history separation permits independent tail actions without violating any shared infoset.

The value with prescribed tails is at most $B_{i,\rm trunk}$. Maximizing its value plus the tail gain and using $\max(f+g)\le\max f+\max g$ yields

$$
B_{i,\rm full}\le B_{i,\rm trunk}+\Delta_i.
$$

The original candidate's value is the same in the full and fixed-tail trunk games. Summing unilateral improvements proves

$$
\boxed{
\operatorname{Expl}_{\rm full}(\sigma)
\le
\operatorname{Expl}_{\rm trunk}(\sigma)
+\frac{\Delta_0+\Delta_1}{2}.
}
\tag{local-global-residual}
$$

This is a sufficient bound, not an equality in general.

$\Delta_i$ itself requires no new black box. Compute the original-game counterfactual mass $m_i(e,h)$ using chance and the deployed opponent's prefix actions only. Set the frontier CF reward to $m_i(e,h)d_{i,e}(h)$, zero at other terminal branches, and apply the same own-max/opponent-sum/chance-sum recurrence through the trunk. Summing at the original entry returns the supremum in (tail-residual).

##### P3.2.3. Turn normalized local certificates into a bound using coverage ratios

Suppose each local test uses reference prior $\mu_e^{\rm ref}$ and the **same deployed tail strategies**. Let $q_{i,e}^{\rm ref}(h)$ be its own-hand marginal. Assume its conditional opponent law, for every relevant own hand, equals the deployed opponent's conditional law used in (tail-gain). Then its unilateral local gain is

$$
g_{i,e}^{\rm ref}
=\sum_hq_{i,e}^{\rm ref}(h)d_{i,e}(h),
\qquad
g_{0,e}^{\rm ref}+g_{1,e}^{\rm ref}\le2\epsilon_e
\tag{local-gains}
$$

when its certified half-NashConv is at most $\epsilon_e$.

Assume finite deviation-coverage constants $\Lambda_{i,e}$ satisfy

$$
p_i^\beta(e,h)\le
\Lambda_{i,e}\,q_{i,e}^{\rm ref}(h)
\quad\text{for every relevant }\beta_i,h.
\tag{coverage}
$$

One explicit sufficient choice is

$$
\Lambda_{i,e}=
\max_{\{h:q_{i,e}^{\rm ref}(h)>0\}}
\frac{m_i(e,h)}{q_{i,e}^{\rm ref}(h)},
\tag{coverage-compute}
$$

provided $m_i(e,h)=0$ wherever $q_{i,e}^{\rm ref}(h)=0$. Here $m_i$ is measured from the original global prior. Indeed, $p_i^\beta(e,h)=\rho_i^\beta(e,h)m_i(e,h)$ and $0\le\rho_i^\beta\le1$. A positive $m_i$ on a reference-zero hand makes finite coverage impossible.

Multiplying (coverage) by nonnegative $d_{i,e}$, summing, and substituting in (local-global-residual) proves

$$
\begin{aligned}
\operatorname{Expl}_{\rm full}
&\le\operatorname{Expl}_{\rm trunk}
 +\frac12\sum_{i,e}\Lambda_{i,e}g_{i,e}^{\rm ref}\\
&\le\operatorname{Expl}_{\rm trunk}
 +\sum_e\max_i\Lambda_{i,e}\,\epsilon_e.
\end{aligned}
\tag{local-global-coverage}
$$

If reference and deployed conditional opponent ranges disagree, this theorem does not apply until that discrepancy is bounded, for example by (range-error), including its effect on both terms of a local gain. A bound on each of its two expected values by $\eta$ gives a conservative $2\eta$ gain allowance.

An alternative sufficient condition is a per-hand bound $d_{i,e}(h)\le k_{i,e}$ for all possible own hands, combined with certified bounds on deviation entry probabilities. Such a bound survives own-range shifts; an average under one posterior generally does not.

**Budget condition.** With local targets $\epsilon_e=0.005P_e$, the root target follows from these local tests only if

$$
\operatorname{Expl}_{\rm trunk}
+\sum_e\max_i\Lambda_{i,e}(0.005P_e)
+E_{\rm numerical}+E_{\rm model}
\le0.0075\ {\rm BB},
\tag{global-budget}
$$

or from a tighter proved version of (local-global-residual). Pots can grow and coverage ratios can be large. Replacing $\Lambda$ by ordinary self-play visitation has no general justification.

For multiple street frontiers, telescope disjoint replacements or apply the residual theorem recursively with correctly inherited ranges. A local turn certificate already concerns its complete turn-plus-river tail; its error is not automatically an additional independent river budget. One direct full-game BR test avoids this decomposition bookkeeping altogether.

##### P3.2.4. Counterexample: arbitrarily small local gap with fixed positive root gap

Consider a zero-sum toy game used only to test the proposed implication. Player 0 privately observes $H$ or $L$, each with probability $1/2$; player 1 has no decisions. Player 0 may Stop for zero or Enter. After Enter, type $H$ always gets zero; type $L$ can choose Bad for zero or Good for one.

The candidate always chooses Bad. Its trunk enters with probability one for $H$ and $\eta/(1-\eta)$ for $L$, where $0<\eta<1/2$. The Enter posterior assigns type $L$ probability $\eta$. Its local half-NashConv is therefore $\eta/2$, and the fixed-tail trunk gap is zero.

At the root, a full deviation enters and chooses Good whenever type $L$ occurs, earning $1/2$. The candidate earns zero and player 1's BR value is zero, so root half-NashConv is $1/4$, independent of $\eta$.

Thus local posterior gaps can approach zero while the root gap stays positive. The missing quantity is coverage of a private type made rare by the candidate's own upstream actions. This proves why a general streetwise composition claim needs the preceding assumptions. It does not assert that this toy payoff structure is an extra branch of R1.

#### P3.3. A separate safe-replacement condition uses per-hand counterfactual BR bounds

There is another sufficient condition for replacing solved tails. Keep all opposing policies outside a disjoint frontier fixed. For each player $i$, compute old and replacement tail BR vectors in the **same global CF units**, including original chance and the fixed opponent prefix reach but excluding player $i$'s own prefix action reach:

$$
c_{i,e}^{\rm new}(h)
\le c_{i,e}^{\rm old}(h)+\eta_{i,e}(h),
\qquad \eta_{i,e}(h)\ge0.
\tag{safe-CF}
$$

These vectors are computed with the already derived BR kernels. They are not just expected values under one normalized posterior.

Each $c_{i,e}$ is a BR vector against the opponent's tail policy; changing the responding player's own deployed tail does not change that vector.

For any fixed deviating trunk strategy, the change in its best-response payoff is at most

$$
\sum_{e,h}\rho_i^\beta(e,h)\eta_{i,e}(h).
$$

Maximizing through the trunk gives $\Gamma_i$, again using own-max and opponent/chance-sum with $\eta$ as already-scaled frontier CF rewards. Thus

$$
B_i^{\rm new}\le B_i^{\rm old}+\Gamma_i,\qquad
\operatorname{Expl}(\sigma^{\rm new})
\le\operatorname{Expl}(\sigma^{\rm old})
+\frac{\Gamma_0+\Gamma_1}{2}.
\tag{safe-global}
$$

If all residuals are zero, these replacements cannot increase exploitability. For both players' policies to be replaced, verify (safe-CF) separately for each potential responding player against the replacement of its opponent's policy. Overlapping/nested replacements need sequential recomputation or a proved telescoping allowance.

This is a checkable sufficient condition for safe refinement, not a claim that an independently computed local equilibrium automatically satisfies it. The general dependence of imperfect-information continuation solutions on outside information is also the issue addressed by subgame-solving research [S].

#### P3.4. A range-dependent equilibrium oracle cannot be treated as an ordinary leaf

For each boundary range pair, the local zero-sum value is

$$
V_e(b_0,b_1)=
\max_{\tau_0}\min_{\tau_1}
\frac{\sum_{x,y}M_{B_e}(x,y)b_0(x)b_1(y)
W_{0,e}^{(\tau_0,\tau_1)}(x,y)}
{Z_e}.
$$

Each fixed-profile numerator is bilinear in the factors. Optimization can change the selected strategies as either range changes; normalization adds its own nonlinearity. This scalar is therefore not a range-independent terminal payoff in the original EFG.

Even an exact scalar $V_e$ lacks the per-hand action/deviation information required by a parent's CF regret and BR. A sound interface returns range-indexed strategies and unnormalized CF/BR vectors, and a sound global algorithm preserves all original legal deviations or proves a replacement bound. Simply calling SolveRiver → SolveTurn → SolveFlop → SolvePreflop once, passing scalars upward, is not a solution method for this imperfect-information game.

The exact baseline derived here instead uses one full tabular strategy within a solve scope, the already explicit linear evaluation kernels, simultaneous DCFR updates, realization-weighted averaging, and the actual scope's BR gate. The street order describes dependencies and backward evaluation, while equilibrium is obtained by iteration.

---

## Implementation and proof obligations at each street root

The following table makes the terminal conditions of the dependency hierarchy explicit.

| Required root | Boundary assumptions | Complete solve scope | Required certification leaves |
|---|---|---|---|
| R0: river $\le0.005P_e$ | Full public history; five-card board; compatible fixed $\mu_e$; $P_e=2C_e$ | All river betting histories | Exact fold/showdown contractions and enclosed legal BR values |
| T0: turn $\le0.005P_e$ | Four-card board; compatible fixed $\mu_e$; $P_e=2C_e$ | Turn and every ordinary river continuation | River evaluation for current-profile regrets; river BR for certification; exact forced one-card runout |
| F0: flop $\le0.005P_e$ | Sorted flop; origin flag; compatible fixed $\mu_e$; $P_e=2C_e$ | Flop, turn, and river | Compatible turn transports; complete suffix BR; exact two-stage all-in runout |
| P0: preflop $\le0.0075$ BB | Original labeled-seat private deal; posted entry pot 1.5 BB | Entire R1 EFG | Exact preflop automaton, all ordinary suffixes, all forced runouts, full-game BR upper bound |

For every returned certificate, retain:

- The precise full-history entry, source/version hashes, monetary units, and entry pot.
- Boundary range factors or a general joint prior, their supports, scale convention, and positive normalization enclosure.
- The exact returned policy, including zero-average-row fallback behavior, and its content identifier.
- DCFR parameters, iteration-index convention, number of completed iterations, and averaging weights.
- Both BR upper/lower enclosures, the resulting half-NashConv upper bound, and the factor-of-two convention.
- Numerical, range, chance, and continuation allowances actually used, with their derived propagation. For an exact full-scope BR, there is no omitted-tail allowance.
- Whether the claim is a local fixed-range certificate, a verified refinement under a stated condition, or the original preflop game certificate.

A time or memory limit can end computation with a candidate and a failed/unmet gate. It cannot turn that candidate into a certified solve.

### Exactness checks needed by an implementation

The derivation permits direct, meaningful comparisons against the provided kernel:

1. Compare full legal action menus and successor descriptors against the EFG/kernel, including aliases that merge after half-up, minimum enforcement, and snapping.
2. Check the preflop table and all ordinary exit menus; verify that the two matched-28 prefixes remain separate learned rows.
3. Check private-pair and board support masks and exact rational normalization; verify each called-all-in scheduler.
4. Compare integer packed best-five ranks with the kernel's lexicographic tuples, including wheel, ties, board-only best hands, and categories with competing five-card subsets.
5. Check net terminal settlements, conservation of final stacks, and no chance after folds.
6. On small complete subtrees, compare pair-value contraction with the compact $F$ recurrence, and compare legal BR against enumeration of infoset-consistent pure responses where feasible.
7. Check that own reach affects averaging but not the immediate CF regret; check that compact opponent/chance backups do not multiply probabilities twice.
8. Verify the interval/radius implementation on cases with known exact rational answers. Check reported upper bounds rather than relying on agreement between two floating-point runs.

These checks validate an implementation of the derived operators. They do not replace its final strategic BR certificate.

## Source binding and validation status

**Historical record:** The source identities and reported checks below come from
preparation of this derivation. See [source provenance](../provenance.md) for
current file locations and validation guidance.

The attached game sources used for this derivation have these SHA-256 digests:

| Source | SHA-256 |
|---|---|
| EFG.md | 0f3bfd197e79ed3d5520c776af320149a8a0d9e36ce201e0a07e7123d3e639c7 |
| kernel.py | dcb9d3f0f5ed2ac401816606af1643a50a4d7c3ebcfbfa15b6c59125082c20c2 |
| preflop.json | 135ca851c5db7d0db237422b3e6943ad7b9374b9d2130f54e874f590e277216a |

A fresh lightweight artifact check during preparation confirmed that the delivered JSON equals the kernel's complete preflop expansion and that its integrated exact-card demo completes. The 16/11/4 public preflop counts above were checked from that expansion. The supplied full-suite log's hashes match these sources. That log records exhaustive reachable mechanics checks, physical five-card ranking checks, further semantic ranking classes, chance/infoset/runout checks, and its own pass result.

The full validation suite was not rerun for this document. As [E9] states, its mechanics quotient is a proof/validation device, not the EFG's information partition. Neither the supplied log nor the fresh lightweight check is an equilibrium certificate. No GPU implementation or DCFR training result is claimed by this derivation.

### References

- **[E1]–[E10]**: the correspondingly numbered sections of the user-supplied **hunl_r1/EFG.md**, the governing generative specification.
- **[K]**: user-supplied **hunl_r1/kernel.py**. Mechanics: raw_targets, resolve, actions, step, _settle, advance_board. Exact game: chance_events, chance_probability, deal, play, infoset_key, payoff. Ranking: _rank_five_unchecked, evaluate. Preflop export: preflop_tree.
- **[J]**: user-supplied **hunl_r1/preflop.json**, the full preflop public adjacency export.
- **[C]**: Martin Zinkevich, Michael Johanson, Michael Bowling, and Carmelo Piccione, [Regret Minimization in Games with Incomplete Information](https://papers.neurips.cc/paper_files/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf), NeurIPS 2007. Source for the CFR framework and counterfactual-regret decomposition.
- **[D]**: Noam Brown and Tuomas Sandholm, [Solving Imperfect-Information Games via Discounted Regret Minimization](https://arxiv.org/pdf/1809.04040), AAAI 2019. Source for the DCFR discount family and conventional $(3/2,0,2)$ parameters. This document explicitly fixes its own before/after-storage indexing and derives the resulting averaging identity.
- **[S]**: Noam Brown and Tuomas Sandholm, [Safe and Nested Subgame Solving for Imperfect-Information Games](https://proceedings.neurips.cc/paper/2017/file/7fe1f8abaad094e0b5cb1b01d712f708-Paper.pdf), NeurIPS 2017. Context for why independently solved imperfect-information continuations need additional global conditions.
