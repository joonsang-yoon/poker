# Exact R1 vectorized tabular DCFR — derivation B

[DCFR index](README.md) · [Derivation request](derivation-request.md) · [R1 game specification](../r1-game-specification.md)

**Status:** One of [four peer solver designs](README.md#peer-derivations); none is preferred.

**Provenance:** Source-audit filenames, hashes, and reported runs are historical
records of the original bundle. See [source provenance](../provenance.md) for
current paths and the [validation guide](../../README.md#validation) for fresh
mechanics checks.

## Reading map

- [Contract and notation](#contract-scope-and-reading-order)
- [River](#river) → [Turn](#turn) → [Flop](#flop) → [Preflop](#preflop)
- [Historical source notes and validation scope](#source-register-and-validation-scope)

## Contract, scope, and reading order

**Objective.** Derive a solver and a verifiable stopping rule for the exact finite game in `hunl_r1.zip`, in the order **river → turn → flop → preflop**. For each specified ordinary street-entry solve $e$, the acceptance requirement is

\[
\boxed{\operatorname{Expl}_e(\bar\sigma)\le 0.005P_e.}
\tag{0.1}
\]

Here $P_e$ is the pot at that entry: $2C_e$ postflop and **1.5 BB preflop**. The preflop requirement is therefore **0.0075 BB per hand**, or 7.5 milli-BB per hand. The kernel's preflop completed-street pot field $P=0$ is a different quantity.

This is a mathematical and implementation specification, not a report that a DCFR solve has already attained (0.1). The supplied game validator was run successfully; no strategy tables or measured equilibrium certificate are supplied. Exact-card tabular storage for the entire game is enormous. Vectorization, tiling, and recomputation below preserve the game; they do not assert that the full solve fits on one GPU.

**Authority.** The [R1 game specification](../r1-game-specification.md) governs. The [reference kernel](../../hunl_r1/kernel.py) and [preflop tree](../../data/preflop-tree.json) are executable/reference realizations of that contract. Source references such as **[G1 §4.1]** identify sections of the supplied specification; the source register at the end identifies the exact files and primary methodological references. All game-specific equations and error proofs below are derived for this contract. No rules of a different poker abstraction are substituted.

**Assumptions.** Two players, SB $=0$ and BB $=1$, each start with 100 BB including their blinds. Throughout, $-i$ denotes the other seat $1-i$, not arithmetic negation. The physical deck is $\mathcal D=\{0,\ldots,51\}$; $D(x,y)$ below is a compatibility matrix, not that deck. There is no rake, ante, side pot, or external payoff adjustment. Chance is the exact physical-card law. Players use behavioral strategies with perfect recall and the exact full-history information partition. A local solve has fixed input boundary ranges throughout its iterations. Numerical approximations are admitted only with an explicit certification error bound. [G1 §§1–2, 7–8]

**Meaning of “subgame.”** A street entry with private cards hidden is generally not a single-history, perfect-information-root subgame. In this document it means a **public-entry continuation game**: root chance draws a compatible pair of private hands from the specified conditional joint distribution; all subsequent R1 rules and original full-history infoset identifiers are retained. Local certification is relative to this specified root distribution.

**Dependency discipline.** Each street chapter starts at its certificate, expands its immediate requirements, and recursively expands those requirements to scalar/integer/GPU operations. A reference to an earlier expanded requirement reuses its equations, not an unspecified solver. This is the direction of the derivation. Runtime evaluation goes in reverse dependency order. Equilibrium solving additionally repeats a forward-reach/backward-value/update loop; a single backward pass does not solve an imperfect-information game.

---

<a id="river"></a>

## 1. River: root requirement R — a BR-certified continuation with exploitability at most $0.005P_e$

Compare this street: [A](derivation-a.md#river) · B · [C](derivation-c.md#river) · [D](derivation-d.md#river) · [Reading map](#reading-map)

At an ordinary river entry $e$, the board is $B_e=(F_1,F_2,F_3,t,r)$, $F_1<F_2<F_3$, the completed matched commitment is $C_e<100$, BB acts first, current-street contributions are zero, and $P_e=2C_e$. The complete earlier transcript remains part of every descendant identifier. [G1 §§2.1, 3.1, 7]

The strict dependency hierarchy is:

| Requirement | Immediate dependencies expanded below |
|---|---|
| **R: certify $\operatorname{Expl}_e\le0.005P_e$** | A precise compatible root game R.1; a frozen output profile R.3; two response upper bounds R.2 and R.4; the export contract R.5 |
| **R.1: define the game being certified** | Boundary factors, joint normalization, full-history indices, exact masks |
| **R.2: calculate each best-response value** | Counterfactual prefix weights → infoset-consistent action reduction → terminal payoffs → best-five ranking; exact public tree |
| **R.3: produce the output profile** | Reach-weighted averaging → signed DCFR regrets → regret matching → counterfactual action values → R.2's evaluation primitives |
| **R.4: make the certificate rigorous numerically** | Outward error bounds → positive contractions/maxima → root BR upper bounds |
| **R.5: export a usable continuation** | Frozen policy, per-hand counterfactual values, response envelopes, ranges, and all normalization scales |

### R.1. The root certificate requires a precise range-conditioned game

#### R.1.1. Exploitability requires two fixed-opponent responses

For a normalized root distribution $\mu_e$ and a complete continuation profile $\sigma=(\sigma_0,\sigma_1)$, let

\[
u_i^e(\sigma)=\mathbb E_{\mu_e,\sigma}[u_i(z)],\qquad
b_i^e(\sigma_{-i})=\max_{\tau_i}u_i^e(\tau_i,\sigma_{-i}).
\]

The maximization ranges over legal, infoset-consistent behavioral strategies. Define the unilateral gain $g_i=b_i-u_i^e(\sigma)\ge0$, NashConv $=g_0+g_1$, and use the poker **half-NashConv** convention:

\[
\operatorname{Expl}_e(\sigma)
=\frac{g_0+g_1}{2}
=\frac{b_0^e(\sigma_1)+b_1^e(\sigma_0)}2.
\tag{1.1}
\]

The second equality uses the exact net zero-sum payoffs. A response value $b_i$ can be negative; do not clamp individual response values to zero. The sum is nonnegative in exact arithmetic. The opponent's **entire** policy, including every later continuation, stays fixed during a response calculation.

Under this convention, (0.1) bounds the **average** of the two gains. Each individual gain is at most $0.01P_e$; claiming that each is at most $0.005P_e$ would require a stronger test. The zero-sum game value $v_e^*$ satisfies

\[
-b_1^e\le v_e^*\le b_0^e.
\tag{1.2}
\]

Thus the interval has width $2\operatorname{Expl}_e$, and its midpoint estimates $v_e^*$ within $\operatorname{Expl}_e$. This scalar statement does not bound each private hand's continuation error.

#### R.1.2. The root distribution requires compatible boundary factors

Enumerate all physical unordered hands

\[
\mathcal H=\{(a,b):0\le a<b<52\},\qquad H=1326,
\]

in lexicographic order. Indices $x,y\in[0,H$) identify hands $h_x,h_y$. Define

\[
m_B(x)=\mathbf1[h_x\cap B=\varnothing],\qquad
D(x,y)=\mathbf1[h_x\cap h_y=\varnothing],
\]
\[
K_B(x,y)=m_B(x)D(x,y)m_B(y).
\tag{1.3}
\]

Let $r_0,r_1\ge0$ be **reach factors**, one per physical hand, not independently specified posterior marginals. Put

\[
Z_e=r_0^{\mathsf T}K_{B_e}r_1>0,\qquad
\mu_e(x,y)=\frac{K_{B_e}(x,y)r_0(x)r_1(y)}{Z_e}.
\tag{1.4}
\]

When the entry is induced by an upstream R1 profile, $r_i(x)$ is the product of that player's own earlier action probabilities along the exact public prefix, conditional on $h_x$. Chance and the opponent's actions are excluded. Because all compatible deals assign the same probability to a specified sequence of public reveals,

\[
\Pr(q,x,y)=c_qK_{B_q}(x,y)r_{0,q}(x)r_{1,q}(y),
\tag{1.5}
\]
\[
c_q=\frac1{\binom{52}{2}\binom{50}{2}}
\prod_{\text{revealed board blocks in }q}\frac1{d_{\rm block}},
\quad d_{\rm block}\in\left\{\binom{48}{3},45,44\right\}.
\]

Consequently $\Pr(q)=c_qZ_q$, and (1.4) is Bayes' rule for the public entry. This factorization follows because a player's earlier action depends only on that player's hand and the public observations available at that action. [G1 §§2, 7]

The actual marginal and opponent distribution are

\[
\mu_{e,i}(x)=\frac{r_i(x)d_i(x)}{Z_e},\qquad
d_i(x)=\sum_yK_{B_e}(x,y)r_{-i}(y),
\tag{1.6}
\]
\[
\Pr(h_{-i}=h_y\mid h_i=h_x,e)
=\frac{K_{B_e}(x,y)r_{-i}(y)}{d_i(x)}\quad(d_i(x)>0).
\]

In general $\mu_{e,i}\ne r_i/\sum_xr_i(x)$. Multiplying two posterior marginals and applying blockers again does not reconstruct the correct joint distribution.

Any nonnegative factors with $Z_e>0$ define a hypothetical local game. To describe **one common global R1 profile**, factors at different entries must also obey realization flow: an $i$-action multiplies $r_i$ by its one infoset policy, leaves $r_{-i}$ unchanged, and the $i$-action children sum to their parent factor. A chance reveal leaves both own-action factors unchanged and changes the compatibility mask. All shared ancestors must use the same policy. Arbitrarily chosen, unrelated local ranges do not meet this stronger requirement.

Positive rescaling of either factor leaves $\mu_e$ unchanged. It changes $Z_e$ and unnormalized counterfactual values, so the scales must be carried when returning values upstream. A correlated mixture of joint reaches need not admit (1.4); if such a prior is intentionally used, store its full $[H,H]$ matrix and use the general tensor formulas below. Do not silently force it into a product.

#### R.1.3. Exact information requires full public-history indices

Let $n$ identify a **complete public prefix** below $e$, including the fixed blinds, all earlier streets, every board reveal with its street, and every action's street, actor, kind, and finalized target. For the acting player $i$, a valid hand $x$ identifies exactly one infoset

\[
I_i(n,x)=(i,h_x,B_n,\operatorname{pub}(n)).
\tag{1.7}
\]

The opponent's private hand varies inside this infoset. Neither future cards nor opponent cards enter its key. The flop is sorted; turn and river retain their separate identities. There is no suit canonicalization, hand bucketing, or monetary-state merging. [G1 §7; G2 `observation`, `infoset_key`]

A mechanics cache may share the pure action-menu calculation for equal monetary descriptors. It may not share regret rows, strategy rows, average accumulators, reach records, or mutable continuation results between different prefixes. In particular, the two preflop routes reaching $C=28$, and a lead/call versus check/bet/call reaching the same commitment, remain separate.

#### R.1.4. Vectorization requires explicit axes and masks

The following are **logical shapes**. $N$ is the number of distinct public nodes in the scoped continuation; $N_D\le N$ counts decision nodes. $A=6$ is sufficient for padding: at most fold/call plus four river raise candidates; deduplication may reduce the actual count. An optional independent-entry batch axis $E$ can prefix every shape. A batch never mixes or sums different entries' regrets.

| Tensor/index | Shape and type | Meaning |
|---|---|---|
| `hand_cards` | $[H,2]$, integer | Exact physical pair $h_x$ |
| `hand_bits`, `board_bits` | $[H]$, $[N]$, uint64 | Bit $c$ represents physical card $c$ |
| `hand_ok` | $[N,H]$, Boolean | $m_{B_n}(x)$ |
| `pair_ok` | $[H,H]$, Boolean | $D(x,y)$; combine with board masks for $K_n$ |
| `actor`, `kind`, `C`, `c`, `level`, `delta` | $[N]$, with `c` $[N,2]$ | Exact public mechanics; separate from node identity |
| `action_ok`, `child`, `action_kind`, `target` | $[N_D,A]$ | Legal-action mask, exact child IDs and finalized action data |
| `infoset_ok` | $[N_D,H,A]$, Boolean | `hand_ok` AND `action_ok` for the acting seat |
| $\sigma,R,S$ | $[N_D,H,A]$, real | Policy, signed discounted regrets, average-policy accumulators |
| $\ell_i$ | $[2,N,H]$, real | Player $i$'s own action reach after entry $e$ |
| $\mu_e$ | $[H,H]$, real | Normalized root pair prior, seat 0 on rows |
| $\lambda_n$ | $[N]$, real/exact rational | Product of reciprocal board-chance denominators after $e$; 1 throughout river |
| $W_i$ | logical $[2,N,H,H]$ | Counterfactual pair prefix weights; form tiles on demand |
| $V_i,\mathcal B_i$ | $[2,N,H]$, real | Counterfactual policy values and BR values; definitions below |
| $Q_i$ | $[N_i,H,A]$, real | Counterfactual action values at nodes of player $i$ |
| $U_i^\sigma$ | logical $[N,H,H]$, real | Pair-conditioned fixed-policy payoff; optional alternative evaluator |
| five-card subset table | $[21,5]$, integer | All $\binom75$ subsets of seven positions |
| rank input / subset / counts | $[B_T,H,7]$, $[B_T,H,21,5]$, $[B_T,H,21,13]$ | $B_T$ is a tile of complete boards, not a betting node ID |

The same $V_i$ symbol below always means a counterfactual vector, while $U_i$ always means a conditional pair matrix. They have different normalization and different backward recurrences. Local-scale boundary exports receive a separate symbol $\mathcal F_i$ in R.5.

Board-local compact axes are an exact indexing optimization:

| Board size | Valid physical hands $H_B=\binom{52-\lvert B\rvert}{2}$ | Compatible opponent hands per valid own hand | Legal ordered pair count |
|---:|---:|---:|---:|
| 0 | 1326 | 1225 | 1,624,350 |
| 3 | 1176 | 1081 | 1,271,256 |
| 4 | 1128 | 1035 | 1,167,480 |
| 5 | 1081 | 990 | 1,070,190 |

A compact child hand axis needs an explicit gather/scatter map to the global hand IDs. No two physical hands become one row. Invalid rows are zero and never enter an action normalization or argmax. Invalid action lanes are zero for sums and $-\infty$ for maxima. Never multiply a zero mask by a NaN; select valid data before arithmetic.

### R.2. The certificate requires exact infoset-consistent best responses

#### R.2.1. A response requires counterfactual prefix weights

Fix a complete policy $\sigma$. Initialize $\ell_i(e,x)=1$ for every valid hand. At a player-$p$ edge $n\to na$,

\[
\ell_p(na,x)=\ell_p(n,x)\sigma_p(n,x,a),\qquad
\ell_{1-p}(na,x)=\ell_{1-p}(n,x).
\tag{1.8}
\]

At chance, own action reaches are copied, and chance probability enters $\lambda$, not $\ell_i$. Invalid child hands are masked separately. The full pair reach at $n$ is

\[
\Pi_n(x,y)=\mu_e(x,y)\lambda_nK_{B_n}(x,y)
\ell_0(n,x)\ell_1(n,y).
\tag{1.9}
\]

Orient $\mu_e^0(x,y)=\mu_e(x,y)$ and $\mu_e^1(x,y)=\mu_e(y,x)$, so $x$ always denotes the player being evaluated. The counterfactual weight omits that player's own reach:

\[
W_i(n,x,y)=\mu_e^i(x,y)\lambda_nK_{B_n}(x,y)
\ell_{-i}(n,y).
\tag{1.10}
\]

Root chance remains included: a standalone local game's $\mu_e$ is its fixed private-root chance distribution. It is incorrect to delete the own-hand prior from (1.10) without explaining the resulting row rescaling. Conversely, an upstream player's own **strategic** prefix reach must not be inserted into a global counterfactual weight. R.5 gives the exact conversion between these two contexts.

All $W_i\ge0$. A zero own action reach $\ell_i(n,x)=0$ does **not** make $W_i(n,x,\cdot)$ zero. This is why a traversal must retain branches the current player never chooses: a deviation can choose them.

#### R.2.2. A response requires hidden-hand reduction before action maximization

For terminal public node $z$, first compute the per-hand contraction

\[
\mathcal B_i(z,x)=\sum_yW_i(z,x,y)u_i^{\rm own}(z,x,y).
\tag{1.11}
\]

For internal nodes, traverse in reverse public-tree order:

\[
\mathcal B_i(n,x)=
\begin{cases}
\displaystyle\max_{a\in A(n)}\mathcal B_i(na,x),&\rho(n)=i,\\[2mm]
\displaystyle\sum_{a\in A(n)}\mathcal B_i(na,x),&\rho(n)=-i,\\[2mm]
\displaystyle\sum_{d\in\mathcal D(n)}\mathcal B_i(nd,x),&\rho(n)=c.
\end{cases}
\tag{1.12}
\]

In (1.12), opponent action probabilities and chance factors have **already been multiplied into the children's $W_i$**. Multiplying them again is an error. The last case will be used on earlier streets. At the river there are no future chance nodes.

Finally,

\[
b_i^e=\sum_x\mathcal B_i(e,x).
\tag{1.13}
\]

At a responder node, store one selected action $a^*(n,x)$, breaking exact ties by the first legal action in the kernel's deterministic action order. Selection depends on $n,x$, never on hidden opponent index $y$. The forbidden calculation is

\[
\sum_yW_i(n,x,y)\max_a U_i(na,x,y),
\]

which grants access to the opponent's hand. The permitted maximum is **outside** the hidden-hand contraction, as (1.11)–(1.12) enforce.

**Proof.** At a terminal, (1.11) is the conditional expectation multiplied by its counterfactual prefix mass. At an opponent or chance node, the already-weighted child supports partition that mass, so summation is exact. At an $i$-node, every underlying history with the same $n,x$ is the same infoset, has the same actions, and must choose one common distribution. Its objective is linear in that distribution, so an action maximizing the contracted value is optimal. Distinct later full transcripts never merge into one infoset, so optimal descendant choices are compatible. Backward induction over this **infoset-consistent** dynamic program proves (1.13). Perfect recall also ensures that the responder's earlier actions do not induce hidden-hand-dependent information unavailable in the key.

#### R.2.3. Terminal contractions require exact net payoffs

At a public decision, use the kernel's mechanics notation

\[
(s,p,C,(c_0,c_1),i_{\rm agg},\Delta),\quad
P=2C,\quad a=c_p,\quad f=c_{1-p},\quad R_{\rm stk}=100-C.
\tag{1.14}
\]

$P$ is fixed within a street. The live pot is $P+c_0+c_1$; the pot after a hypothetical call is $Q=P+2f$. A target $b$ pays $b-a$. $R_{\rm stk}$ is the maximum **street target**, not the remaining chips of an actor who has already contributed $a$.

If player $p$ folds, let $L=C+c_p$. The exact terminal utilities are

\[
u_p=-L,\qquad u_{1-p}=L.
\tag{1.15}
\]

The survivor's uncalled excess wager is returned economically. Using the faced target $f$, or the entire visible pot, as the folder's loss is wrong. A fold triggers no future board chance.

The payoff matrices in the next display use fixed seat axes: SB hand on rows, BB hand on columns. Counterfactual arrays instead orient $x$ as the evaluated player's own hand. Their terminal kernel is therefore

\[
u_i^{\rm own}(z,x,y)=
\begin{cases}
u_0(z,x,y),&i=0,\\
u_1(z,y,x),&i=1.
\end{cases}
\]

Apply this transpose whenever player 1's own-hand weights are contracted with a fixed-seat payoff or continuation matrix. Fold payoffs use the same convention, although their matrix is constant on compatible pairs.

At a closed river, add its matched street target $x_*$ once:

\[
C_*=C+x_*.
\]

For complete board $B$, compute the showdown sign

\[
J_B(x,y)=\operatorname{sgn}\bigl(\operatorname{rank}_7(h_x,B)
-\operatorname{rank}_7(h_y,B)\bigr).
\]
\[
u_0(z,x,y)=C_*J_B(x,y),\qquad u_1=-u_0.
\tag{1.16}
\]

Every terminal utility lies in $[-100,100]$ BB; ties give exactly zero. Final stacks are $100+u_i$ and sum to 200. These are net utilities from before posting blinds, including when solving a later street. Adding $C_e$ to both utilities would destroy zero-sum cancellation in (1.1). [G1 §8; G2 `payoff`]

A GPU fold contraction is a masked opponent-mass reduction times the signed scalar $L$. A showdown contraction is a tiled matrix-vector operation with kernel $C_*J_B(x,y)$, the exact pair mask, and the prefix weights from (1.10). No poker-equity black box is required.

#### R.2.4. Showdown payoffs require a complete best-five ranking primitive

The card integer $c\in\{0,\ldots,51\}$ has

\[
\operatorname{rank}(c)=\lfloor c/4\rfloor+2,
\qquad \operatorname{suit}(c)=c\bmod4.
\tag{1.17}
\]

For one hand and complete board, concatenate the two hole cards and five board cards. Check distinctness and legal card indices. Gather all 21 five-position subsets. For each subset, compute rank counts

\[
n_r=\sum_{j=1}^{5}\mathbf1[\operatorname{rank}(c_j)=r],
\qquad r=2,\ldots,14,
\]

the descending five-card rank list, and `flush = all five suits equal`. Test the following ten straight patterns: high card 5 has ranks $\{14,2,3,4,5\}$; high cards $h=6,\ldots,14$ have $\{h-4,\ldots,h\}$. A test succeeds only when all five listed ranks occur. Let `straight_high` be the largest successful high card, or zero. No other ace wrap is legal.

Construct the first matching category in this priority table, with descending kickers where indicated:

| Priority/category value | Condition | Six-component tuple, padded with zeros |
|---:|---|---|
| 8 | Flush and straight | $(8,\text{straight high},0,0,0,0)$ |
| 7 | One $n_r=4$ | $(7,\text{quad rank},\text{kicker},0,0,0)$ |
| 6 | One $n_r=3$, one $n_r=2$ | $(6,\text{trip rank},\text{pair rank},0,0,0)$ |
| 5 | Flush | $(5,r_1,r_2,r_3,r_4,r_5)$ |
| 4 | Straight | $(4,\text{straight high},0,0,0,0)$ |
| 3 | One $n_r=3$ | $(3,\text{trip rank},k_1,k_2,0,0)$ |
| 2 | Two ranks with $n_r=2$ | $(2,\text{higher pair},\text{lower pair},\text{kicker},0,0)$ |
| 1 | One $n_r=2$ | $(1,\text{pair rank},k_1,k_2,k_3,0)$ |
| 0 | Otherwise | $(0,r_1,r_2,r_3,r_4,r_5)$ |

Extract pair/trip/quad ranks by masked maxima over the 13 ranks; extract kickers by descending masked rank selection. There are only five cards in each subset, so all cases in the table are exhaustive and mutually resolved by priority. [G1 §8.1]

Pack tuple $t_0,\ldots,t_5$ into

\[
\operatorname{code}_5=\sum_{j=0}^{5}t_j15^{5-j}.
\tag{1.18}
\]

Every component is between 0 and 14; thus integer comparison equals lexicographic comparison, and the code is below $15^6<2^{24}$, safely inside int32. The seven-card score is the integer maximum over the 21 subset scores. It permits zero, one, or two hole cards, so a best board hand can tie. Suits never enter the tie-breaking tuple. An invalid hand/board lane gets a separate invalid mask and may use score $-1$; it is excluded from payoff reductions.

This construction is exactly the best-five definition, not a hand-strength approximation. The analogous five- and six-card evaluators use all $\binom{5}{5}=1$ or $\binom{6}{5}=6$ subsets; terminal hold'em comparisons use seven cards. Integer ranking and showdown signs have zero numerical approximation error if these operations are implemented correctly.

#### R.2.5. Ranking and chance support require exact blocker primitives

Represent a hand by `hand_bits[x] = (1 << a) OR (1 << b)` in uint64 and a board by the OR of its card bits. Then

\[
m_B(x)=[\operatorname{handbits}(x)\mathbin{\&}\operatorname{boardbits}(B)=0],
\]
\[
D(x,y)=[\operatorname{handbits}(x)\mathbin{\&}\operatorname{handbits}(y)=0].
\tag{1.19}
\]

Broadcast these Boolean tests over hand tiles. They implement (1.3) exactly. The flop's canonical sort is a serialization convention, not a random permutation or an additional chance factor. Caching a pure rank or payoff kernel by the cards on which it mathematically depends is permitted; using such a cache key as an infoset key is not.

#### R.2.6. The response action maximum requires the exact river tree

At an unopened river, raw opening targets are

\[
\{P/2,P,3P/2,R_{\rm stk}\}.
\]

This same menu applies to BB's lead and SB's bet after BB checks. At every facing-wager raise or re-raise, raw targets are

\[
\{f+\Delta,\ f+Q/2,\ f+Q,\ R_{\rm stk}\},
\qquad Q=P+2f.
\tag{1.20}
\]

First require $f<R_{\rm stk}$ and $i_{\rm agg}<K_3=R_{\rm stk}$. Resolve each raw rational $x=n/d\ge0$ independently:

\[
b_0=\left\lfloor\frac{2n+d}{2d}\right\rfloor,
\quad m=\begin{cases}1,&\text{unbet opening},\\ f+\Delta,&\text{raise},\end{cases}
\quad b_1=\max(b_0,m),
\]
\[
b=\begin{cases}R_{\rm stk},&C+b_1\ge100,\\b_1,&\text{otherwise}.
\end{cases}
\tag{1.21}
\]

Only then deduplicate and sort final targets. The order is **positive half-up → minimum → snap → deduplicate**. A raw sizing alias is not an action. An explicit all-in passes through the same pipeline. A minimum-clamped target above the remaining stack snaps back to the all-in target; it is not rejected. The finalized all-in may be smaller than a full minimum raise. Use integer/rational menu compilation, never binary floating-point rounding or ties-to-even. [G1 §§4.1–4.3]

An unopened BB node offers check plus these finalized bets. Its check passes to SB, whose check closes the street at matched target 0. A facing-wager node offers fold, call to $f$, and the finalized raises. A call closes immediately at $C_*=C+f$. Aggression to $b$ changes

\[
c_p\leftarrow b,\quad p\leftarrow1-p,\quad
i_{\rm agg}\leftarrow i_{\rm agg}+1,\quad \Delta\leftarrow b-f.
\tag{1.22}
\]

Append the exact finalized action token to the public transcript. If $f=R_{\rm stk}$, only fold/call remain. An uncalled jam is therefore a decision node followed by a response, not a terminal. [G1 §§3.2–3.4, 6]

**Redundant-cap proof.** At a facing state, aggressive targets are integers and each aggression strictly increases the previous target by at least one. Starting from zero postflop gives $i_{\rm agg}\le f$. Therefore $f<R_{\rm stk}$ implies $i_{\rm agg}<R_{\rm stk}=K_3$. Retain the formal cap guard; do not replace it by a smaller live raise cap. Every aggression increases a bounded integer target, and passive actions close or terminate, so the public recursion is finite.

Mechanics may be compiled on the CPU with exact integers/rationals and copied to GPU arrays. Alternatively use the same integer expressions in GPU kernels. Finalized actions are in kernel order: passive actions first, followed by increasing aggressive targets. Current contributions may use integer half-BB units; raw thirds on earlier streets still use rational numerators and denominators.

### R.3. The certificate requires a frozen reach-weighted average profile generated by DCFR

The profile checked by R.2 is the **averaged behavioral profile**, not the latest policy and not an average of root payoff matrices. R.3 expands how to construct it.

#### R.3.1. A valid average requires realization weights

At iteration $t=1,2,\ldots$, freeze $\sigma^t$, and let $\ell_i^t(n,x)$ be its own action reach from (1.8). With averaging exponent $\gamma=2$, set

\[
A_i^T(n,x,a)=\sum_{t=1}^Tt^2\ell_i^t(n,x)\sigma_i^t(n,x,a),
\quad D_i^T(n,x)=\sum_a A_i^T(n,x,a).
\]
\[
\bar\sigma_i^T(n,x,a)=
\begin{cases}
A_i^T(n,x,a)/D_i^T(n,x),&D_i^T(n,x)>0,\\
1/|A(n)|,&D_i^T(n,x)=0\text{ and }a\in A(n),\\
0,&a\notin A(n).
\end{cases}
\tag{1.23}
\]

All sums are over legal action lanes. Neither opponent reach, joint reach, nor the current chance reach replaces $\ell_i$. The root private-hand distribution is fixed throughout a local solve; a positive, fixed own-hand factor would cancel from (1.23), but a varying strategic prefix factor does not.

An exactly equivalent rescaled accumulator uses $S^0=0$ and

\[
S^t=\left(\frac{t}{t+1}\right)^2
\left(S^{t-1}+\ell_i^t\sigma_i^t\right).
\tag{1.24}
\]

Indeed,

\[
S^T=\sum_{t=1}^T\left(\frac{t}{T+1}\right)^2
\ell_i^t\sigma_i^t=A_i^T/(T+1)^2.
\]

Normalize either $A$ or $S$, not both. Adding the sample after discounting in (1.24) with the same index would give different weights. Direct $t^2$ accumulation is simplest to audit; the scaled form avoids avoidable growth.

**Why this average is correct.** Perfect recall gives every infoset a unique own-action sequence. Averaging its realization probabilities $x_i^t(s)$ with weights $t^2$ gives a feasible realization plan because sequence-flow constraints are linear. Taking the child/parent realization ratio yields exactly (1.23). Induction along own-action sequences proves behavioral realization equivalence. If a parent average realization is zero, every child is zero and the arbitrary legal fallback cannot change the averaged realization plan. An unweighted average of the behavioral rows lacks this property. [M1, Eq. (4), for the standard realization-weighted construction; the weighted extension follows from this argument.]

#### R.3.2. DCFR policies require signed regrets and regret matching

Initialize every valid regret lane $R^0(n,x,a)=0$. At the beginning of iteration $t$, define

\[
R_+^{t-1}=\max(R^{t-1},0),\qquad
s_R(n,x)=\sum_{a\in A(n)}R_+^{t-1}(n,x,a),
\]
\[
\sigma_i^t(n,x,a)=
\begin{cases}
R_+^{t-1}(n,x,a)/s_R(n,x),&s_R(n,x)>0,\\
1/|A(n)|,&s_R(n,x)=0\text{ and }a\in A(n),\\
0,&a\notin A(n).
\end{cases}
\tag{1.25}
\]

The positive part is used only for policy extraction. Stored negative regrets are retained. This is not CFR+ clipping.

Choose the standard DCFR parameters $(\alpha,\beta,\gamma)=(3/2,0,2)$. After computing the instantaneous regret $r^t$ below, form $T^t=R^{t-1}+r^t$ and apply

\[
R^t=\begin{cases}
\displaystyle\frac{t^{3/2}}{t^{3/2}+1}T^t,&T^t\ge0,\\[2mm]
\displaystyle\frac12 T^t,&T^t<0.
\end{cases}
\tag{1.26}
\]

The sign is the sign of the **new total $T^t$**, and the discount is applied **after adding** this iteration's regret. These explicit indexing choices remove a common off-by-one ambiguity. The general signed factors are $t^\alpha/(t^\alpha+1)$, $t^\beta/(t^\beta+1)$; (1.24) supplies the average-strategy discount. [M2, “Regret Discounting for CFR and Its Variants”]

#### R.3.3. Instantaneous regrets require counterfactual policy evaluation

Use (1.10) under the frozen current profile $\sigma^t$. At terminals set

\[
V_i^t(z,x)=\sum_yW_i^t(z,x,y)u_i^{\rm own}(z,x,y).
\tag{1.27}
\]

At an own decision, define action values and the policy value:

\[
Q_i^t(n,x,a)=V_i^t(na,x),\qquad
V_i^t(n,x)=\sum_{a\in A(n)}\sigma_i^t(n,x,a)Q_i^t(n,x,a).
\tag{1.28}
\]

At opponent or chance nodes, sum child vectors, exactly as in the corresponding cases of (1.12). Then

\[
r_i^t(n,x,a)=Q_i^t(n,x,a)-V_i^t(n,x).
\tag{1.29}
\]

Do not multiply (1.29) by the actor's own reach. Do not divide it by the varying compatible opponent mass. Counterfactual weighting is already in $W_i$. A fixed positive factor for one infoset may be removed from **all** of its iterations' regrets because regret matching is homogeneous; an iteration-dependent renormalization generally changes the algorithm.

To see why (1.27)–(1.29) are the CFR values, expand (1.27) over terminal descendants. The weight contains root chance, later chance, and every opponent prefix action, while the backward own-node mixtures supply all own actions after $n$. Forcing action $a$ changes only the first own mixture, giving $Q_i$. Subtracting the original mixture therefore equals the gain from the one-infoset counterfactual deviation. This is the standard counterfactual regret construction specialized to explicit hand axes. [M1, §3]

**Alternative conditional evaluator, with a different weighting convention.** For debugging or a frozen-policy continuation matrix, set $U_i(z,x,y)=u_i(z,x,y)$, and use

\[
U_i(n,x,y)=
\begin{cases}
\sum_a\sigma_0(n,x,a)U_i(na,x,y),&\rho(n)=0,\\
\sum_a\sigma_1(n,y,a)U_i(na,x,y),&\rho(n)=1,\\
\sum_d f_c(d\mid n,x,y)U_i(nd,x,y),&\rho(n)=c.
\end{cases}
\tag{1.30}
\]

Here axes are always SB hand $x$, BB hand $y$. The value excludes all prefix probabilities. Inserting it into $\sum_yW_i(n,x,y)U_i^{\rm own}(n,x,y)$, where $U_0^{\rm own}(n,x,y)=U_0(n,x,y)$ and $U_1^{\rm own}(n,x,y)=U_1(n,y,x)$, gives the same $V_i$ as (1.27)–(1.28). This identity follows by distributivity and is a useful independent check. The $U$ recursion multiplies edge probabilities; the $V$ recursion sums children whose prefix weights already include them. Mixing these conventions double counts reach or chance.

#### R.3.4. Reproducibility requires a complete initialization and update schedule

Use simultaneous full-tree updates as the specified schedule:

```text
compile the exact full-history public tree, hand IDs, masks, and legal action lanes
fix the entry prior mu_e and all exact monetary/chance data
set every valid R = 0 and S = 0; initialize legal policies uniformly
for t = 1, 2, ...:
    sigma_t = masked_regret_matching(R)          # freeze BOTH players
    forward all own reaches ell_0, ell_1 under sigma_t
    form W_i tiles from mu_e, chance prefixes, masks, and ell_-i
    backward evaluate V_0, V_1 under this same frozen sigma_t
    record every own-node Q and r = Q - sum_a sigma_t[a] * Q[a]
    S = (t/(t+1))^2 * (S + ell_actor * sigma_t) # sample OLD frozen policy once
    T = R + r
    R = signed_discount(T, t)                   # sign of T, after addition
    at the chosen check iterations:
        bar_sigma = masked_row_normalize(S), with specified zero-row fallback
        freeze this complete bar_sigma
        recompute opponent reaches under bar_sigma, never reuse sigma_t reaches
        run both infoset-consistent BR passes with outward bounds
        stop only when their outward half-sum is <= exact(P_e / 200)
```

Both players' regret increments must be completely computed before either player's next policy is exposed to the traversal. An alternating-update variant is possible, but it is a different documented schedule and must recompute the affected reaches/values; it is not implemented by racing in-place writes. Parallelize independent hand tiles, terminal contractions, and nodes on a dependency frontier; synchronize between forward/backward layers and iteration stages.

There are no regret or strategy rows at chance nodes, fold terminals, showdown terminals, or forced all-in runout nodes. Sparse storage may omit structurally impossible hands/actions, but may not prune legal histories just because their current strategic reach is zero. The average fallback is part of the actual policy and is included in global BR certification.

#### R.3.5. The loop has an exact-arithmetic convergence argument, not an iteration-count certificate

The following proof is included to expose what the DCFR update controls. It does not substitute for the measured BR stopping rule.

Fix an infoset with $A_I\le6$ actions and $|r_a^t|\le D_I$. A universal choice is $D_I=200$, since terminal utilities lie in $[-100,100]$ and normalized-root counterfactual mass is at most one. A tighter bound is $200\sup_t\sum_yW_i^t(n,x,y)$.

Let $\Phi_t=\sum_a(R_a^{t,+})^2$. Regret matching gives $\sum_aR_a^{t-1,+}r_a^t=0$. The scalar inequality

\[
((x+r)^+)^2\le(x^+)^2+2x^+r+r^2
\]

and a positive discount no greater than one imply

\[
\Phi_t\le\Phi_{t-1}+A_ID_I^2,
\quad R_a^{t,+}\le D_I\sqrt{A_It}.
\tag{1.31}
\]

The negative half-discount also gives $R_a^t\ge-D_I$ by induction. Because the negative discount is no larger than the positive discount for $t\ge1$, (1.26) implies

\[
r_a^t\le R_a^t-R_a^{t-1}+t^{-3/2}R_a^t.
\]

Multiply by $t^2$, sum, and use summation by parts:

\[
\sum_{t=1}^Tt^2r_a^t
\le T^2R_a^T-\sum_{t=1}^{T-1}(2t+1)R_a^t
+\sum_{t=1}^Tt^{1/2}R_a^t
\]
\[
\le D_I\sqrt{A_I}\,T^{5/2}
+D_I(T^2-1)
+\frac{D_I\sqrt{A_I}}2T(T+1)
\equiv L_I(T).
\tag{1.32}
\]

For completeness, perfect recall gives the counterfactual performance-difference identity against any fixed deviation $\tau_i$:

\[
u_i(\tau_i,\sigma_{-i}^t)-u_i(\sigma^t)
=\sum_{I\in\mathcal I_i}\pi_i^{\tau_i}(I)
\sum_a\tau_i(I,a)r_i^t(I,a).
\tag{1.33}
\]

It follows by replacing one own decision at a time from root to leaves and telescoping the downstream values. $\pi_i^{\tau_i}(I)$ is the deviator's own realization reach; opponent and chance factors are already inside $r_i^t$. It is constant across the summation over $t$. Therefore weighted external regret is bounded by the sum of positive maximal weighted counterfactual regrets.

Let $W_T=\sum_{t=1}^Tt^2=T(T+1)(2T+1)/6$. Realization equivalence of (1.23), bilinearity of expected utility in the two realization plans, and zero-sum cancellation yield

\[
\operatorname{Expl}_e(\bar\sigma^T)
\le\frac{\sum_{i=0}^{1}\sum_{I\in\mathcal I_i}L_I(T)}{2W_T}
=O(T^{-1/2}).
\tag{1.34}
\]

The game is finite, so exact full-tree iteration eventually meets any positive target. The bound can be extremely loose because the exact game has many infosets. Discounted stored positive regrets alone are not the weighted external regrets appearing in (1.33); do not report their sum as an exploitability certificate. Numerical trajectories require R.4's final response verification.

### R.4. A numerical certificate requires an upper bound on the exact BR of the exported policy

#### R.4.1. Certification requires an unambiguous normalized policy

Treat each exported nonnegative finite row weight as an exact binary rational and define the policy by exact division by that row's sum. This defines a valid mathematical behavioral strategy even if training used floating point. Use the declared uniform fallback for an exactly zero legal row. Enclose these exact ratios during certification. Both BR passes must evaluate this same policy interpretation and the same entry distribution.

Menu generation, card IDs, masks, best-five codes, and payoff signs are integer operations. Monetary amounts are exact rationals; they can be represented by integer half-BB units, with integral postflop matched commitments. Only probability products, divisions, reductions, and accumulated real values need numerical enclosures.

FP64 is a useful working precision, but “computed in FP64” alone is not a proof. One sufficient implementation uses outward-rounded intervals:

| Operation | Enclosure rule |
|---|---|
| Addition | $[l_1,u_1]+[l_2,u_2]=[\operatorname{down}(l_1+l_2),\operatorname{up}(u_1+u_2)]$ |
| Multiplication | Outward round the minimum and maximum of the four endpoint products |
| Division | Multiply by the outward reciprocal interval when the denominator interval has a strictly positive lower endpoint |
| Sum/reduction | Apply outward additions along the actual reduction tree |
| Maximum over legal actions | $[\max_a l_a,\max_a u_a]$ |
| Exact structural zero | $[0,0]$; exclude invalid lanes before arithmetic |

With correctly rounded scalar operations, directed rounding or one outward `nextafter` expansion of each rounded endpoint suffices for each primitive. The implementation must account for its actual fused operations and reduction order; unaccounted fast-math transformations are not covered by this statement. Initialize a rational chance probability or normalized weight with bounds containing its exact rational value. Handle underflow with exponent scaling or an explicit lost-mass bound.

Apply these rules to (1.10)–(1.13). At responder nodes, interval maxima certify the optimal value without requiring a numerically decisive choice between nearly tied actions. The maximum remains after the hidden-hand contraction. Let $b_i^+$ be the resulting upper endpoint of the root BR. Accept only if

\[
\boxed{\operatorname{up}\!\left(\frac{b_0^++b_1^+}{2}\right)
\le P_e/200.}
\tag{1.35}
\]

The threshold is the exact rational $P_e/200$; preflop it is exactly $3/400$ BB. If the comparison uses floating point, use a certified **downward** bound for the threshold and an **upward** bound for the final BR sum/division. A nearest-rounded decimal threshold alone is not sufficient for a strict certificate.

Equivalently, if an estimate $\widehat b_i$ has a proved absolute error $\eta_i$, use $(\widehat b_0+\widehat b_1+\eta_0+\eta_1)/2$. Do not subtract separately approximated on-policy values: their exact zero-sum cancellation already supplied (1.1). A negative purported upper bound indicates inconsistent bounds or arithmetic, not negative exploitability.

For a non-interval implementation, a standard elementary alternative is to track each reduction's roundoff. If the unit roundoff is $u$ and $mu<1$, define $\gamma_m=mu/(1-mu)$. Expanding a chain of $m$ rounded multiplications/additions gives a multiplicative factor within $1\pm\gamma_m$. Thus a length-$k$ sequential dot product satisfies the conservative bound

\[
\left|\operatorname{fl}\!\left(\sum_j a_jb_j\right)-\sum_j a_jb_j\right|
\le\gamma_{2k}\sum_j|a_jb_j|,
\tag{1.36}
\]

before adding uncertainty in the inputs. A balanced reduction can use its actual, shorter operation depth. The bound follows by multiplying the per-operation factors $1+\delta$, $|\delta|\le u$, and bounding their product; it assumes no unaccounted overflow/underflow. For $W\ge0$ and $|u_i|\le100$, $\sum_y|W_iu_i|\le100\sum_yW_i$. Track coefficient errors separately instead of relying on cancellation of positive and negative showdown terms.

#### R.4.2. Backward numerical errors propagate through positive mixtures and maxima

Define the exact counterfactual mass

\[
m_i(n,x)=\sum_yW_i(n,x,y).
\]

At a responder edge, $m_i(na,x)=m_i(n,x)$. At opponent or chance nodes,

\[
\sum_a m_i(na,x)=m_i(n,x).
\tag{1.37}
\]

For $m_i(n,x)>0$, divide the analytical value, not the training update, by this mass. The BR recurrence for $\mathcal B_i/m_i$ is a maximum at own decisions and a stochastic mixture with weights $m_{\rm child}/m_{\rm parent}$ elsewhere. If a local arithmetic operation contributes normalized error at most $\epsilon(n,x)$, its descendant error obeys

\[
E(n,x)\le
\begin{cases}
\epsilon(n,x)+\max_aE(na,x),&\rho(n)=i,\\
\epsilon(n,x)+\sum_a\frac{m_i(na,x)}{m_i(n,x)}E(na,x),&\rho(n)\in\{-i,c\}.
\end{cases}
\tag{1.38}
\]

**Proof.** For expectations, the absolute error of a weighted sum with nonnegative weights is at most the weighted sum of the absolute errors. For maxima,
$|\max_a v_a-\max_a\widehat v_a|\le\max_a|v_a-\widehat v_a|$.
Induct from leaves to the entry. Coefficient uncertainty is included in the local $\epsilon$ or enclosed directly by intervals.

Consequently a uniform terminal error $\delta$ and a per-operation-node bound $\epsilon_{\max}$ over at most $L$ visited levels give a coarse bound $\delta+L\epsilon_{\max}$. A sharper bound is the responder's largest expected accumulated local error. At exactly zero mass the unnormalized value is exactly zero; no division is taken. Tiny positive mass is not an exact zero.

The fixed-policy evaluation proof is identical with the responder maximum replaced by its policy mixture. Unnormalized recurrences remain preferable operationally because they never divide by a small reach merely to undo that division later.

#### R.4.3. Training error has a bounded update effect but no uniform policy-sensitivity bound near zero regret

For the same frozen policy and weights, suppose every action counterfactual value is perturbed by at most $\epsilon_Q$. Then the exact policy mixture is perturbed by at most $\epsilon_Q$, and each regret increment by at most $2\epsilon_Q$, plus the baseline reduction's own arithmetic error.

The signed discount map in (1.26) is continuous, piecewise linear, and globally Lipschitz with constant $\max(d_+,d_-)\le1$. Therefore, comparing two regret buffers driven by that same frozen policy sequence,

\[
\|\widehat R^t-R^t\|_\infty
\le\|\widehat R^{t-1}-R^{t-1}\|_\infty
+\|\widehat r^t-r^t\|_\infty+\epsilon_{\rm discount}^t.
\tag{1.39}
\]

This remains true across a sign change because both pieces meet at zero. It bounds the accumulated error in an update sequence, not the distance between two independently evolving strategy trajectories.

For nonnegative vectors $p,q$ with positive sums,

\[
\left\|\frac p{\|p\|_1}-\frac q{\|q\|_1}\right\|_1
\le \frac{2\|p-q\|_1}{\min(\|p\|_1,\|q\|_1)}.
\tag{1.40}
\]

Apply this to positive regrets or average-policy accumulators. There is no uniform bound as the denominator approaches zero: $(\varepsilon,0)$ and $(0,\varepsilon)$ yield opposite deterministic policies even as $\varepsilon\to0$. An average buffer with error $E_A$ and positive exact row sum $D_A$ admits the analogous $2E_A/D_A$ bound, or the symmetric denominator in (1.40). For reaches, telescoping products of factors in $[0,1]$ bounds absolute product error by the sum of the factor errors. These facts explain why final independent BR certification is needed even when training arithmetic errors are individually small.

#### R.4.4. Range normalization has its own error budget

For any two normalized pair priors $\mu,\nu$, fixed policy, or fixed opponent response problem,

\[
|u_i^\sigma(\mu)-u_i^\sigma(\nu)|\le100\|\mu-\nu\|_1,
\qquad
|b_i(\mu)-b_i(\nu)|\le100\|\mu-\nu\|_1.
\tag{1.41}
\]

The first inequality expands the expectation and uses $|u_i|\le100$. The second takes a supremum over the same legal strategy class and uses the maximum inequality from R.4.2. Applying both a supremum and an infimum proves the same bound for the zero-sum game value. For a fixed complete profile, half-NashConv changes by at most $100\|\mu-\nu\|_1$; an individual deviation gain has the conservative bound $200\|\mu-\nu\|_1$.

If $w,\widehat w\ge0$ have masses $Z,\widehat Z>0$ and $\xi=\|w-\widehat w\|_1$, then

\[
\left\|\frac wZ-\frac{\widehat w}{\widehat Z}\right\|_1
\le\frac{2\xi}{Z}.
\tag{1.42}
\]

To prove it, add and subtract $\widehat w/Z$ and use
$|Z-\widehat Z|\le\xi$ and $\|\widehat w\|_1=\widehat Z$.
The symmetric bound with $\widehat Z$ also holds. If all four factors $r_0,r_1,\widehat r_0,\widehat r_1$ have unit $\ell_1$ norm before masking,

\[
\|K\odot(r_0r_1^{\mathsf T}-\widehat r_0\widehat r_1^{\mathsf T})\|_1
\le\|r_0-\widehat r_0\|_1+\|r_1-\widehat r_1\|_1.
\]

Thus a very small compatibility normalizer can amplify conditional error. Retaining unnormalized counterfactual mass avoids falsely treating such a local sensitivity as large global probability. Input-range uncertainty must either be enclosed in $\mu_e$ or added through (1.41)–(1.42) to the stopping budget.

### R.5. A river continuation requires values that retain their range dependence

#### R.5.1. A parent requires a frozen-policy hand operator, not just one equilibrium number

For a **fixed complete continuation policy** $\sigma$, let $U_i^{\sigma,\rm own}(e,x,y)$ be the own-hand-oriented version of its pair-conditioned payoff from (1.30). Define the opponent-only counterfactual operator

\[
\mathcal F_i^\sigma(e,x;r_{-i})
=\sum_yK_{B_e}(x,y)r_{-i}(y)U_i^{\sigma,\rm own}(e,x,y).
\tag{1.43}
\]

The corresponding best-response operator $\mathcal G_i(e,x;r_{-i},\sigma_{-i})$ uses the same opponent factor and the max/sum recursion, omitting the responder's **entire prefix** reach. Its internal opponent reaches include all subsequent actions of the fixed opponent. Both outputs have shape $[H]$. The input pair-conditioned matrix has shape $[H,H]$; streaming terminal contractions can implement the operators without storing it at all nodes.

The exact conversions at an entry are

\[
V_i^{\rm local}(e,x)=\frac{r_i(x)}{Z_e}\mathcal F_i^\sigma(e,x),
\qquad
u_i^e(\sigma)=\frac1{Z_e}\sum_xr_i(x)\mathcal F_i^\sigma(e,x),
\tag{1.44}
\]
\[
b_i^e=\frac1{Z_e}\sum_xr_i(x)\mathcal G_i(e,x),
\qquad
v_i^{\rm global}(e,x)=c_e\mathcal F_i^\sigma(e,x).
\tag{1.45}
\]

The global expression excludes the player's own upstream action reach. These equations reconcile a local solver's fixed private-root prior with global CFR's counterfactual convention. Never divide a zero $r_i(x)$ out of a local value to recover a missing counterfactual export; compute (1.43) directly.

The same interface also splices correctly into an arbitrary local parent. If the parent entry is $e$ with fixed factors $r_i^e$, and a descendant $q$ has $r_i^q(x)=r_i^e(x)\ell_i(q,x)$, then

\[
V_i^{\rm parent}(q,x)=
\frac{\lambda_{e\to q}r_i^e(x)}{Z_e}
\mathcal F_i^\sigma(q,x;r_{-i}^q).
\tag{1.45a}
\]

By contrast, an independently rooted $q$-local game has root counterfactual value $r_i^q(x)\mathcal F_i(q,x)/Z_q$. The parent's own prefix factor $\ell_i(q,x)$ is absent from (1.45a). The same conversion applies to $\mathcal G_i$. Compute the opponent-only export directly; do not recover it by dividing a local value by a possibly zero own reach.

For fixed $\sigma$, $\mathcal F_i^\sigma$ is linear in the opponent factor. A reported conditional hand value is

\[
E_i^\sigma(e,x)=\mathcal F_i^\sigma(e,x)/d_i(x)\quad(d_i(x)>0).
\tag{1.46}
\]

This division is for reporting or conditional bounds. Dividing each iteration's regret update by the changing $d_i^t(x)$ changes its time weighting. Likewise, independently renormalizing evolving ranges and dropping their scale changes ancestor regrets.

#### R.5.2. An equilibrium continuation requires solving a range-parametrized game

An exact continuation value is

\[
v_e^*(r_0,r_1)
=\max_{\sigma_0}\min_{\sigma_1}
\frac{r_0^{\mathsf T}(K_{B_e}\odot U_0^\sigma)r_1}{Z_e}.
\tag{1.47}
\]

A DCFR call approximates this finite zero-sum range game and returns its **complete** average policies, $\mathcal F_i$, $\mathcal G_i$, exact entry identity, range factors/scales, and certificate (1.35). The minimax statement follows by representing strategies as compact convex realization-plan polytopes and observing that the payoff numerator is bilinear in those plans; no perfect-information optimization is substituted for the actual infosets.

The selected policy generally changes with both input ranges, so the **solved** continuation map is not the linear frozen-policy map (1.43). An accurate scalar $v_e^*(r_0,r_1)$ does not determine the two per-hand counterfactual vectors needed by a parent, and a small local exploitability does not bound every per-hand payoff or response error. A mistake on a hand of tiny root mass can have a large conditional gain while contributing very little to (1.1).

#### R.5.3. Zero-reach rules are part of the interface

| Situation | Required behavior |
|---|---|
| Structurally illegal hand/action/pair | Exclude it with exact masks; never create a policy lane for it |
| $Z_e=0$ under a nominated upstream profile | There is no Bayes-conditioned local game for that profile; do not divide or claim a conditional certificate |
| $r_i(x)=0$ but $d_i(x)>0$ | Retain the opponent-only values $\mathcal F_i,\mathcal G_i$ and the history; upstream deviations can restore own reach |
| $d_i(x)=0$ | Unnormalized opponent-only values are zero; a conditional value is undefined and may be stored as zero only with a zero-mass flag |
| $\ell_i(n,x)=0$ but $W_i(n,x,\cdot)\ne0$ | Still compute counterfactual regrets and BR values |
| All positive regrets zero | Uniform distribution over the exact legal actions |
| Average-policy row sum zero | Uniform legal fallback, included in any certificate of the complete policy |
| Floating-point underflow | Treat as numerical uncertainty or rescale; never silently declare structural impossibility |

In a standalone local game with a zero prior for one own hand, its ordinary local counterfactual regrets are zero. One may define an extension by omitting that fixed own-prior factor and updating from (1.43). On positive-prior rows this is merely a constant regret rescaling; on zero-prior rows it chooses extra behavior outside the local certificate's support. It does not certify that behavior for all changed upstream ranges.

---

<a id="turn"></a>

## 2. Turn: root requirement T — a BR-certified continuation with exploitability at most $0.005P_e$

Compare this street: [A](derivation-a.md#turn) · B · [C](derivation-c.md#turn) · [D](derivation-d.md#turn) · [Reading map](#reading-map)

At an ordinary turn entry $e$, $B_e=(F_1,F_2,F_3,t)$, $C_e<100$, $P_e=2C_e$, and BB acts with zero current-street contributions. The certified continuation includes **all remaining turn and river decisions**, all legal river cards, and all called-all-in runouts. [G1 §§2–4, 6]

The strict hierarchy is:

| Requirement | Immediate dependencies |
|---|---|
| **T: certify $\operatorname{Expl}_e\le0.005P_e$** | T.1's frozen full turn-plus-river profile and BR upper bounds; T.4's propagated errors |
| **T.1: generate and certify that profile** | R.3's exact DCFR schedule; T.2 values and T.3 legal children; complete river policies; turn BRs with river response operators |
| **T.2: obtain turn action values and BR leaves** | Turn terminal folds; exact closure; card-blocked river chance; frozen-policy or BR river operators, according to the pass |
| **T.3: generate legal turn children** | Turn raw menus → half-up → minimum → flop/turn snap → dedup; redundant cap and exact ledgers |
| **T.4: certify approximation propagation** | Uniform continuation/BR errors, chance weighting, and R.4 arithmetic enclosures |

### T.1. The target requires a complete frozen suffix policy and its two BRs

Use (1.4) as the turn entry prior and (1.1) as exploitability. Build the turn and all river descendants with independent full-history infoset rows. Run R.3's DCFR schedule over this **whole continuation**. During each iteration, river policies are simply the frozen current policies of that iteration; the river modules perform backward evaluation, not fresh equilibrium solving.

To certify the final turn profile, freeze its averaged turn and river policies, recompute opponent reaches, and apply R.2 with responder maxima at **both** streets. A river local-equilibrium scalar cannot replace a river best response against the actual frozen opponent.

If the river suffix is frozen externally and only turn regrets are updated, the procedure instead solves a restricted game in which that suffix cannot change. Its turn BR must still allow river deviations if the claim concerns the complete turn game. The difference is quantified by the local-to-global theorem in P.5.

### T.2. Turn values require an exact interface through river chance

#### T.2.1. Closure determines which continuation is required

At a turn fold, use (1.15) immediately. At a turn call or check-through, put $C'=C+x$ with $x=f$ or $0$ respectively. Then:

- If $C'<100$, schedule one river-card chance node; after its reveal enter a new river root with $C=C'$, $P=2C'$, BB acting, zero current contributions, and a distinct complete transcript.
- If $C'=100$, schedule one river-card chance node and then showdown at commitment 100. Instantiate no river betting node.

An all-in bet itself still leaves its opponent's fold/call response. Only the call creates the chance-only runout. [G1 §§2.4, 3.4, 6.3]

#### T.2.2. River chance requires pair blockers and the denominator 44

From a fixed turn board, enumerate the 48 public-card candidates $d\in \mathcal D\setminus B$. For a compatible private pair, exactly 44 remain legal. Define the tileable chance tensor

\[
\mathsf C_d(x,y)=\frac{\mathbf1[d\notin h_x\cup h_y\cup B]}{44},
\qquad\text{shape }[48,H,H].
\tag{2.1}
\]

Parent incompatibility is handled by $K_B$; do not divide by a zero mask. For every compatible pair,

\[
\sum_d\mathsf C_d(x,y)=1.
\tag{2.2}
\]

A conditional pair evaluator therefore uses

\[
U_i(q,x,y)=\frac1{44}
\sum_{\substack{d\notin B\cup h_x\cup h_y}}U_i(qd,x,y).
\tag{2.3}
\]

The counterfactual prefix-weight implementation instead sets
$W_i(qd)=W_i(q)\mathsf C_d$ and sums child $V_i$ or $\mathcal B_i$ without another $1/44$. An opponent-only boundary export $\mathcal F_i$ that excludes the prefix chance scalar uses

\[
\mathcal F_i(q,x)=\frac1{44}\sum_d\mathcal F_i(qd,x),
\tag{2.4}
\]

with child board masks inside each term. These are three compatible conventions with explicitly different stored quantities, not three interchangeable weighting rules.

For boundary reach factors after the closing action, let $Z_q=r_0^{\mathsf T}K_Br_1$ and $Z_{qd}=r_0^{\mathsf T}K_{B+d}r_1$. The public conditional card probability is

\[
\Pr(d\mid q)=\frac{Z_{qd}}{44Z_q},\qquad
\Pr(d\mid q,h_i=h_x)=\frac{d_i(qd,x)}{44d_i(q,x)}.
\tag{2.5}
\]

The first formula follows by summing the exact pair chance law against the joint prior; the second conditions additionally on the own hand. In particular, a public or single-player-visible deck count is not the dealer's denominator. After strategic filtering, public card marginals need not be uniform.

For a conditional hand value, (2.4) becomes

\[
E_i(q,x)=\sum_d\frac{d_i(qd,x)}{44d_i(q,x)}E_i(qd,x).
\tag{2.6}
\]

Do not multiply the unnormalized $\mathcal F_i(qd,x)$ by the public posterior in (2.5): that would normalize and weight the child twice.

#### T.2.3. A called-all-in leaf requires only ranking and chance

At a called turn all-in, the pair-conditioned SB payoff matrix is

\[
A_0(q,x,y)=\frac{100}{44}
\sum_{d\notin B\cup h_x\cup h_y}J_{B+d}(x,y),
\qquad A_1=-A_0.
\tag{2.7}
\]

Obtain each $J$ from R.2.4, block invalid pairs/cards, and reduce the 44 legal outcomes. No strategy, regret, averaging, or best-response action is present inside this runout. Its strategic exploitability is zero, while its expected payoff and numerical error remain part of the ancestor value.

#### T.2.4. A GPU implementation requires segmented card tiles

Use a chance-edge list with offsets `chance_offset[n]`, event card IDs, and one unique child public ID per event. At turn, a node has at most 48 public candidates before hand-pair masking. A card tile of size $B_C$ uses Boolean event masks $[B_C,H]$ and, only when needed, pair tiles $[B_C,H_{\rm row},H_{\rm col}]$.

Broadcast the event hand-validity mask over both pair axes; multiply exact $1/44$ into the forward chance scalar/weight once; gather the child's board-local hand rows; and reduce children by parent and own-hand ID. Exact blockers leave 44 legal event lanes per compatible pair. Strategies remain indexed by each actual river card and full transcript.

The backward arrays are $[2,N,H]$; the expensive pair work can be streamed at payoff or continuation boundaries. Do not materialize $[N,H,H]$ merely because it is a convenient logical shape. Tiling changes the reduction order, so its numerical bound must match that order.

### T.3. Turn children require the exact turn sizing and closure grammar

Turn opening raw targets are $\{P/2,P\}$ for both seats in their corresponding unopened contexts. Responding raw targets at every raise level are

\[
\{f+\Delta,\ f+Q/2,\ f+Q\}
=\{f+\Delta,\ C+2f,\ 2C+3f\}.
\tag{2.8}
\]

There is no extra turn jam candidate. After eligibility $f<R_{\rm stk}$ and $i_{\rm agg}<K_2=R_{\rm stk}$, compute half-up $b_0$ and minimum-clamped $b_1$ as in (1.21). Then

\[
b=
\begin{cases}
R_{\rm stk},&C+b_1\ge100\ \text{or}\ 3(C+b_1)>200,\\
b_1,&\text{otherwise}.
\end{cases}
\tag{2.9}
\]

Deduplicate only after the snap. The inequality is strict: at $C=30$, a clamped target 36 stays 36, while 37 snaps to 70. These are resolver probes, not additional policy sizes. The minimum full raise remains an explicit candidate. Record the actual finalized increment $b-f$, including a short all-in. [G1 §4]

All passive actions, actor changes, and redundant-cap reasoning are as in R.2.6; street closure now invokes T.2 instead of immediate showdown. The cumulative commitment is updated once, and its new value is not also re-added when the river starts.

### T.4. Turn certification requires continuation-error propagation, not nominal river exploitability

Suppose a frozen-policy river matrix used at a public boundary $f$ obeys

\[
|\widehat U_i(f,x,y)-U_i(f,x,y)|\le\delta_f
\tag{2.10}
\]

for every compatible pair. Then the corresponding opponent-only hand error is bounded by

\[
|\widehat{\mathcal F}_i(f,x)-\mathcal F_i(f,x)|
\le d_i(f,x)\delta_f.
\tag{2.11}
\]

This is just the triangle inequality applied to nonnegative opponent weights. For one river card layer, (2.3) gives

\[
|\widehat U_i(q,x,y)-U_i(q,x,y)|
\le\frac1{44}\sum_{\text{legal }d}\delta_{qd}.
\tag{2.12}
\]

For BR certification, the approximation must cover **every allowed continuation deviation against the fixed opponent**, or directly enclose the true per-hand BR operator. Accuracy of the on-policy matrix alone does not constrain a response that changes river actions.

More generally, let $\mathcal Q$ be a public frontier antichain: a play reaches at most one of its entries. If $\delta_f$ is a uniform valid continuation error for the response problem of player $i$, then

\[
|b_i-\widehat b_i|
\le D_i,\qquad
D_i=\sup_{\tau_i}\sum_{f\in\mathcal Q}
\Pr_{(\tau_i,\sigma_{-i})}(f)\delta_f.
\tag{2.13}
\]

**Proof.** Every fixed response incurs expected error at most the displayed sum. Taking the maximum over the same response class on both sides changes the optimal value by no more than the largest such error. This is the maximum inequality of R.4.2. Because the cut is an antichain, $D_i\le\max_f\delta_f$; on-policy probabilities cannot replace the deviation probabilities in (2.13).

The supremum in (2.13) is itself computable by R.2's infoset-consistent DP: use the pair-conditioned payoff $\delta_f$ at each cut entry, contract by $W_i$ to initialize the scalar leaf as $m_i(f,x)\delta_f$, and maximize its expectation against the fixed opponent. Original terminal branches ending before the cut receive zero error cost. It is therefore not an unspecified optimization primitive.

With arithmetic/range errors bounded by $\eta_i$, the certified turn test is

\[
\frac{\widehat b_0+\widehat b_1+D_0+D_1+\eta_0+\eta_1}{2}
\le0.005P_e.
\tag{2.14}
\]

For a coherent zero-sum surrogate retaining the same feasible response class, with uniform payoff error $\delta$ at a single cut, both BR errors are at most $\delta$, so half-NashConv differs by at most $\delta$. NashConv can differ by $2\delta$, and an individual unilateral gain by $2\delta$. The same conclusion holds for a directly proved uniform approximation of the full BR operator. Merely replacing a suffix by an accurate fixed-policy matrix deletes suffix deviations and does not satisfy this premise. A scalar local river exploitability $\epsilon_f$ is not automatically the uniform payoff error $\delta_f$ required here.

---

<a id="flop"></a>

## 3. Flop: root requirement F — a BR-certified continuation with exploitability at most $0.005P_e$

Compare this street: [A](derivation-a.md#flop) · B · [C](derivation-c.md#flop) · [D](derivation-d.md#flop) · [Reading map](#reading-map)

At an ordinary flop entry, $B_e=(F_1,F_2,F_3)$ with increasing card IDs, $P_e=2C_e$, and BB acts after the flop has been revealed. The limp/check flag $L$ is true exactly when the complete preflop prefix is SB limp followed by BB check. The certified game contains all flop, turn, and river decisions and their exact chance descendants. [G1 §§3.1, 4.2, 5.3, 6]

The strict hierarchy is:

| Requirement | Immediate dependencies |
|---|---|
| **F: certify $\operatorname{Expl}_e\le0.005P_e$** | F.1's complete averaged profile; both full-suffix BRs; F.4's total numerical/continuation budget |
| **F.1: produce and certify the profile** | R.3 DCFR on the entire flop continuation; F.2 values and F.3 legal children; turn fixed-policy evaluation and BR operators |
| **F.2: obtain flop values** | Exact flop folds and closures → 45-way pair-legal turn chance → T's turn-plus-river operators, or a forced runout |
| **F.3: generate exact flop actions** | Origin flag → raw openings; universal responding raises → half-up/minimum/snap/dedup |
| **F.4: justify the certificate through two future streets** | Conditional chance contraction, compatible range flow, nested-error induction, and BR-uniform bounds |

### F.1. Flop equilibrium requires joint iteration across all its suffix decisions

Fix the flop boundary factors and the exact complete prefix. Initialize independent regrets and average accumulators for every legal flop, turn, and river infoset in this continuation. Use R.3's simultaneous schedule without changing the root prior during the solve.

A single iteration first forwards reaches from the flop entry; then evaluates river leaves and decisions, turn chance/decisions, and flop decisions backward. Only after both players' values are complete are all regrets discounted and the next policies formed. The flop root's average is not assembled from separately averaged local suffix solves with unrelated iteration weights or root ranges.

At a certification checkpoint, freeze the entire averaged profile and run both BR recurrences over all three streets. A certification traversal may reuse immutable card-rank and menu caches, but must rebuild the opponent reaches for that frozen profile.

### F.2. Flop values require the exact turn boundary and all-in runout

#### F.2.1. Turn chance is a 49-candidate masked contraction with denominator 45

After an ordinary flop closure at $C'=C+x<100$, enumerate the 49 card IDs absent from the public flop. For each compatible private pair, four more cards are blocked, leaving 45:

\[
\mathsf T_d(x,y)=\frac{\mathbf1[d\notin B\cup h_x\cup h_y]}{45},
\qquad\text{logical shape }[49,H,H].
\tag{3.1}
\]

The pair-conditioned continuation is

\[
U_i(q,x,y)=\frac1{45}\sum_{\text{legal turn }d}
U_i^{\sigma}(qd,x,y).
\tag{3.2}
\]

Each child is a separate full-history turn entry, retaining the particular flop action history that caused closure. Its monetary descriptor is $C=C'$, $P=2C'$, zero current-street contributions, and BB to act after the reveal.

Use the same three explicit conventions as T.2:

- Pair-conditioned $U$ multiplies $1/45$ in the backward chance sum.
- Prefix-weighted $V,\mathcal B$ multiply chance into child $W$ on the forward pass, then sum backward without an extra factor.
- Opponent-only exports $\mathcal F,\mathcal G$ without prefix chance use $1/45$ in their child sum.

For the public posterior,

\[
\Pr(d\mid q)=\frac{Z_{qd}}{45Z_q},\qquad
\Pr(d\mid q,h_i=h_x)=\frac{d_i(qd,x)}{45d_i(q,x)}.
\tag{3.3}
\]

Summing $Z_{qd}$ over all public candidates gives $45Z_q$ because every compatible private pair permits exactly 45 turn cards. This proves normalization without replacing the full-history dealer law by a player's visible deck.

#### F.2.2. Range flow through an action and reveal is explicit

Let $r_i$ be factors at the flop entry and let $\ell_i(q,x)$ be the player's own action product through the closing flop action. The factors for a legal turn child can be stored as

\[
r_{i,qd}(x)=r_i(x)\ell_i(q,x)m_{B+d}(x).
\tag{3.4}
\]

Including the mask in the factor is optional if it is retained in $K_{B+d}$. It does not change the compatible joint weights. There is no chance probability in the own-action factor; the $1/45$ belongs to the scalar chance reach. Normalize with the **joint** $Z_{qd}$ only when defining that child's local conditional game or reporting a conditional value.

When a complete-game DCFR iteration calls the turn evaluator, use the upstream unnormalized counterfactual weights. Do not reset own reach to one and renormalize the child as though starting an unrelated local solve. Resetting is appropriate only for a separately specified local game, whose outputs then need (1.44)–(1.45)'s scale conversion.

#### F.2.3. A called flop all-in has two labeled chance steps

When a flop closure gives $C'=100$, the remaining outcome is the ordered-by-street pair $(t,r)$ with $t\ne r$:

\[
A_0(q,x,y)
=\frac{100}{45\cdot44}
\sum_{\substack{t\notin B\cup h_x\cup h_y\\
r\notin B\cup h_x\cup h_y\cup\{t\}}}
J_{(B,t,r)}(x,y),\qquad A_1=-A_0.
\tag{3.5}
\]

Generate a turn reveal, then a river reveal, then showdown. The probability of one legal labeled outcome is $1/(45\cdot44)$. An unordered set $\{t,r\}$ is a different aggregated outcome and cannot retain this probability unchanged. The specified implementation keeps the labels. Skipped betting streets have ledger zeros, not artificial check/check action histories. [G1 §§2.4, 3.4, 6.3]

Vectorize by a turn-event tile and a river-event tile, applying hand/blocker masks before reductions. The rank kernel remains the same 21-subset best-five primitive. No player is allowed to condition an earlier action on a tile's unrevealed future card.

### F.3. Flop action values require the exact origin-dependent raw menu

Only the opening raw menu depends on the limp/check origin:

\[
\mathcal X_{\rm open}=
\begin{cases}
\{P/2,P\},&L=\text{true},\\
\{P/3,2P/3\},&L=\text{false}.
\end{cases}
\tag{3.6}
\]

This applies equally to BB's immediate bet and SB's bet after BB checks. On a reachable flop entry the special origin has $C=1$, but retain the complete prefix and the explicit flag; neither is an infoset merger.

At every facing state, use

\[
\mathcal X_{\rm raise}=\{f+\Delta,\ f+Q/2,\ f+Q\}.
\tag{3.7}
\]

The guard is $f<R_{\rm stk}$ and $i_{\rm agg}<K_1=R_{\rm stk}$. Use the same half-up/minimum/strict cumulative snap/dedup pipeline (2.9). No initiative, private hand, board texture, or seat-dependent sizing rule is added. No extra direct jam is added on the flop. [G1 §§3.3, 4]

Examples that pin down the order:

- At $C=28$, an ordinary flop's openings resolve to $\{19,37\}$ from raw $\{56/3,112/3\}$.
- After a bet to 19 at that entry, the three responding raw targets are $38,66,113$. The minimum candidate 38 has total commitment 66 and stays 38; the other two snap to $R_{\rm stk}=72$. The action set has **two** raise targets $\{38,72\}$, not three differently labeled choices.
- At $C=36$, raw openings $\{24,48\}$ resolve to $\{24,64\}$ because $C+48$ exceeds the strict flop/turn threshold.

These examples derive the actual menu from the general rules; they do not replace the recursive generation of all descendants. In every street, finalized aggressive increments are stored as $b-f$, and the redundant-cap proof remains valid.

### F.4. Flop certification requires nested error bounds and a fixed root prior

If turn and river approximations each introduce a separate local error, those errors can occur on the same path. Do not apply the “one leaf per antichain” bound independently and then pretend only one error was encountered.

For a finite collection of local approximation sources $\epsilon_q$, induction on (1.38) gives

\[
|\Delta b_i|
\le
\sup_{\tau_i}\mathbb E_{(\tau_i,\sigma_{-i})}
\left[\sum_{q\ \text{encountered}}\epsilon_q\right].
\tag{3.8}
\]

For fixed-policy values, remove the supremum and use the fixed policy's expectation. Include root-prior error through (1.41), arithmetic through R.4, and continuation approximation only when it is valid for the deviation class being certified. A coarse bound sums the largest allowed error at each remaining street layer; a sharper bound solves the corresponding nonnegative error-cost response problem.

The proof expands one recurrence at a time: each mixture averages its children's accumulated errors; each responder maximum selects an upper-bounding branch; the new local error adds once. The resulting path expression is exactly (3.8). Fold branches terminate the sum. Called-all-in branches contain only the remaining chance/evaluator errors.

If $b_i^+$ already encloses every such source, accept by (1.35). Otherwise add the separate proved terms before comparing with $0.005P_e$. Changing the boundary ranges during a local flop solve changes the game; the convergence argument (1.34) applies only to fixed local inputs. A global solve may have changing *descendant* reaches because it keeps one fixed preflop root and updates the whole policy together.

---

<a id="preflop"></a>

## 4. Preflop: root requirement P — a BR-certified complete R1 profile with exploitability at most 0.0075 BB

Compare this street: [A](derivation-a.md#preflop) · B · [C](derivation-c.md#preflop) · [D](derivation-d.md#preflop) · [Reading map](#reading-map)

The root requirement is

\[
\boxed{\operatorname{Expl}_{\rm R1}(\bar\sigma)
=\frac{b_0(\bar\sigma_1)+b_1(\bar\sigma_0)}2
\le0.005(1.5)=0.0075\ {\rm BB}.}
\tag{4.1}
\]

This is the certificate for the entire exact game. It includes all preflop private deals, all action histories, ordinary board reveals, folds, and called-all-in runouts. The initial private deal precedes any player action. [G1 §§1–2]

The strict hierarchy is:

| Requirement | Immediate dependencies |
|---|---|
| **P: certify (4.1)** | P.1's fixed private-root law and complete averaged profile; two global BR upper bounds; P.4–P.5's error/composition conditions |
| **P.1: generate and certify a complete profile** | R.3's one global DCFR loop; P.2 action/chance values and P.3 exact entry identities; full flop/turn/river policy and BR continuations |
| **P.2: obtain preflop values** | Exact 16-row betting tree → net folds or exact flop chance → F operators; called-jam chance-only payoff |
| **P.3: preserve exact entry identity** | Full preflop prefixes, 11 distinct ordinary flop exits, four jam/call exits, root blind accounting |
| **P.4: propagate numerical and continuation errors** | R.4 and the antichain/nested proofs T.4/F.4 using deviation reaches |
| **P.5: justify any local-to-global strategic bound** | Fixed-policy truncation, per-hand counterfactual response gaps, and deviation-weighted error-cost BRs |
| **P.6: implement and verify the resulting specification** | Explicit schedules, immutable-vs-mutable cache separation, source parity checks and a reproducible certificate record |

### P.1. The complete-game certificate requires the exact private-root distribution and one coherent policy

#### P.1.1. Root chance requires labeled seats and disjoint physical pairs

At the root, use $r_0=r_1=\mathbf1$, the empty-board compatibility mask $D$, and

\[
Z_{\rm root}=\binom{52}{2}\binom{50}{2}=1326\cdot1225=1,624,350,
\qquad
\mu_{\rm root}(x,y)=D(x,y)/Z_{\rm root}.
\tag{4.2}
\]

Equivalently, chance first selects an unordered SB pair uniformly and then an unordered BB pair uniformly from the remaining 50 cards. Seats are labeled; do not divide by two for exchanging them. Only the own hand is observed by each player. Invalid, overlapping, noncanonical, or out-of-deck assignments have probability zero. [G1 §2.2; G2, chance_events and chance_probability]

After this chance event, the betting state is

\[
s=0,\ p=\mathrm{SB},\ C=P=0,\quad
(c_0,c_1)=(1/2,1),\quad i_{\rm agg}=1,\quad\Delta=1.
\tag{4.3}
\]

The BB blind is aggression level 1 and the initial minimum increment is 1, not $1-1/2$. The actual entry pot is $P_e=1.5$ BB. The two quantities $P$ and $P_e$ remain distinct throughout the preflop chapter.

#### P.1.2. Global DCFR requires one common iteration and full-history tables

Apply R.3's initialization and update schedule to the whole tree with the fixed prior (4.2). At iteration $t$:

1. Freeze the current behavioral policy at **every** preflop, flop, turn, and river infoset.
2. Forward own realization reaches from the preflop root. Root chance remains in $\mu_{\rm root}$; public chance contributes the appropriate scalar product and masks.
3. Evaluate all terminal folds and showdowns, including chance-only all-in suffixes.
4. Reduce values in reverse dependency order: river, turn, flop, then the preflop tree. All continuation calls in this stage are fixed-policy evaluation calls.
5. Form every infoset's counterfactual regrets from that one frozen profile, average using the player's global own-action reach, then perform the signed DCFR updates.
6. At checkpoints, normalize the global average tables, freeze them, recompute both opponents' global reaches, and run full infoset-consistent BRs through **all** streets.

A local river/flop solver uses own reach starting at its local root. The global average instead includes that player's own earlier actions from preflop; these weights cannot be interchanged. Averaging child solve outputs separately and pasting them into the trunk generally does not produce the global realization average.

The river→turn→flop→preflop order is exact for backward evaluation, and useful for constructing these modules. It does not make the equilibrium problem a sequence of four independent scalar minimizations.

### P.2. Preflop values require the complete preflop action table and exact board chance

#### P.2.1. The authoritative preflop table fixes every action

In the following table, $L$ means the root action C1; $F_v$ is a terminal with SB net utility $v$ and BB utility $-v$; $E(C)$ means an ordinary flop deal retaining **this exact complete prefix plus its closing action**; $U$ means this prefix's called-all-in runout. The row prefix is the full public preflop action prefix, omitting only the fixed blind record and private deal. [G1 §5.2; G3]

| Full prefix | Actor | $(c_{\rm SB},c_{\rm BB})$ | $(i_{\rm agg},\Delta)$ | Passive successors | Final raise targets |
|---|---|---:|---:|---|---|
| Empty | SB | $(1/2,1)$ | $(1,1)$ | $F_{-1/2}$; $L$ to BB option | $2,3$ |
| $L$ | BB | $(1,1)$ | $(1,1)$ | $X\to E(1)$ | $4$ |
| $L,R_4$ | SB | $(1,4)$ | $(2,3)$ | $F_{-1}$; $C_4\to E(4)$ | $12$ |
| $L,R_4,R_{12}$ | BB | $(12,4)$ | $(3,8)$ | $F_{+4}$; $C_{12}\to E(12)$ | $28$ |
| $L,R_4,R_{12},R_{28}$ | SB | $(12,28)$ | $(4,16)$ | $F_{-12}$; $C_{28}\to E(28)$ | $100$, raw 60 |
| $L,R_4,R_{12},R_{28},R_{100}$ | BB | $(100,28)$ | $(5,72)$ | $F_{+28}$; $C_{100}\to U$ | None |
| $R_2$ | BB | $(2,1)$ | $(2,1)$ | $F_{+1}$; $C_2\to E(2)$ | $8$ |
| $R_2,R_8$ | SB | $(2,8)$ | $(3,6)$ | $F_{-2}$; $C_8\to E(8)$ | $22$ |
| $R_2,R_8,R_{22}$ | BB | $(22,8)$ | $(4,14)$ | $F_{+8}$; $C_{22}\to E(22)$ | $36,100$, raws 36, 50 |
| $R_2,R_8,R_{22},R_{36}$ | SB | $(22,36)$ | $(5,14)$ | $F_{-22}$; $C_{36}\to E(36)$ | $100$, raw 50 |
| $R_2,R_8,R_{22},R_{100}$ | SB | $(22,100)$ | $(5,78)$ | $F_{-22}$; $C_{100}\to U$ | None |
| $R_2,R_8,R_{22},R_{36},R_{100}$ | BB | $(100,36)$ | $(6,64)$ | $F_{+36}$; $C_{100}\to U$ | None |
| $R_3$ | BB | $(3,1)$ | $(2,2)$ | $F_{+1}$; $C_3\to E(3)$ | $11$ |
| $R_3,R_{11}$ | SB | $(3,11)$ | $(3,8)$ | $F_{-3}$; $C_{11}\to E(11)$ | $28$ |
| $R_3,R_{11},R_{28}$ | BB | $(28,11)$ | $(4,17)$ | $F_{+11}$; $C_{28}\to E(28)$ | $100$, raw 60 |
| $R_3,R_{11},R_{28},R_{100}$ | SB | $(28,100)$ | $(5,72)$ | $F_{-28}$; $C_{100}\to U$ | None |

This is 16 public decision rows and 45 player edges before card expansion. Every ordinary call closes preflop except the initial SB limp. BB's check after that limp closes at matched target 1. There is no fold/call at the BB check option.

Preflop raw candidates are exactly those that generate the table. Eligibility requires $f<100$ and $i_{\rm agg}<K_0=100$. Apply

\[
b_0=\operatorname{hu}(x),\qquad b_1=\max(b_0,f+\Delta),
\]
\[
b=\begin{cases}
100,&b_1\ge100\ \text{or}\ b_1>40,\\
b_1,&\text{otherwise},
\end{cases}
\tag{4.4}
\]

then deduplicate final targets. The raw targets 50 and 60 become 100. A clamped 40 would remain ordinary and 41 would snap, but these probes add no candidates to the table. After $R_{22}$ in the $R_2$ branch, $R_{36}$ is a genuine full raise with increment 14; its following raw 50 meets the minimum and then snaps.

Starting from $i_{\rm agg}=f=1$, the same integer-target argument gives $i_{\rm agg}\le f$ at every facing preflop state. The cap is therefore redundant when $f<100$, exactly as required by the source. The kernel's short internal route marker ("C",) after the limp, the JSON's C1, and the table's $L$ describe the same action; the full public transcript still stores the exact action kind and target. [G1 §§3.3, 5; G2, _PREFLOP_RAW and step]

#### P.2.2. Ordinary flop chance requires unordered triples and the denominator $\binom{48}{3}$

After any ordinary preflop closure, enumerate candidate public flops as sorted triples from the 52-card deck: $\binom{52}{3}=22,100$ candidates. For each compatible private pair, exactly
$\binom{48}{3}=17,296$ avoid all four hole cards:

\[
\mathsf F_F(x,y)=
\frac{\mathbf1[F\cap(h_x\cup h_y)=\varnothing]}{\binom{48}{3}},
\qquad \text{logical shape }[22100,H,H].
\tag{4.5}
\]

The fixed-pair continuation is

\[
U_i(q,x,y)=
\frac1{\binom{48}{3}}\sum_{\substack{F\subseteq \mathcal D\setminus(h_x\cup h_y)\\|F|=3}}
U_i^\sigma(qF,x,y).
\tag{4.6}
\]

The flop is unordered internally and serialized in increasing card order. There is no factor of $3!$. No burn-card histories exist. The hand-pair mask, not a player's observed cards alone, determines legal support. [G1 §§2.1–2.3]

Public and own-hand-conditioned flop probabilities are

\[
\Pr(F\mid q)=\frac{Z_{qF}}{\binom{48}{3}Z_q},\qquad
\Pr(F\mid q,h_i=h_x)=\frac{d_i(qF,x)}{\binom{48}{3}d_i(q,x)}.
\tag{4.7}
\]

Normalization follows because each compatible private pair appears in exactly $\binom{48}{3}$ legal flop candidates. A GPU tile holds flop card IDs $[B_F,3]$, flop bit masks $[B_F]$, hand-validity masks $[B_F,H]$, and only the needed pair blocks. Each candidate has its own public child ID, board observation, and policy table.

For regret evaluation use the frozen F.1 flop continuation. For a global response use its fixed-opponent, infoset-consistent BR continuation. Ordinary continuation values include all remaining betting; a preflop equity-only matrix would omit that game.

#### P.2.3. Called preflop all-ins require a complete labeled chance runout

After the call of a preflop jam, the legal remaining outcome is $(F,t,r)$ with sorted three-card flop $F$ and distinct labeled turn and river. The pair-conditioned payoff is

\[
A_0(x,y)=
\frac{100}{\binom{48}{3}\,45\,44}
\sum_{\substack{F\subseteq \mathcal D\setminus(h_x\cup h_y),\,|F|=3\\
t\notin F\cup h_x\cup h_y\\
r\notin F\cup\{t\}\cup h_x\cup h_y}}
J_{(F,t,r)}(x,y),\qquad A_1=-A_0.
\tag{4.8}
\]

Sequential flop, turn, and river chance nodes are normative. A fused iterator is equivalent only if it enumerates the same labeled outcomes with these product probabilities. Do not assign this probability to an unordered five-card set. No action is taken between these reveals; the final matched commitment stays 100; skipped-street ledger zeros do not create artificial betting histories. [G1 §§2.4, 3.4, 6.3]

No fold branch enters this iterator. No uncalled jam enters it. The immediate fold values in the table remain net contribution-based payoffs even when a large unmatched all-in wager is visible.

### P.3. Preflop certification requires preserving all distinct ordinary flop entries

These are the exact ordinary exits and resolved flop opening menus. Check is also available at an unopened root; the same opening targets apply after BB checks. All entries activate BB only **after** the scheduled flop reveal. [G1 §5.3]

| Complete closing prefix | $C$ | $P_e=2C$ | $R_{\rm stk}$ | $L$ | Resolved flop opening targets |
|---|---:|---:|---:|---|---|
| $L,X$ | 1 | 2 | 99 | True | $\{1,2\}$ |
| $L,R_4,C_4$ | 4 | 8 | 96 | False | $\{3,5\}$ |
| $L,R_4,R_{12},C_{12}$ | 12 | 24 | 88 | False | $\{8,16\}$ |
| $L,R_4,R_{12},R_{28},C_{28}$ | 28 | 56 | 72 | False | $\{19,37\}$ |
| $R_2,C_2$ | 2 | 4 | 98 | False | $\{1,3\}$ |
| $R_2,R_8,C_8$ | 8 | 16 | 92 | False | $\{5,11\}$ |
| $R_2,R_8,R_{22},C_{22}$ | 22 | 44 | 78 | False | $\{15,29\}$ |
| $R_2,R_8,R_{22},R_{36},C_{36}$ | 36 | 72 | 64 | False | $\{24,64\}$ |
| $R_3,C_3$ | 3 | 6 | 97 | False | $\{2,4\}$ |
| $R_3,R_{11},C_{11}$ | 11 | 22 | 89 | False | $\{7,15\}$ |
| $R_3,R_{11},R_{28},C_{28}$ | 28 | 56 | 72 | False | $\{19,37\}$ |

The two $C=28$ rows are distinct histories for every compatible private hand and flop. Each of the four jam/call routes likewise retains its own prefix, even though the forced-runout payoff calculation can reuse a pure card-equity kernel. A monetary continuation template is reusable arithmetic; it is not an information partition.

At all closures, add the matched current-street target to $C$ exactly once. Reset only the mechanics fields for the next street; never reset the public history. A pending-deal descriptor must expose chance, not future BB betting actions. [G1 §§3.4, 6–7; G2, _settle and advance_board]

### P.4. The root numerical budget must be in BB and include every approximated continuation

Apply (1.35) directly if the full BR traversal encloses the exact original game. This is the strongest and simplest final criterion: the realized strategy is certified regardless of the speed, heuristics, or roundoff of its training procedure.

If cut operators are approximated, let $D_i$ be the deviation-uniform continuation bound from (2.13) or the nested expected-sum bound (3.8), and $\eta_i$ cover the remaining arithmetic and root-prior uncertainty. Then require

\[
\boxed{\frac{\widehat b_0+\widehat b_1+D_0+D_1+\eta_0+\eta_1}{2}
\le0.0075\ {\rm BB}.}
\tag{4.9}
\]

All terms use net BB utilities, not percentages of different pots. A numerical allocation can reserve any nonnegative portions summing to 0.0075 for the computed gap and the two half-weighted error contributions; the actual proved quantities, not the allocated amounts alone, must pass (4.9).

A local target at a 56-BB entry is $0.28$ BB. This is far larger than $0.0075$ BB, and it is not automatically an admissible preflop error term. Even chance averaging cannot justify a bound based solely on the nominal profile's low probability of reaching that entry: a best response can change its own preceding actions and reach it more often. The following strategic composition theorem states the needed conditions.

### P.5. A local-to-global strategic guarantee requires deviation-compatible counterfactual bounds

#### P.5.1. Define the cut without splitting infosets or changing the opponent

Fix one complete profile $\sigma$. Let $\mathcal Q$ be an antichain of complete public histories, closed under both players' infosets: all compatible hidden deals for an entry belong to the same continuation collection. A trajectory reaches at most one entry of this cut. Distinct full public prefixes below the cut never share an infoset.

Construct a truncated **prefix game** that retains the original root chance and all prefix actions, but ends at $q\in\mathcal Q$ with the exact pair-conditioned payoff $U_i^\sigma(q,x,y)$ of the fixed suffix. Let $\eta_i$ be the unilateral gain in this prefix game against $\sigma_{-i}$, and let $\operatorname{Expl}_{\rm prefix}=(\eta_0+\eta_1)/2$. The on-policy root value is unchanged by this truncation.

For each entry and own hand, use the opponent's fixed prefix factor $r_{-i,q}^\sigma$ and define

\[
\Delta_i(q,x)=
\mathcal G_i(q,x;r_{-i,q}^\sigma,\sigma_{-i})
-\mathcal F_i^\sigma(q,x;r_{-i,q}^\sigma)\ge0.
\tag{4.10}
\]

The first term permits all legal suffix actions of player $i$; the second follows $\sigma_i$. Their counterfactual weights exclude the responder's own prefix actions. Compute these gaps even for hands whose nominal own prefix reach is zero.

For a prefix deviation $\tau_i$, let $r_{i,q}^{\tau_i}(x)$ be its own prefix realization factor. The opponent's policy remains fixed, so its prefix factor at the exact same observed history remains $r_{-i,q}^\sigma$. Define

\[
G_i(\tau_i)=
\sum_{q\in\mathcal Q}c_q\sum_x
r_{i,q}^{\tau_i}(x)\Delta_i(q,x).
\tag{4.11}
\]

For a fixed own hand and public transcript, the responder's prefix likelihood is a scalar common to every hidden opponent hand, so omitting it does not alter the opponent conditional distribution used in the suffix maximization. Different own hands and different complete cut histories have separate infosets, so their optimal suffix choices can be combined into a single feasible response.

#### P.5.2. The composition bound follows by separating a full deviation into prefix and suffix

For any full deviation, replace its suffix by $\sigma_i$ while preserving its prefix. The gain that remains is a feasible prefix-game gain, at most $\eta_i$. Allowing the best suffix back can add at most (4.11). Hence

\[
g_i^{\rm full}\le
\eta_i+\sup_{\tau_i^{\rm prefix}}G_i(\tau_i^{\rm prefix}),
\tag{4.12}
\]
\[
\boxed{\operatorname{Expl}_{\rm full}
\le\operatorname{Expl}_{\rm prefix}
+\frac{\sup_{\tau_0}G_0(\tau_0)+\sup_{\tau_1}G_1(\tau_1)}2.}
\tag{4.13}
\]

More precisely, the full best response maximizes the **sum** of its prefix value and its compatible suffix gain. The inequality uses $\max(f+g)\le\max f+\max g$; it can therefore be conservative but never relies on nominal reach probabilities.

The additional supremum is another explicit response DP. Place the already globally counterfactual-weighted vector $c_q\Delta_i(q,x)$ at each cut leaf, traverse prefix own nodes with a maximum, and opponent/chance nodes with a sum. Do not multiply their already incorporated prefix factors a second time. Sum over root hands. Original terminals reached without hitting the cut have zero gap cost. This returns $\sup G_i$. The same construction applies within a conditional parent entry using the local-parent scale specified in R.5.

This proof supplies the conditions often missing from informal “solve streets backward” arguments: one fixed opponent, complete public-history cuts, compatible boundary reaches, all own types, and a uniform value or response bound for every deviation included in the claim.

#### P.5.3. Per-hand bounds give an interpretable sufficient condition

Suppose for every compatible own hand, including nominal zero-own-reach hands,

\[
\Delta_i(q,x)\le d_i(q,x)\delta_{i,q}.
\tag{4.14}
\]

Then

\[
G_i(\tau_i)\le
\sum_q\Pr_{(\tau_i,\sigma_{-i})}(q)\delta_{i,q}.
\tag{4.15}
\]

This follows by substituting (4.14) into (4.11) and using
$c_q\sum_xr_{i,q}^{\tau_i}(x)d_i(q,x)=\Pr_{(\tau_i,\sigma_{-i})}(q)$.
For an antichain, the probabilities sum to at most one, giving

\[
\operatorname{Expl}_{\rm full}
\le\operatorname{Expl}_{\rm prefix}
+\frac{\max_q\delta_{0,q}+\max_q\delta_{1,q}}2.
\tag{4.16}
\]

The response DP in P.5.2 usually gives a tighter bound than separate maxima. For nested cuts, apply the same argument recursively or use the expected accumulated-gap construction corresponding to (3.8); count each source once.

A nominal local certificate controls

\[
g_i^q=
\frac{\sum_xr_{i,q}^\sigma(x)\Delta_i(q,x)}{Z_q^\sigma}.
\tag{4.17}
\]

It does **not** imply (4.14), nor does it control the same expression reweighted by $r_{i,q}^{\tau_i}$. For example, a large conditional mistake on a private hand of zero nominal entry mass contributes zero to (4.17), yet a changed earlier action can give that hand positive entry mass. A rare entry can also carry a large conditional error while contributing little to global on-policy value.

Even if the same frozen suffix profile's half-NashConv were bounded by $\epsilon_q$ **uniformly over all feasible unilateral induced entry ranges**, each directional gain would only be bounded by $2\epsilon_q$. Preserve this factor of two when deriving a bound from local exploitability. Separate solves that change the opponent policy for each queried range do not satisfy the fixed-opponent premise.

#### P.5.4. Safe local replacement can be checked using response envelopes

Suppose policies are replaced only below an antichain, while all prefix policies stay fixed. A sufficient safety condition is, for both responders and every compatible own hand,

\[
\mathcal G_i^{\rm new}(q,x)
\le\mathcal G_i^{\rm old}(q,x)+\zeta_{i,q}(x),
\qquad\zeta_{i,q}(x)\ge0.
\tag{4.18}
\]

The opponent prefix factors in these operators are the unchanged ones; the suffix opponent policies are the corresponding old or new policies. Monotonicity of the ancestor sums/maxima gives

\[
b_i^{\rm new}\le b_i^{\rm old}
+\sup_{\tau_i}\sum_qc_q\sum_x
r_{i,q}^{\tau_i}(x)\zeta_{i,q}(x).
\tag{4.19}
\]

**Proof.** Replace each cut BR vector by its old value plus the nonnegative envelope. Every feasible prefix response incurs at most the displayed added cost. Maximize and use the same max-sum inequality as in (4.12). Summing the two inequalities and dividing by two bounds the change in exploitability because net payoffs remain zero-sum.

The envelope cost is again evaluated by the explicit response DP, with zero cost on original terminals that do not reach the cut. Zero envelopes guarantee no increase in the two exact root BR values; numerical interval widths are a separate issue. If a locally trained replacement fails this condition, retain the previous profile or continue a global solve; its small local scalar exploitability alone does not authorize a mathematical claim of global improvement.

#### P.5.5. A single profile meeting all local targets requires additional local checks

The four street solvers above are callable for any specified valid entry distribution. If the desired output is **one complete profile** satisfying the local tolerance at every required on-policy entry as well as (4.1), freeze that profile and:

1. Recompute every required entry's reach factors from the same normalized exported average profile.
2. For each entry with $Z_q>0$, form its exact compatible conditional prior and certify the restriction of that same profile against both full-suffix BRs.
3. Apply its own threshold $0.005P_q$.
4. Independently certify the preflop root against the entire profile.

A small root exploitability alone does not guarantee all small conditional exploitabilities, because root error can concentrate on a rare entry. The collection of local tests alone does not guarantee the root bound for the reasons proved above. Zero-probability entries require a declared hypothetical prior or a counterfactual envelope such as (4.14)/(4.18); they have no Bayes-conditioned certificate under the nominal profile. A certificate using stale or approximate ranges must include their error through R.4.4.

### P.6. The derivation closes at implementable GPU operations and explicit verification obligations

#### P.6.1. Exact public compilation has no implicit state merger

Generate a prefix tree, with a distinct ID for each full public event sequence. A node record stores its parent ID and appended event, exact mechanics, board, kind, and outgoing edge offsets. Reconstructing or collision-checking the full sequence establishes identity; a hash of the monetary state is not an identifier.

The compiler's cases are exhaustive:

| Node kind | Enumerate | Successor construction |
|---|---|---|
| Private root chance | All disjoint ordered-seat hand pairs | Keep private cards on the two hand axes; expose only the acting player's hand in policy lookup |
| Preflop decision | P.2.1's exact row | Append actor/street/kind/final target; apply its explicit continuation or fold |
| Unopened postflop BB decision | Check and resolved opening bets | Check changes actor to SB; a bet creates a facing node and records actual increment |
| Checked-to SB decision | Check and the same resolved opening bets | Check closes at target 0; a bet creates a facing node |
| Facing wager | Fold, closing call, resolved raises | Fold settles existing own contribution; call closes; raise switches actor and updates target/level/increment |
| Ordinary pending deal | All legal next public blocks | Append the labeled reveal, then activate BB at reset current-street mechanics |
| Called-all-in runout | Same exact remaining public blocks | Append only chance reveals until showdown; create no player nodes |
| Terminal | No edges | Fold payoff or completed-board best-five showdown |

Public reveal candidates can be enumerated without holes and then masked per pair as derived above. Impossible pair/event combinations have zero probability. No legal public history is removed because its current strategy reach is small or zero. The actions, payoff, and observation construction provide an induction from the root proving that this expansion has exactly the source EFG's histories and infosets.

#### P.6.2. The primitive inventory is finite and fully specified

| GPU operation | Exact mathematical purpose | Reduction/broadcast axes |
|---|---|---|
| Integer card decode; bitwise AND/OR | Ranks, suits, private/public blockers | Card/hand and paired-hand tiles |
| Gather 21 subsets; count rank equalities; masked sort/max | Complete best-five evaluation | Five cards, 13 ranks, then 21 subsets |
| Integer comparison and signed scalar multiply | Showdown or fold net payoff | Own/opponent pair tiles |
| Rational-to-enclosed-probability conversion | Root and board chance | One scalar denominator per chance stage |
| Broadcast multiply | Own reaches, opponent counterfactual weights | Actor's hand axis, never an unseen-card policy axis |
| Masked matrix-vector/dot reduction | Sum over compatible opponent hands | Opponent axis first |
| Segmented sum | Opponent-action/chance backward evaluation | Children grouped by parent and own hand |
| Masked weighted action sum | Current-policy own-node value | Legal action axis |
| Masked action max/argmax | One BR action per exact infoset | Action axis after hidden-hand contraction |
| Subtract, signed scale, positive part, row normalization | Instantaneous regrets, DCFR, regret matching | Infoset/action lanes |
| Own-reach weighted add and row normalization | Realization-equivalent average strategy | Iteration accumulation, then legal action axis |
| Outward interval versions of arithmetic/reductions | Numerically valid BR upper bounds | Same axes and dependency order |

No step asks an unspecified evaluator, equilibrium oracle, posterior oracle, or BR oracle to supply a missing computation. The named evaluation/response modules are the recurrences already expanded in R.2–R.5, composed with the exact chance kernels of T.2, F.2, and P.2.

For $N_D$ decision nodes, dense policy/regret/average storage is proportional to $3N_DHA$ real numbers, before additional reaches and values. Counterfactual pair weights need not be retained at every node: derive them from the root prior, scalar chance prefix, masks, and opponent reaches on demand. Immutable monetary templates and card-ranking results may be reused; mutable infoset state remains full-history-specific. Board batching, deterministic tiled reductions, out-of-core tables, and recomputation are exact scheduling choices. Hand bucketing, suit-isomorphism merging, smaller raise caps, or replacing range-dependent continuations by fixed scalar equities would change the specified problem.

#### P.6.3. Semantic checks distinguish an implementation error from a solver convergence failure

An implementation of this derivation should establish the following before trusting a certificate:

| Check | Required result |
|---|---|
| Source preflop export | Exactly the 16 rows and 45 edges of P.2.1, including both $R_{36}$ and $R_{100}$ after $R_2,R_8,R_{22}$ |
| Initial passives | Root menu exactly fold/call-to-1/raise-to-2/raise-to-3; limp option exactly check/raise-to-4 |
| Final-target identity | All raw aliases that resolve to one target produce one action lane and one successor |
| Cap redundancy | Removing only the redundant cap test leaves reachable menus identical; adding a smaller cap is rejected as a different game |
| Root and board chance | Supports have the derived cardinalities and normalize exactly for each compatible pair |
| Rank kernel | Category priorities, wheel straight, kickers, shared-board ties, and all 21 subsets match the source's best-five definition |
| Payoff accounting | Root SB fold is $-1/2$; BB fold to either root raise is $-1$; ties are zero; final stacks sum to 200 |
| Axis orientation | Player 1's own-hand contraction uses the transpose of the fixed-seat payoff matrix |
| Reach bookkeeping | Child counterfactual masses satisfy (1.37); changing own upstream reach does not alter that player's global counterfactual weight |
| Evaluation parity | Pair-conditioned recursion (1.30) and counterfactual contraction (1.27) agree |
| Response consistency | One action per $(n,x)$; hidden opponent hand cannot affect its selection |
| History separation | Equal board/money with different earlier transcripts retains different infoset IDs |
| Averaging | Recurrence (1.24) equals explicit $t^2$ own-reach accumulation up to its common scale |
| All-in closure | No payoff before missing reveals, no later betting, and correct labeled-runout probability |
| Numerical acceptance | Stored normalized profile, ranges, exact game identity, and all error terms are the ones actually enclosed |

These are correctness obligations, not extra abstractions. A GPU implementation can test its elementary kernels against exact rational/CPU reference calculations on manageable fixtures while using the source's complete betting/card validation and the inductive arguments for the generative game.

#### P.6.4. A solver's acceptance record is concrete

For each certified scope, record the source hashes; complete entry prefix and board; $C_e$ and $P_e$; boundary factors and retained scales or exact joint prior; iteration count and update convention; exported policy/table identity; average-strategy weighting; both BR intervals; any separate range/continuation/roundoff bounds; the resulting upper exploitability; and the threshold.

Report **passed** only when the upper bound, not a point estimate or regret-buffer heuristic, is within the threshold. If the interval is too wide, refine the certificate computation or reduce the error source. If the true candidate gap is too large, continue solving or change the candidate and recertify. Neither a fixed iteration count nor the supplied game validator is an equilibrium certificate.

---

## Source register and validation scope

### Supplied normative and executable sources

**Historical record:** The source identities and reported checks below come from
preparation of this derivation. See [source provenance](../provenance.md) for
current file locations and validation guidance.

| ID | Archive member | Role and exact SHA-256 |
|---|---|---|
| **G1** | hunl_r1/EFG.md | Normative game. SHA-256: 0f3bfd197e79ed3d5520c776af320149a8a0d9e36ce201e0a07e7123d3e639c7 |
| **G2** | hunl_r1/kernel.py | Exact mechanics, chance, observations, best-five evaluator, and payoff implementation. SHA-256: dcb9d3f0f5ed2ac401816606af1643a50a4d7c3ebcfbfa15b6c59125082c20c2 |
| **G3** | hunl_r1/preflop.json | Complete exported preflop adjacency data. SHA-256: 135ca851c5db7d0db237422b3e6943ad7b9374b9d2130f54e874f590e277216a |
| **G4** | hunl_r1/validate.py, validate_betting.py, validate_cards.py | Independent factorized validation suite described by G1 §9 |

A fresh invocation of the supplied full validator completed with exit status 0 and **RESULT=PASS** during preparation of this document. It checked the independently generated reachable public mechanics closure, every root private deal, every physical five-card hand, the specified five/six/seven-card semantic evaluator classes, conditional chance supports on exercised residual decks, history/infoset separation, runout scheduling, payoff obligations, the preflop JSON export, and the integrated kernel demo. The universal support/evaluator conclusions use the exact compositional arguments stated in G1 §9.

This does not claim literal enumeration of every physical six- or seven-card holding or the full private-deal × board × betting-history product. It validates the supplied game under its stated factorized scope. No DCFR strategy was trained and no numerical exploitability result was measured for this derivation.

### Primary methodological references

- **M1.** Martin Zinkevich, Michael Johanson, Michael Bowling, and Carmelo Piccione, *Regret Minimization in Games with Incomplete Information*, NeurIPS 2007. [Official paper](https://proceedings.neurips.cc/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf). Reference for counterfactual regret and realization-weighted behavioral averaging. The tensor specializations, weighted telescoping calculations, and error proofs here are explicitly derived above.
- **M2.** Noam Brown and Tuomas Sandholm, *Solving Imperfect-Information Games via Discounted Regret Minimization*, AAAI 2019. [Authors' paper on arXiv](https://arxiv.org/pdf/1809.04040). Reference for the signed DCFR discounts and parameters $(3/2,0,2)$. Equations (1.24)–(1.26) fix the exact update indexing used here; R.3.5 gives the independent bound used in this document.

**Deliverable status:** a self-contained derivation of exact R1 vectorized tabular DCFR, its four street-specific certification requirements, and the conditions under which numerical and local continuation guarantees compose.
