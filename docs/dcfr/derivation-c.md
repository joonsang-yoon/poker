# Exact R1 vectorized tabular DCFR — derivation C

[DCFR index](README.md) · [Derivation request](derivation-request.md) · [R1 game specification](../r1-game-specification.md)

**Status:** One of [four peer solver designs](README.md#peer-derivations); none is preferred.

**Provenance:** Source-audit filenames, hashes, and reported runs are historical
records of the original bundle. See [source provenance](../provenance.md) for
current paths and the [validation guide](../../README.md#validation) for fresh
mechanics checks.

## Reading map

0. [Scope, assumptions, boundary distributions, and tensor contract](#0-scope-assumptions-boundary-distributions-and-tensor-contract)
1. [River: certificate → strategy → DCFR → values → exact primitives](#river)
2. [Turn: certificate → joint turn/river solving → continuation and river chance](#turn)
3. [Flop: certificate → joint flop/turn/river solving → turn chance and runouts](#flop)
4. [Preflop: certificate → full-game solving → exact table and private/flop chance](#preflop)
5. [Proofs of numerical and continuation-error propagation](#5-proofs-of-numerical-and-continuation-error-propagation)
6. [Conditions for local certificates to imply a global bound](#6-conditions-for-local-certificates-to-imply-a-global-bound)
7. [Historical source audit, references, and completion criteria](#7-source-audit-references-and-completion-criteria)

## Overview

*River → turn → flop → preflop, with best-response certificates*

**Deliverable type:** a mathematical and implementation-level derivation, not a claim that an equilibrium has been computed. The target at every specified public street entry $e$ is

\[
\boxed{\operatorname{Expl}_e(\bar\sigma_e)\le 0.005P_e.}
\]

All values and error budgets below are in **BB**, unless explicitly divided by the fixed entry pot $P_e$. Preflop $P_e=1.5$ BB, so its target is exactly $0.0075=3/400$ BB. At an ordinary postflop entry $P_e=2C_e$, so its target is $C_e/100$ BB. Neither the eventual pot nor a later street's entry pot replaces this normalizer.

**Authority.** The [R1 game specification](../r1-game-specification.md) governs the game. The [reference kernel](../../hunl_r1/kernel.py) is its executable reference, and the [preflop tree](../../data/preflop-tree.json) is the explicit preflop expansion. Citations of the form **[R1 §4.1]** refer to that governing specification; **[K: resolve]** refers to a kernel function. The original source fingerprints and a historically reported validation result are recorded in §7. No external poker rule, alternative sizing abstraction, or computational shortcut overrides R1.

**Central construction.** For a fixed boundary game, DCFR trains every descendant information set jointly. Within an iteration, strategies are frozen, reaches propagate forward, and values propagate backward in river → turn → flop → preflop order. Backward evaluation is not equilibrium solving. A river equilibrium solved for one pair of ranges is not a constant payoff that can simply be installed in every turn game.

---

## 0. Scope, assumptions, boundary distributions, and tensor contract

### 0.1 What is being solved

R1 is the finite, two-player, zero-sum, perfect-recall EFG specified in the attachment: 100 BB initially per player including blinds; SB/button posts $1/2$, BB posts $1$; no rake, ante, side pot, additional board, or suit tie break. We solve that action abstraction with exact physical cards and exact information sets. This is not a claim about exploitability in a larger action game. [R1 §§1–2, 7–8]

A **public entry** $e$ fixes the entire public transcript, including the blind record, all earlier finalized actions with their actors and streets, and every already revealed street-labeled board block. A postflop street entry is immediately after its board reveal and before BB acts. The preflop entry is the initial SB decision after the private deal. The local game has an artificial root chance draw of the two private hands from the specified joint boundary distribution; it then preserves every descendant R1 history and information set. It is a public continuation game, not a claim that one hidden underlying history forms a conventional singleton-root subgame.

Assumptions for the derivation are explicit:

1. A local normalized boundary distribution exists: $Z_e>0$, defined below. A zero-probability public event has no conditional posterior to certify without an additional specified distribution.
2. The action tree is generated without depth truncation, chance sampling, hand buckets, suit canonicalization, probability pruning, or merging distinct public histories. Batching and tiling may change execution order only.
3. The baseline uses full traversals and simultaneous updates. Both players use the same frozen iteration profile. Alternating updates would require a separately specified schedule.
4. The chosen DCFR parameters are $(\alpha,\beta,\gamma)=(3/2,0,2)$; these are algorithm choices, not R1 rules. Other parameters are not silently substituted.
5. Exact rational/integer rules define the game. Floating-point training is allowed; a numerical certificate must account for its own evaluation errors and must evaluate the actual normalized stored strategy.
6. Sufficient storage and execution time are assumed for a finite tabular calculation. Vectorization does not establish that the full card-expanded R1 tree fits a particular GPU or can be solved within a stated time.

### 0.2 Exploitability, units, and the certificate

For a strategy profile $\sigma=(\sigma_0,\sigma_1)$ in the fixed boundary game, let

\[
U_{i,e}(\sigma)=\mathbb E_{\mu_e,\sigma}[u_i],\qquad
\mathcal B_{i,e}(\sigma_{-i})
=\max_{\tau_i\text{ respects R1 infosets}}
U_{i,e}(\tau_i,\sigma_{-i}).
\]

The unilateral gain is $d_{i,e}=\mathcal B_{i,e}-U_{i,e}\ge0$. We use the common **half-NashConv** convention:

\[
\operatorname{NashConv}_e=d_{0,e}+d_{1,e}
=\mathcal B_{0,e}+\mathcal B_{1,e},\qquad
\operatorname{Expl}_e=\frac{\mathcal B_{0,e}+\mathcal B_{1,e}}2.
\tag{0.1}
\]

The equality uses $U_0+U_1=0$. Thus the stated target bounds the *sum* of unilateral gains by $0.01P_e$. It does not assert that each gain is at most $0.005P_e$. If that stronger convention is desired, additionally require $\max_i d_{i,e}\le0.005P_e$; report both gains so the factor of two is visible.

A genuine numerical certificate supplies **upper bounds** $\mathcal B_{i,e}\le\overline{\mathcal B}_{i,e}$ and accepts only if

\[
\boxed{\frac{\overline{\mathcal B}_{0,e}+
\overline{\mathcal B}_{1,e}}2\le0.005P_e.}
\tag{0.2}
\]

Evaluating a feasible response alone gives a lower bound on a best response. Small observed improvement, a small discounted-regret table, or a sampled response is not an upper certificate. Sections 1.2 and 5 construct the required upper bounds.

Utilities always remain the net utilities of R1. The uniform bound is $\lvert u_i\rvert\le100$ BB and payoff range at most 200 BB. After dividing by $P_e$, the bound is $100/P_e$, not universally one. Multiplying every payoff and regret in one fixed solve by the same positive constant preserves regret-matching probabilities; mixing normalizers between its descendant streets does not.

### 0.3 Exact observations and boundary-compatible ranges

Number seats $0=\mathrm{SB}$, $1=\mathrm{BB}$. In a player subscript, $-i$ denotes the opponent $1-i$, not a negative tensor index. The physical deck is $\mathcal D=\{0,\ldots,51\}$. Let

\[
\mathcal H_2=\{(c,d):0\le c<d<52\},\qquad H=|\mathcal H_2|=1326,
\]

with a fixed lexicographic hand-index map $h_x\leftrightarrow x\in[0,H)$. A public-node ID $v$ denotes a **complete public transcript**, never just a betting state. A decision information set is precisely

\[
I=(p(v),h_x,B_v,\operatorname{pub}(v)).
\tag{0.3}
\]

Because $v$ already stores the board and transcript, an implementation may index it as $(v,x)$, provided the exact key is preserved. Different opponent hands inhabit the same information set; different public histories do not. Equal pot sizes, equal boards, equal mechanics, equal hand strength, or suit isomorphism cannot share strategy, regret, average, or BR-decision rows. Read-only arithmetic templates and rank tables may be shared. [R1 §7; K: `infoset_key`, `observation`]

For the entry board $B_e$, define the exact compatibility matrix

\[
M_e(x,y)=\mathbf1[h_x\cap h_y=\varnothing]
\mathbf1[h_x\cap B_e=\varnothing]
\mathbf1[h_y\cap B_e=\varnothing].
\]

Let $a_0(x),a_1(y)\ge0$ be **range factors**, zero on board-invalid hands. We may normalize each factor to sum to one if it is nonzero. Define

\[
Z_e=\sum_{x,y}M_e(x,y)a_0(x)a_1(y),\qquad
\mu_e(x,y)=\frac{M_e(x,y)a_0(x)a_1(y)}{Z_e}.
\tag{0.4}
\]

These factors are not independent posterior marginals. For player $i$, write the opponent hand as $h_{-i}$ and define

\[
m_i(h_i)=\sum_{h_{-i}}M_e(h_0,h_1)a_{-i}(h_{-i}),\qquad
\mu_{i,e}(h_i)=\frac{a_i(h_i)m_i(h_i)}{Z_e}.
\tag{0.5}
\]

The matrix orientation is always SB on rows and BB on columns; an expression indexed first by $h_i$ means a transpose when $i=1$.

**Why this factorization is compatible with R1.** At an exact public transcript, each player's past behavioral-action likelihood is a function of that player's own hand and the public history. The root private-deal probability and the probabilities of the already observed labeled board are constant over compatible private pairs. Therefore conditioning on the transcript leaves precisely a blocker mask times the two action-likelihood factors. Their arbitrary positive rescalings cancel in (0.4).

For a *globally consistent* boundary, the factors must come from the same stored ancestor policies, and the complete ancestor transcript must be retained. Merely giving two plausible ranges or an arbitrary supported joint matrix does not prove that it is the posterior induced by that prefix. An arbitrary nonfactorizable joint prior can define another mathematical continuation game, but is not substituted for an R1-reachable posterior in this derivation.

If raw prefix likelihoods are $\ell_i=s_i a_i$, and $k_e$ is the exact root-deal/past-board chance factor for one compatible pair, then

\[
\Pr_\sigma(e)=k_e s_0s_1Z_e.
\tag{0.6}
\]

Normalization must retain those scales when recovering unconditional entry probabilities or global counterfactual values. If $Z_e=0$, do not invent a uniform posterior. The full-game counterfactual calculation can still have meaningful rows at that public history because it excludes the responding player's own reach.

### 0.4 Tensor contract and masks

Use global hand indices across streets; card-invalid entries are masked. Let $N$ be the number of public nodes in the chosen continuation tree, $N_D$ the number of its player-decision nodes, and $E_c$ its chance edges. Every descendant transcript gets a distinct node ID even if its mechanics are identical to another node's.

| Object | Shape / indexing | Meaning |
| --- | --- | --- |
| `hand`, `hand_bits` | $[H,2]$, $[H]$ | Canonical physical hole pairs and 52-bit masks |
| `kind`, `actor`, `parent`, `street`, `board_bits` | $[N]$ | Exact node/control metadata |
| `board` | $[N,5]$ plus board length | Sorted flop followed by labeled turn and river; unused slots masked |
| `child`, `legal`, `action_kind`, `target` | $[N_D,6]$ | Finalized player actions and padded successor IDs |
| chance CSR offsets, children, event cards | $[N+1]$, $[E_c]$, $[E_c,3]$ plus event length | All public next-block events, with pairwise legality masks |
| $A(v,x,a)$ | logical $[N_D,H,6]$ | Valid hand row and legal action slot |
| $R,S,\sigma,\bar\sigma$ | $[N_D,H,6]$ each | Signed discounted regrets, average accumulator, current and output policies |
| $r_i(v,h_i)$ | $[2,N,H]$ | Own-action reach from the chosen entry, excluding chance and opponent |
| $\chi_v(x,y)$ | conceptual $[N,H,H]$ | Entry root-chance mass and later board-chance factors, excluding both players |
| $V_i(v,h_i)$ | $[2,N,H]$ | Unnormalized counterfactual values |
| $G(v,h,a)$ | $[N_D,H,6]$, optional | Acting player's action CFVs |
| BR vectors and argmax actions | $[2,N,H]$, $[N_D,H]$ per responder | Independent response evaluation |
| `rank7` | $[B_5,H]$ | Integer best-five keys for distinct five-card board observations |
| terminal pair tiles | $[T_b,H_b,H_b]$, streamed | Exact payoff contractions over hand-pair tiles |

Here `B_5`, `T_b`, and `H_b` are batch/tile sizes, not strategic abstractions. Six player-action slots suffice: a river facing node has fold, call, and at most four resolved aggressive targets. An unopened river has at most check plus four bets. Chance uses a separate ragged edge axis; it never fits into the six-action axis.

Construct $A(v,x,a)=\mathrm{handvalid}(v,x)\land\mathrm{legal}(v,a)$. Illegal action slots are zero in policies, regrets, average sums, and ordinary reductions; they are $ -\infty$ in maxima. Maintain an explicit decision-row map $d(v)\in[0,N_D)$ for each public decision node; references to a decision tensor at $v$ mean row $d(v)$. Replace padded child IDs by a safe dummy index before gathering, then mask the gathered values; an index such as -1 must not alias a real last node. Every valid decision row has at least one legal action. Invalid hand rows are not information sets; return zero values and never perform an all-$-\infty$ maximum on them.

The conceptual $[N,H,H]$ chance tensor need not be materialized. At each public descendant it factors as the entry factors, its updated compatibility mask, the fixed entry normalization $1/Z_e$, and one scalar product of reciprocal board-chance denominators. This is an exact factorization of arithmetic, not state merging. Likewise, child CFVs can be streamed and their $G$ slots discarded after computing the regret increments.

| Fixed board length | Board-valid own hands | Compatible opponent hands per valid row | Ordered compatible seat pairs |
| ---: | ---: | ---: | ---: |
| 0 | 1326 | 1225 | 1,624,350 |
| 3 | 1176 | 1081 | 1,271,256 |
| 4 | 1128 | 1035 | 1,167,480 |
| 5 | 1081 | 990 | 1,070,190 |

The formulas are $\binom{52-b}{2}$, $\binom{50-b}{2}$, and their product. Compact board-specific hand axes are also possible, but each chance edge then needs an exact gather map to the global indices. No hand class may replace physical hand identity.

---

<a id="river"></a>

## 1. River: top-down derivation

Compare this street: [A](derivation-a.md#river) · [B](derivation-b.md#river) · C · [D](derivation-d.md#river) · [Reading map](#reading-map)

### R0 — Root obligation: a certified river continuation

For every specified river entry $e=(\operatorname{pub}(e),B_e,C_e,a_0,a_1)$, with five physical board cards, $C_e<100$, and $Z_e>0$, return a legal stored profile and prove

\[
\operatorname{Expl}_e(\bar\sigma)\le0.005(2C_e)=C_e/100.
\tag{R0}
\]

A called all-in arriving at a complete river board is already showdown; it has no river strategy table. Its continuation still needs the exact payoff calculation.

The following is a **strict tree of dependencies**, read from its root downward. Reused equations at a leaf are textual expansions of that leaf; they do not identify histories or share strategy rows. Temporal dependencies always refer to the previous iteration, so the iteration recurrence is not a same-iteration dependency cycle.

| Node | Parent | Required object / operation | Expansion |
| --- | --- | --- | --- |
| R0 | — | $\operatorname{Expl}_e\le0.005P_e$ | (0.2), R0 |
| R1 | R0 | Legal candidate $\bar\sigma$ | §1.1 |
| R1.1 | R1 | Reach-weighted average and zero-denominator rule | §1.1.1 |
| R1.1.1 | R1.1 | Frozen current policy from masked regret matching | §1.1.2 |
| R1.1.1.1 | R1.1.1 | Signed DCFR state from advantage updates | §1.1.3 |
| R1.1.1.1.1 | R1.1.1.1 | Counterfactual action and node values | §1.1.4 |
| R1.1.1.1.1.1 | R1.1.1.1.1 | Forward own reaches and chance/compatibility weights | §1.1.5 |
| R1.1.1.1.1.2 | R1.1.1.1.1 | Terminal contractions | §1.1.6 |
| R1.1.1.1.1.2.1 | R1.1.1.1.1.2 | Net fold/showdown payoffs | §1.1.7 |
| R1.1.1.1.1.2.1.1 | R1.1.1.1.1.2.1 | Exact best-five integer ranking | §1.1.8 |
| R1.1.1.1.1.3 | R1.1.1.1.1 | Exact river tree and masks | §1.1.9 |
| R2 | R0 | Two information-set-consistent BR upper values | §1.2 |
| R2.1 | R2 | Fresh opponent reaches and the same terminal primitives | §§1.1.5–1.1.8, instantiated independently |
| R2.2 | R2 | Max after hidden-hand reduction; proof of legality | §1.2 |
| R3 | R0 | Outward error bounds and exact stopping comparison | §1.3 and §5 |

### 1.1 R1 — Produce the candidate demanded by the certificate

#### 1.1.1 R1.1 — Derive the output strategy from realization weights

For a decision information set $I=(v,h_i)$, let $r_i^t(I)$ be the product of player $i$'s own action probabilities **before** $I$ in iteration $t$, starting at one at the selected entry. It excludes the opponent and all chance probabilities. Maintain $S^0(I,a)=0$, and after iteration $t\ge1$ use

\[
S^t(I,a)=\left(\frac{t}{t+1}\right)^2
\left[S^{t-1}(I,a)+r_i^t(I)\sigma_i^t(I,a)\right].
\tag{1.1}
\]

Repeated substitution gives, without an approximation,

\[
S^T(I,a)=\frac1{(T+1)^2}
\sum_{t=1}^T t^2r_i^t(I)\sigma_i^t(I,a).
\tag{1.2}
\]

Normalize each valid row:

\[
\bar\sigma_i^T(I,a)=
\begin{cases}
S^T(I,a)/\sum_{b\in A(I)}S^T(I,b),&\sum_bS^T(I,b)>0,\\
1/|A(I)|,&\sum_bS^T(I,b)=0,
\end{cases}
\tag{1.3}
\]

on legal actions, with zero elsewhere. The fallback is part of the returned complete policy, including off-path information sets. Do not divide by an arbitrary epsilon. No burn-in is assumed. To add one, its weights and all resulting averages must be explicitly redefined.

**Derivation of the reach factor.** Perfect recall gives each information set one own-action sequence. Its iteration-$t$ sequence realization probability is $r_i^t(I)$; extending that sequence by action $a$ gives $r_i^t(I)\sigma_i^t(I,a)$. Form the $t^2$-weighted mean of each sequence realization. The ratio of extended to parent mean realization is exactly (1.3). Induction through successive own decisions makes these ratios telescope. Thus the behavioral output implements the weighted mean realization plan. An arithmetic mean of behavioral action probabilities generally does not. Chance or opponent reach would average a different object.

A fixed positive own-hand prior factor can cancel from a row's numerator and denominator, but an iteration-dependent child posterior cannot be inserted. The forward reach calculation needed here is expanded in §1.1.5.

#### 1.1.2 R1.1.1 — Derive each frozen policy by masked regret matching

Initialize every legal regret entry at zero: $R^0(I,a)=0$. For iteration $t$, form

\[
R_+^{t-1}(I,a)=A(I,a)\max(R^{t-1}(I,a),0),\qquad
s_R(I)=\sum_aR_+^{t-1}(I,a).
\]

Then

\[
\sigma_i^t(I,a)=
\begin{cases}
R_+^{t-1}(I,a)/s_R(I),&s_R(I)>0,\\
A(I,a)/|A(I)|,&s_R(I)=0.
\end{cases}
\tag{1.4}
\]

GPU operations are elementwise maximum, Boolean mask multiplication, a six-slot row reduction, a positive-denominator branch, and rowwise division. Valid rows sum to one. Initial play is uniform over finalized legal actions, not raw sizing aliases. Regrets are signed; clipping all accumulated regrets to zero would define another algorithm.

#### 1.1.3 R1.1.1.1 — Derive the DCFR state update from CF advantages

For the actor $i=p(v)$, let $G_i^t(v,h_i,a)$ be the unnormalized counterfactual value of taking $a$ at $I$ and then following the frozen profile. Let

\[
V_i^t(v,h_i)=\sum_a\sigma_i^t(v,h_i,a)G_i^t(v,h_i,a),\qquad
\Delta R^t(I,a)=G_i^t(I,a)-V_i^t(I).
\tag{1.5}
\]

Form $Y^t=R^{t-1}+\Delta R^t$, then apply the discount according to the sign of **this updated value**:

\[
R^t(I,a)=
\begin{cases}
\dfrac{t^{3/2}}{t^{3/2}+1}Y^t(I,a),&Y^t(I,a)\ge0,\\[4pt]
\dfrac12Y^t(I,a),&Y^t(I,a)<0.
\end{cases}
\tag{1.6}
\]

Illegal slots stay zero. This specifies add-then-discount indexing completely. The general factors are $t^\alpha/(t^\alpha+1)$, $t^\beta/(t^\beta+1)$, and average discount $(t/(t+1))^\gamma$; the selected defaults are from the DCFR method of Brown and Sandholm [DCFR]. The negative factor is $1/2$, since $t^0=1$ for $t\ge1$.

Do not multiply (1.5) by the player's own reach: its absence is the counterfactual construction. Do not normalize it separately by an iteration-dependent opponent mass, subtree probability, or current pot. Such changes reweight iterations or information sets. A fixed positive scale per information set can be represented consistently only if its entire accumulated state and every new increment use that same scale.

The stored signed-discounted $R^T$ is **not** $\sum_t t^2\Delta R^t$. Dividing its positive entries by $\sum_t t^2$ is not an exploitability certificate. Section 5.7 gives the precise weighted-regret identity and explains the distinction.

#### 1.1.4 R1.1.1.1.1 — Derive CF values by a reverse linear sweep

First define a reference object to fix the semantics. $W_i^\sigma(v,x,y)$ is the expected **net terminal payoff**, conditional on already reaching public node $v$ with the compatible private pair $(x,y)$, following $\sigma$ thereafter. It includes no probability of reaching $v$. At a terminal $z$, $W_i(z,x,y)=u_i(z,x,y)$. At a player node,

\[
W_i(v,x,y)=\sum_a\sigma_{p(v)}(v,h_{p(v)},a)W_i(va,x,y).
\tag{1.7}
\]

There is no future board chance within an ordinary river betting tree. The earlier-street chance version is given in §2.3.

Given forward weights $\chi_v$ and own reaches $r_i$, define

\[
V_0(v,x)=\sum_y\chi_v(x,y)r_1(v,y)W_0(v,x,y),
\qquad
V_1(v,y)=\sum_x\chi_v(x,y)r_0(v,x)W_1(v,x,y).
\tag{1.8}
\]

These are **unnormalized CFVs**. In particular, neither expression divides by the probability of the information set.

Substitution of (1.7) into (1.8) gives a vector-only reverse evaluator. For a player node $v$ with actor $p$, gather its six padded child vectors and compute

\[
G_p(v,h,a)=V_p(va,h),\qquad
V_p(v,h)=\sum_a\sigma_p(v,h,a)V_p(va,h),
\tag{1.9}
\]

\[
V_{1-p}(v,h)=\sum_{a\in A(v)}V_{1-p}(va,h).
\tag{1.10}
\]

Why is (1.10) an unweighted sum? For player $1-p$'s CFV, the actor $p$ is the opponent. The child's forward opponent reach already contains $\sigma_p(v,h_p,a)$. Multiplying it again would square that probability. At the actor's own node this factor is excluded from the child CFV, so it must appear exactly once in (1.9).

At the selected entry, $r_0=r_1=1$ and $\chi_e=\mu_e$, giving

\[
U_{i,e}(\sigma)=\sum_{h_i}V_i(e,h_i).
\tag{1.11}
\]

Equations (1.8)–(1.10) prove that storing every pairwise $W$ is unnecessary for training. Compute terminal opponent-hand contractions, then reduce child vectors. It is legitimate to recompute a terminal tile when needed; it is not legitimate to replace distinct descendant strategy rows by one cached strategy.

#### 1.1.5 R1.1.1.1.1.1 — Derive forward reaches and exact blocker masks

Represent a set of physical cards by an unsigned 64-bit word. For hand $h_x=(c,d)$,

\[
b_x=(1\ll c)\lor(1\ll d),\qquad b_{B_v}=\bigvee_{c\in B_v}(1\ll c).
\]

Then

\[
\mathrm{handvalid}(v,x)=[b_x\mathbin{\&}b_{B_v}=0],
\quad M_v(x,y)=\mathrm{handvalid}(v,x)\mathrm{handvalid}(v,y)
[b_x\mathbin{\&}b_y=0].
\tag{1.12}
\]

No numerical threshold appears in compatibility. Card IDs are $0,\ldots,51$, and the bit operations are exact. A GPU pair tile forms masks by broadcasting row and column bit words and applying bitwise AND/equality.

At entry, set

\[
\chi_e(x,y)=\mu_e(x,y),\qquad r_i(e,h_i)=1
\]

on valid hand rows. Across an action edge $v\xrightarrow a w$ by player $p$,

\[
\chi_w=\chi_v,
\quad r_p(w,h)=r_p(v,h)\sigma_p(v,h,a),
\quad r_{1-p}(w,h)=r_{1-p}(v,h).
\tag{1.13}
\]

The actual joint reach is

\[
J_v(x,y)=\chi_v(x,y)r_0(v,x)r_1(v,y).
\tag{1.14}
\]

For player 0, counterfactual prefix mass uses $\chi_v r_1$; for player 1 it uses $\chi_v r_0$. Own reach zero does not imply counterfactual mass zero. Retain such branches in regret and BR sweeps. At a valid information set with zero **counterfactual** mass, all CF action values and increments are zero; the existing regrets still receive the specified discount, and the output policy still has a legal fallback.

GPU execution groups same-depth edges and performs gathers and elementwise products. Every public child has one parent, so no collision-prone reach accumulation is necessary. A new card reveal additionally masks invalid own-hand rows, as derived for turn/flop in §2.3.

#### 1.1.6 R1.1.1.1.1.2 — Reduce terminal hand pairs into CF vectors

For each terminal $z$, compute

\[
V_0(z,x)=\sum_y\chi_z(x,y)r_1(z,y)u_0(z,x,y),
\qquad
V_1(z,y)=\sum_x\chi_z(x,y)r_0(z,x)u_1(z,x,y).
\tag{1.15}
\]

This is a tiled masked matrix–vector contraction. To avoid materializing $\mu_e$, substitute

\[
\chi_z(x,y)=\frac{a_0(x)a_1(y)}{Z_e}M_z(x,y)
\]

for a river-rooted solve. Then, for example,

\[
V_0(z,x)=\frac{a_0(x)}{Z_e}
\sum_yM_z(x,y)[a_1(y)r_1(z,y)]u_0(z,x,y).
\tag{1.16}
\]

An earlier-street root adds the exact public-chance scalar to this expression. Row and column reductions use independent accumulators for the two players. A terminal fold payoff is constant across compatible pairs, allowing the same contraction with only the blocker mass. A showdown tile forms integer rank comparisons by broadcast, multiplies by the final matched commitment, masks illegal pairs, then reduces.

Never compute a player's best action for each $(x,y)$ before this reduction. The player does not observe $y$.

#### 1.1.7 R1.1.1.1.1.2.1 — Derive the exact net terminal payoffs

At a fold by player $p$, let $C$ be the contribution matched on completed streets and $c_p$ the folder's current-street contribution. The folder has lost exactly $L=C+c_p$, while the survivor's unmatched chips are returned economically. Therefore

\[
u_p=-L,\qquad u_{1-p}=L.
\tag{1.17}
\]

Using the faced target or the whole live pot as the winner's profit would change the game. For example, the initial SB fold is $(-1/2,+1/2)$, and BB folding to a root open is $(+1,-1)$.

At a showdown, let $C_*$ be the final matched contribution per player, after adding the closing street exactly once. With best-five integer keys $k(B,h)$,

\[
u_0=C_*\bigl([k(B,h_x)>k(B,h_y)]-[k(B,h_x)<k(B,h_y)]\bigr),
\qquad u_1=-u_0.
\tag{1.18}
\]

A tie is exactly zero; a called-all-in showdown uses $C_*=100$. These are net changes from the original stacks before blinds, so final stacks $100+u_i$ sum to 200. There is no additional sunk-cost subtraction at a subgame boundary. [R1 §8; K: `payoff`]

#### 1.1.8 R1.1.1.1.1.2.1.1 — Expand best-five ranking to integer GPU operations

For each seven-card holding $h_x\cup B$, gather the fixed list of the $\binom75=21$ increasing five-position subsets. For each gathered five-card vector $c_1,\ldots,c_5$:

1. Map to ranks $q_j=\lfloor c_j/4\rfloor+2\in\{2,\ldots,14\}$ and suits $s_j=c_j\bmod4$.
2. For each rank $r=2,\ldots,14$, form the count $n_r=\sum_{j=1}^5[q_j=r]$ and presence bit $b_r=[n_r>0]$. This is a $[\text{batch},21,5,13]$ equality broadcast and five-slot reduction, or an equivalent integer histogram.
3. Set `flush` to $[s_1=s_2=s_3=s_4=s_5]$. For a straight high $k=6,\ldots,14$, form $t_k=\prod_{r=k-4}^k b_r$; for $k=5$, use $t_5=b_{14}b_2b_3b_4b_5$. Set $s=\max(\{k:t_k=1\}\cup\{0\})$. This includes only the ace-low wheel as a wraparound.
4. Extract ranks with multiplicities four, three, and two by masked maximum. Extract descending kickers by sorting the at-most-five relevant ranks or scanning ranks 14 down to 2. No learned classifier or lookup oracle is required.
5. Select the first satisfied category in descending strength and produce the following six-component padded tuple.

All rank extraction can use fixed-width maxima instead of an unspecified sort. Given an eligible-rank mask $E_r$, set $k_0=15$ and

\[
k_j=\max\left(\{r\in\{2,\ldots,14\}:E_r=1,\ r<k_{j-1}\}\cup\{0\}\right).
\]

For kickers use $E_r=[n_r=1]$; for pair ranks use $E_r=[n_r=2]$; for trips/quads use the corresponding count. Flush and high-card categories have distinct ranks, so use $E_r=[n_r>0]$ there. Each extraction is a 13-slot masked integer maximum, repeated at most five times. Padding supplies zero for unused tuple components.

| Category | Condition, after stronger categories fail | Tuple before padding |
| --- | --- | --- |
| 8: straight flush | `flush` and $s>0$ | $(8,s)$ |
| 7: quads | Some $n_q=4$ | $(7,q,k_1)$ |
| 6: full house | $n_t=3,n_p=2$ | $(6,t,p)$ |
| 5: flush | `flush` | $(5,q_{(1)},q_{(2)},q_{(3)},q_{(4)},q_{(5)})$ |
| 4: straight | $s>0$ | $(4,s)$ |
| 3: trips | Some $n_t=3$ | $(3,t,k_1,k_2)$ |
| 2: two pair | Two ranks $p_1>p_2$ have count two | $(2,p_1,p_2,k_1)$ |
| 1: one pair | One rank $p$ has count two | $(1,p,k_1,k_2,k_3)$ |
| 0: high card | Otherwise | $(0,q_{(1)},q_{(2)},q_{(3)},q_{(4)},q_{(5)})$ |

Here $q_{(j)}$ and the distinct kickers are descending. Pad on the right with zeros to obtain $(d_0,\ldots,d_5)$. Encode

\[
k_5=\sum_{j=0}^5d_j15^{5-j}.
\tag{1.19}
\]

Every digit is less than 15. Consequently integer order equals the specified lexicographic tuple order. The key is less than $9\cdot15^5=6{,}834{,}375$, so signed 32-bit integers suffice. No suit component is encoded.

Finally,

\[
k_7(h,B)=\max_{j=1}^{21} k_5(\text{five-card subset }j).
\tag{1.20}
\]

This proves best-five evaluation, including board-only hands and the use of zero, one, or two hole cards. The same construction uses one subset for five-card inputs and six for six-card inputs. It exactly matches R1's evaluator definition; all terminal hold'em comparisons use seven cards. Invalid overlapping hands are masked before ranking or gathered only into legal rows. [R1 §8.1; K: `_rank_five_unchecked`, `evaluate`]

#### 1.1.9 R1.1.1.1.1.3 — Expand the exact river tree and generic resolver

At a decision, store exact mechanics

\[
(s,p,C,c_0,c_1,i,\Delta,L),\quad
P=2C,\ a=c_p,\ f=c_{1-p},\ R_{\mathrm{stack}}=100-C,
\quad Q_{\mathrm{call}}=P+2f.
\]

Here $P$ is fixed for the current street, $P+c_0+c_1$ is the live pot, and a target $b$ costs $b-a$. $R_{\mathrm{stack}}$ is a street target cap, not the actor's remaining stack $R_{\mathrm{stack}}-a$. Use half-BB integers for contribution ledgers and exact numerator/denominator integers for raw candidates and the resolver. A raw flop third need not be a half-BB multiple. Strategy tensors do not determine legal actions.

**Eligibility comes first.** Aggressive candidates are available only if

\[
f<R_{\mathrm{stack}},\qquad i<K_s,\quad K_0=100,\quad K_s=R_{\mathrm{stack}}\ (s>0).
\tag{1.21}
\]

For each raw rational target $x=n/d\ge0$, independently execute

\[
b_0=\left\lfloor\frac{2n+d}{2d}\right\rfloor,
\quad m=\begin{cases}1,&\text{unopened postflop},\\f+\Delta,&\text{raise, including BB's preflop option},\end{cases}
\quad b_1=\max(b_0,m).
\tag{1.22}
\]

Then define

\[
T=(C+b_1\ge100)
\lor(s=0\land b_1>40)
\lor(s\in\{1,2\}\land3(C+b_1)>200),
\qquad b=\begin{cases}R_{\mathrm{stack}},&T,\\b_1,&\neg T.\end{cases}
\tag{1.23}
\]

Only **after** this half-up → minimum → snap pipeline do sort/unique on final targets. The action is its kind and final target; raw aliases get no extra probability slots or histories. Do not use floating rounding, ties-to-even, premature clipping, or rejection of $b_1>R_{\mathrm{stack}}$: the snap must first return that candidate to the all-in target. [R1 §4.1; K: `resolve`, `actions`]

The small sort/unique itself needs only comparisons. For the resolved candidate list $b_0,\ldots,b_{J-1}$, where $J\le4$, keep candidate $j$ iff no earlier candidate has the same final target. For a kept candidate, its aggressive-slot rank is

\[
\operatorname{slot}(j)
=\sum_{k=0}^{J-1}
\mathbf1[\text{candidate }k\text{ is kept}]
\mathbf1[b_k<b_j].
\]

Scatter each kept target into that slot, after the passive slots. This produces exactly one slot per sorted final target, regardless of how many raw candidates rounded, clamped, or snapped together.

On river, the unopened raw targets for BB or SB after BB checks are

\[
\{P/2,P,3P/2,R_{\mathrm{stack}}\}.
\tag{1.24}
\]

Every eligible facing raise, check-raise, or later re-raise uses

\[
\{f+\Delta,\ f+Q_{\mathrm{call}}/2,\ f+Q_{\mathrm{call}},\ R_{\mathrm{stack}}\}.
\tag{1.25}
\]

The two fractional targets equal $C+2f$ and $2C+3f$. The minimum raise is a real candidate. River's explicit all-in passes through the same resolver; river has no additional commitment threshold beyond the stack snap.

Compile each exact transcript recursively:

- Unopened BB: check passes to SB; a bet to $b$ passes to SB facing $b$.
- SB after BB check: check closes the street; a bet passes to BB facing $b$.
- Facing $f>a$: fold terminates; call closes at target $f$; each legal raise to $b$ swaps actor, sets the raiser's contribution to $b$, increments $i$, and sets $\Delta'=b-f$.
- At river closure with matched current-street target $x$, set $C_*=C+x$ exactly once and go to showdown.

A facing all-in has only fold/call. A short all-in records its actual finalized increment. The two equal starting stacks leave no opponent able to raise against an all-in player, so no extra reopening flag is introduced. A check node has no fold or call. An ordinary call has no extra response node. [R1 §§3, 6]

**Redundant-cap proof.** Initially a postflop street has $i=0,f=0$; the preflop blind has $i=f=1$. Every aggressive target is an integer strictly above the previous faced target, hence at least one larger. Induction gives $i\le f$ at facing states. If $f<R_{\mathrm{stack}}$, then $i<R_{\mathrm{stack}}$ postflop and $i<100$ preflop. The caps cannot remove a reachable raise that passes the stack guard. They remain explicit checks, not a license for a smaller live cap. Strict target growth, closing passive actions, and only four streets also prove finiteness. [R1 §§3.3, 6.4]

### 1.2 R2 — Derive an information-set-consistent best response

Freeze the extracted opponent strategy $\bar\sigma_{-i}$, **including its off-path rows**. Recompute reaches from the stored normalized average policy so that the certificate matches its actual rounding and fallback choices. Do not substitute an unweighted, differently weighted, or stale average of iteration reaches. For the realization-weighted construction in §1.1.1, exact own sequence reaches equal their corresponding weighted averages; joint reaches generally do not equal weighted averages of joint reaches.

For responder $i$, propagate $\chi_v$ and $r_{-i}(v,h_{-i})$ through all legal edges. Exclude every responder action probability, even when its submitted policy assigns the action zero probability. At each terminal use (1.15), with the opponent fixed at $\bar\sigma_{-i}$. Then reverse the tree:

\[
B_i(v,h_i)=
\begin{cases}
\max_{a\in A(v)}B_i(va,h_i),&p(v)=i,\\
\sum_{a\in A(v)}B_i(va,h_i),&p(v)=1-i.
\end{cases}
\qquad
\mathcal B_{i,e}=\sum_{h_i}B_i(e,h_i).
\tag{1.26}
\]

Store one maximizing action per $(v,h_i)$. Use the first legal slot in the exact compiled action order to break ties. The stored action applies to every compatible hidden opponent hand. At zero counterfactual mass, all actions have value zero; the same tie rule applies.

**Why this is a legal and optimal BR.** Terminal contraction first sums all hidden opponent hands using the fixed opponent's reach. At each future observed public branch, an independent decision is permitted because the full transcript differs. At each own-hand information set, all underlying opponent hands require one common action, so maximize only after their aggregation. Reverse induction on the finite tree proves optimality. Perfect recall makes own prefix reach constant across all histories in an information set. When it is positive, omitting that common factor does not affect the maximizing action. When it is zero, counterfactual maximization is still required because a BR can change earlier own actions and reach the information set. The opponent-node sum accounts for its already weighted actions.

For comparison, let two equally likely hidden opponent hands give action payoffs $a:(1,-1)$, $b:(-1,1)$. A legal action has expected value zero. The invalid operation $\sum_y\mu(y)\max_a u(a,y)$ gives one by observing the hidden hand. Equation (1.26) performs $\max_a\sum_y\mu(y)u(a,y)$, as required.

For interval-valued child CFVs $[L_a,U_a]$, own-node backup is

\[
[\max_aL_a,\ \max_aU_a],
\tag{1.27}
\]

with outward rounding; opponent-node backup is the interval sum. Terminal products use sign-aware interval multiplication. This encloses the true BR even if the best action is numerically ambiguous. The lower and upper endpoints need not correspond to the same selected response policy. It is the upper endpoint that certifies (0.2).

### 1.3 R3 — Initialization, update order, numerical closure, and stopping

The complete simultaneous iteration is:

```text
Compile the exact public-history tree and immutable integer/rational metadata.
Initialize every legal R and S entry to 0; initialize a complete legal policy.
For t = 1, 2, ...:
    Freeze sigma^t = masked_regret_matching(R^(t-1)) for BOTH players.
    Forward-propagate r_0, r_1 and exact chance/compatibility factors.
    Compute every terminal CF vector by masked opponent-hand contraction.
    Reverse all public nodes; obtain V and every actor's action values G.
    Form all DeltaR = G - V using this same frozen sigma^t.
    Update S with the OLD/frozen own reaches and sigma^t by (1.1).
    Set Y = R^(t-1) + DeltaR; apply sign-selected discount (1.6).
    Synchronize; only now may the next iteration policy be formed.
    At a chosen certification checkpoint:
        Extract the complete normalized bar_sigma from S.
        Freeze its exact stored interpretation.
        Recompute full BR_0 and BR_1 bounds independently.
        Stop only if (0.2) holds after all error allowances.
```

The BR and fixed-policy sweeps evaluate a frozen profile; they never update regrets or solve an equilibrium. Updating a child strategy midway through a reverse sweep changes the profile being evaluated and violates the stated schedule.

Full traversal means a zero actual-reach information set is still visited. A zero own reach suppresses only that iteration's average contribution, not its regret calculation. A zero counterfactual mass yields a zero instantaneous regret. A zero average row receives the documented uniform fallback. Invalid card rows and invalid actions are never reinterpreted as zero-reach legal decisions.

All reductions, interval rules, probability-rounding terms, and continuation allowances required to close R3 are derived in §5. Training in FP64 by itself is not a proof of the requested tolerance. No iteration count, exploitability measurement, or solved river policy is asserted by this document.

---

<a id="turn"></a>

## 2. Turn: top-down derivation

Compare this street: [A](derivation-a.md#turn) · [B](derivation-b.md#turn) · C · [D](derivation-d.md#turn) · [Reading map](#reading-map)

### T0 — Root obligation: a certified turn continuation

For a specified four-card public entry $e$, fixed compatible boundary factors, and $C_e<100$, the required root result is

\[
\boxed{\frac{\overline{\mathcal B}_{0,e}+
\overline{\mathcal B}_{1,e}}2\le0.005P_e,\qquad P_e=2C_e.}
\tag{T0}
\]

The strategies certified here include **both turn and every descendant river decision**. The river board retains the exact prior flop and turn transcript.

| Node | Parent | Required object / operation | Expansion |
| --- | --- | --- | --- |
| T0 | — | Turn BR certificate at $0.005P_e$ | T0 |
| T1 | T0 | Complete turn-plus-river averaged policy | §2.1 |
| T1.1 | T1 | Reach-weighted DCFR at every descendant infoset | (1.1)–(1.6), with turn-rooted weights |
| T1.1.1 | T1.1 | Turn CF advantages | (1.9)–(1.10), §2.2 |
| T1.1.1.1 | T1.1.1 | Range-correct fixed-profile river continuation | §§2.2, 2.4 |
| T1.1.1.1.1 | T1.1.1.1 | River action/terminal vector kernels | River §1, independently indexed per full history |
| T1.1.1.2 | T1.1.1 | Exact river reveal and all-in chance leaf | §2.3 |
| T1.1.1.2.1 | T1.1.1.2 | Physical-card mask, $1/44$, rank/payoff contractions | (1.12), (1.15)–(1.20), (2.3) |
| T1.1.2 | T1.1 | Exact turn menus, closure, and forward reaches | §2.5, (1.13), (2.4) |
| T2 | T0 | Fresh full turn-plus-river BR bounds | §2.6 |
| T2.1 | T2 | Infoset max and chance/opponent sums | (1.26) and (2.5) |
| T3 | T0 | Numerical and continuation error allowance | §§5–6, with turn entry units |

### 2.1 T1 — A turn solve includes all its river information sets

Instantiate the §1.3 loop over the entire turn-rooted descendant tree. Initialize $R=S=0$ in its turn and river rows, or provide a fully specified warm start; the baseline is zero initialization. Freeze one complete profile $\sigma^t$ across both streets.

The forward traversal passes through turn actions, river chance events, and river actions. The backward traversal evaluates river terminal payoffs, river decisions, river chance, and then turn decisions. The resulting turn and river advantages all belong to the same fixed boundary game and the same iteration profile. Apply all discounts and average updates only after that traversal.

In particular, a river information set's average weight is its own reach **from the turn entry**, including any earlier own turn actions. Its CFVs include the opponent's reach from the turn entry. Resetting either quantity at the river entry changes the simultaneous full-subgame DCFR update. Separate local river solves can be useful as separately certified objects or initial policies, but are not required calls inside this loop.

### 2.2 T1.1.1 — What a river continuation must supply to a turn backup

At a fixed exact river entry $f$, distinguish three different operations:

| Operation | Inputs | Output | What stays fixed |
| --- | --- | --- | --- |
| Fixed-profile evaluation | $f$, a complete descendant profile $\sigma_f$, pair $(x,y)$ | $W_i^{\sigma_f}(f,x,y)$ | Both players' river policies |
| Counterfactual contraction | The same profile, compatible opponent factor, and prefix scale | A vector for every own hand | Policies and the given weights |
| Equilibrium solving | $f$, two boundary factors, tolerance, algorithm state | A new complete profile and its certificate | The boundary game during that solve |

The first operation is the expanded river recursion (1.7), ending in (1.17)–(1.20). Its pairwise payoff matrix is independent of boundary ranges **once the profile is fixed**. The third operation can change the policies, so its matrices and vectors generally change with the ranges.

For a fixed river profile, define opponent-weighted boundary values

\[
g_{i,f}(h_i)=
\sum_{h_{-i}}M_f(h_0,h_1)a_{-i}(h_{-i})
W_i^{\sigma_f}(f,h_0,h_1).
\tag{2.1}
\]

Their three useful interpretations are

\[
F_{i,f}(h_i)=\frac{a_i(h_i)}{Z_f}g_{i,f}(h_i),
\quad
\nu_{i,f}(h_i)=\frac{g_{i,f}(h_i)}{m_i(h_i)}
\quad(m_i>0),
\quad
U_{i,f}=\sum_{h_i}F_{i,f}(h_i).
\tag{2.2}
\]

$F$ is the local root-chance-included CF vector; $\nu$ is the ordinary value conditional on the player's hand when $\mu_{i,f}(h_i)>0$; $g$ excludes the player's own boundary factor. Do not interchange them. In particular, a turn player needs hand-specific continuation values, not only $\sum F$.

If $a_i(h_i)=0$ but $m_i(h_i)>0$, $g_i$ is still defined, and $\nu_i=g_i/m_i$ is an explicit counterfactual conditional extension using the opponent kernel proportional to $M_f(h_i,h_{-i})a_{-i}(h_{-i})$. It is not ordinary conditioning on a positive-probability event under $\mu_f$. These values are important for possible upstream deviations. If $m_i(h_i)=0$, $g_i=0$ and the conditional quotient $\nu_i$ is undefined; mark it invalid rather than interpreting it as a conditional zero payoff.

### 2.3 T1.1.1.2 — Expand river chance and the turn all-in leaf

For a four-card public board $B_v$, enumerate every physical candidate card $d\in\mathcal D\setminus B_v$, in card-ID order. There are 48 public candidates; each underlying pair of disjoint private hands removes four more. Therefore

\[
q_v(d\mid x,y)=
\frac{\mathbf1[d\notin h_x\cup h_y\cup B_v]}{44}.
\tag{2.3}
\]

The public candidate set is a convenient union over underlying chance supports. An edge with a zero pairwise mask is absent for that underlying history; it does not create a legal zero-probability private-world history. For each compatible pair, exactly 44 cards have nonzero probability, so their sum is one. It is wrong to use $1/46$ based only on a player's two private cards and four visible board cards. [R1 §2.3]

For the child public transcript $w=vd$,

\[
\chi_w(x,y)=\chi_v(x,y)q_v(d\mid x,y),\qquad
r_i(w,h_i)=r_i(v,h_i)
\tag{2.4}
\]

on card-valid child rows. In a conditional pairwise suffix representation,

\[
W_i(v,x,y)=\sum_dq_v(d\mid x,y)W_i(vd,x,y).
\]

In the forward-weighted CF representation used for training and BR, the equivalent backup is instead

\[
\boxed{V_i(v,h_i)=\sum_dV_i(vd,h_i),\qquad
B_i(v,h_i)=\sum_dB_i(vd,h_i).}
\tag{2.5}
\]

The child $\chi$ already includes $1/44$ and the blocker mask. Applying them again in (2.5) would double-count chance. GPU implementation is a ragged segmented sum of child vectors; generate the 48 candidate cards, mask pair incompatibilities at the hand-pair contractions, and keep the original global hand indices.

An ordinary turn closure at matched target $x$ sets $C'=C+x$. If $C'<100$, the river reveal is followed by the exact river game at $C'$. If $C'=100$, the reveal is followed directly by showdown at 100; there are no river decision nodes.

For a called turn all-in, its pairwise payoff is consequently the explicitly computable kernel

\[
J_0^{\mathrm{AI}}(B,x,y)
=\frac{100}{44}
\sum_{\substack{d\notin B\cup h_x\cup h_y}}
\operatorname{sgn}\!\left(
k_7(h_x,Bd)-k_7(h_y,Bd)\right),
\quad J_1^{\mathrm{AI}}=-J_0^{\mathrm{AI}}.
\tag{2.6}
\]

Here $Bd$ appends a river card to the four-card board; it never sorts turn and river together. Equation (2.6) is a fused chance-only computation of the same sequential R1 runout. Its value depends on the cards, not strategic ranges; contracting it against ranges produces the desired CF vector. There is no all-in equilibrium to solve.

### 2.4 T1.1.1.1 — Exact range updates and lifting local outputs back to the parent

Let the current outer solve start at $e$ with factors $a_i$ and normalization $Z_e$. At a descendant exact public boundary $f$, define the within-solve own-action reaches $r_i(f,h_i)$ and raw new factors

\[
\ell_i^f(h_i)=a_i(h_i)r_i(f,h_i).
\tag{2.7}
\]

Apply the child board mask. Let $\kappa_{e\to f}$ be the product of the intervening board-chance probabilities for the exact observed board path; this is a scalar common to compatible pairs. For a direct turn-to-river reveal it includes $1/44$. Put

\[
Z_f^{\rm raw}=\sum_{x,y}M_f(x,y)\ell_0^f(x)\ell_1^f(y).
\]

If $Z_f^{\rm raw}>0$, then

\[
\mu_f(x,y)=
\frac{M_f(x,y)\ell_0^f(x)\ell_1^f(y)}{Z_f^{\rm raw}},
\qquad
\Pr_{\sigma,\mu_e}(f)
=\frac{\kappa_{e\to f}Z_f^{\rm raw}}{Z_e}.
\tag{2.8}
\]

For a fixed suffix policy, calculate a child value with the *raw opponent factor*

\[
g_i^{f,\rm raw}(h_i)
=\sum_{h_{-i}}M_f(h_0,h_1)\ell_{-i}^f(h_{-i})
W_i^{\sigma_f}(f,h_0,h_1).
\]

The exact parent CFV is

\[
\boxed{
V_i^{\text{outer}}(f,h_i)
=\frac{\kappa_{e\to f}}{Z_e}
a_i(h_i)\,g_i^{f,\rm raw}(h_i).
}
\tag{2.9}
\]

**Proof.** Substitute the factorized $\chi_f$ into (1.8):
$\chi_f=(\kappa/Z_e)M_fa_0a_1$. Multiplication by only the opponent's within-solve reach gives $\ell_{-i}^f$ inside the hidden-hand sum and leaves the original $a_i$ outside. No own within-solve reach is present.

If a local routine normalizes $\ell_{-i}^f$ to $\ell_{-i}^f/s_{-i}$, multiply its returned $g_i$ by $s_{-i}$ before (2.9). Do not replace $a_i$ by $\ell_i^f$. A tempting conversion via
$\Pr(f)F_i^{\rm local}(h_i)/r_i(f,h_i)$ works only when the denominator is positive; (2.9) is the correct direct definition, including zero own reach.

If $Z_f^{\rm raw}=0$, (2.8) has no normalized posterior. Equation (2.9) can nevertheless be nonzero for the player whose own prefix reach caused the zero. Therefore full DCFR uses unnormalized forward weights and does not require a normalized solve at every current off-path river entry.

For an actual **solving** interface, one may define

\[
\operatorname{Solve}(f,a_0,a_1,\varepsilon)
\mapsto
\bigl(\bar\sigma_f,\ W_f^{\bar\sigma},
g_{0,f},g_{1,f},\
\overline{\mathcal B}_{0,f},\overline{\mathcal B}_{1,f},
\text{error bounds}\bigr).
\tag{2.10}
\]

The matrix can be streamed rather than stored. This is not an unspecified oracle: its implementation is the loop and primitives in §1. Its guarantee applies to the stated inputs. The family of solved profiles can be denoted $\bar\sigma_f[a_0,a_1]$, emphasizing its range dependence.

The equilibrium scalar

\[
v_f^*(a_0,a_1)=
\max_{\tau_0}\min_{\tau_1}
\sum_{x,y}\mu_f(x,y)W_0^{\tau_0,\tau_1}(f,x,y)
\tag{2.11}
\]

has already integrated away hand identity. Substituting it for every hand pair at the turn boundary cannot reproduce (2.1), a deviation's continuation values, or the complete fixed strategy being certified. Even an exact solver for every nominal river range does not remove this issue. Section 6 gives the conditions under which separately solved continuations can safely be stitched.

### 2.5 T1.1.2 — Compile the turn without changing its action abstraction

At turn entry $s=2$, BB acts with $P=2C$, $c_0=c_1=0$, and $i=\Delta=0$. Both the immediate BB opening and SB's opening after a BB check use raw targets

\[
\{P/2,P\}.
\tag{2.12}
\]

Every eligible responding raise uses

\[
\{f+\Delta,\ f+Q_{\rm call}/2,\ f+Q_{\rm call}\}.
\tag{2.13}
\]

There is no additional explicit turn jam. Apply exactly (1.21)–(1.23), including the strict condition $3(C+b_1)>200$. At $C=30$, a clamped target 36 remains 36; a clamped target 37 snaps to 70. These demonstrate the resolver, not extra menu candidates.

The passive and aggressive transitions are those already expanded in §1.1.9. A check-through closes at $x=0$; a call closes at $x=f$; a fold terminates before any river reveal. An uncalled jam is followed by the explicit fold/call response. Ordinary closure activates a pending chance node first, then BB acts on the river; no future river action is visible before that reveal. [R1 §§3–4, 6; K: _settle, advance_board]

### 2.6 T2 and T3 — Turn BR certification and its exact scope

Freeze the **complete** average turn/river policy. Run two fresh BR passes. Use own-node maxima (1.26), opponent-node sums, and the chance sum (2.5), with exact pairwise chance masks. The BR can change the responder's turn policy and every downstream river policy coherently; it does not ask a local solver to re-equilibrate the opponent after a deviation.

Apply the numerical upper-bound construction in §5 and accept only T0. A separate certificate for a river profile at one posterior does not substitute for this turn-rooted BR. Conversely, a passing turn-rooted certificate by itself does not imply that every rare or zero-reach river entry meets its own local $0.005P_f$ requirement; such a local claim requires its own specified ranges and test.

---

<a id="flop"></a>

## 3. Flop: top-down derivation

Compare this street: [A](derivation-a.md#flop) · [B](derivation-b.md#flop) · C · [D](derivation-d.md#flop) · [Reading map](#reading-map)

### F0 — Root obligation: a certified flop continuation

For every specified exact three-card flop entry $e$ with $Z_e>0$ and $C_e<100$,

\[
\boxed{\frac{\overline{\mathcal B}_{0,e}+
\overline{\mathcal B}_{1,e}}2\le0.005P_e,\qquad P_e=2C_e.}
\tag{F0}
\]

Its returned policy contains every flop, turn, and river information set below that exact preflop history and flop observation.

| Node | Parent | Required object / operation | Expansion |
| --- | --- | --- | --- |
| F0 | — | Flop BR certificate at $0.005P_e$ | F0 |
| F1 | F0 | Complete three-street average policy | §3.1 |
| F1.1 | F1 | Reach-weighted DCFR and full-profile advantages | §§1.1.1–1.1.5, from the flop root |
| F1.1.1 | F1.1 | Flop action CFVs and turn continuations | (1.9)–(1.10), (2.9), §3.2 |
| F1.1.1.1 | F1.1.1 | Exact turn/river fixed-policy evaluator | §2, with separate full-history indices |
| F1.1.1.2 | F1.1.1 | Turn chance and called-flop-all-in payoffs | §3.2 |
| F1.1.1.2.1 | F1.1.1.2 | $1/45$, then $1/44$, blockers, ranking, net payoff | (1.12), (1.18)–(1.20), (3.1)–(3.2) |
| F1.1.2 | F1.1 | Exact flop origin, raw menus, and resolver | §3.3 |
| F2 | F0 | Full three-street infoset BR upper bounds | §3.4 |
| F2.1 | F2 | Opponent reaches, max after aggregation, chance sums | §§1.2, 2.3, 3.2 |
| F3 | F0 | Numerical/continuation proof obligations | §§5–6, in flop entry units |

### 3.1 F1 — Joint solving and backward evaluation remain distinct

Run the same simultaneous DCFR loop over the full flop-rooted tree. At iteration $t$, freeze every flop, turn, and river row. Propagate reaches forward from the flop entry; perform the backward sweep river decisions → river chance → turn decisions → turn chance → flop decisions, with folds terminating at their actual street.

A descendant turn average uses the player's own flop reach; a descendant river average uses the player's own flop and turn reaches. Its regrets use the opponent/chance weights from the flop root. Local normalization at a turn boundary is only a representation change if the exact scale is restored by (2.9).

The range-dependent turn solver is the expanded §2 algorithm, not a black-box scalar. If invoked separately, it returns a profile and hand-specific continuation outputs for its given ranges. During joint training, use the **fixed current turn/river policies** in the value sweep. Inserting a fresh child equilibrium while retaining old reaches or old ancestor policies does not implement the stated algorithm.

### 3.2 F1.1.1.2 — Expand turn chance and the complete flop all-in runout

For a fixed flop $B=(F_1,F_2,F_3)$ with $F_1<F_2<F_3$, enumerate the 49 physical card IDs outside the public flop. Four are blocked by the underlying pair of private hands. Hence

\[
q_v(t\mid x,y)=
\frac{\mathbf1[t\notin B\cup h_x\cup h_y]}{45}.
\tag{3.1}
\]

Append $t$ with its turn label. The next river reveal uses (2.3), denominator 44. Forward chance weights multiply by these probabilities; weighted CFV and BR backups sum the already weighted child vectors exactly as in (2.5).

On an ordinary flop closure, set $C'=C+x$ once, deal the turn, and start BB at $C'$ with zero street contributions and zero aggression metadata. On a called flop all-in, skip **all turn and river betting** and use

\[
J_0^{\rm AI}(B,x,y)=
\frac{100}{45\cdot44}
\sum_{\substack{t,r\notin B\cup h_x\cup h_y\\t\ne r}}
\operatorname{sgn}\!\left(
k_7(h_x,(B,t,r))-k_7(h_y,(B,t,r))\right),
\quad J_1^{\rm AI}=-J_0^{\rm AI}.
\tag{3.2}
\]

The summation is over **ordered street-labeled** turn/river pairs: 1980 outcomes for each compatible underlying pair. The two reveals are sequential in the EFG. A fused tile may accumulate (3.2), preserving that product probability and those labels. Replacing this by an unordered two-card set with unchanged $1/(45\cdot44)$ weights would halve the total probability. An exact algebraic grouping would have to sum the weights of both labeled outcomes and must not identify any ordinary decision histories.

A fold is still immediate and produces no runout. A jam without a call is still a player response, not this chance-only leaf. Skipped streets record ledger zeros rather than artificial checks. [R1 §§2.4, 3.4, 6.3]

GPU execution can tile first over turn candidates, then river candidates, accumulate compatible payoff contributions, and free each tile. There is no need to allocate all runout/pair combinations simultaneously, but every legal outcome is included. Sharing these purely chance/payoff kernels across equal card/commitment inputs does not share any strategy row.

### 3.3 F1.1.2 — Compile the exact flop origin and menus

At flop entry, $s=1$, BB acts, $P=2C$, $c_0=c_1=0$, and $i=\Delta=0$. The public flag $L$ is true **only** for root SB limp followed by BB check. Its raw opening menu, for either BB immediately or SB after a BB check, is

\[
\mathcal X_{\rm open}=
\begin{cases}
\{P/2,P\},&L=\mathrm{true},\\
\{P/3,2P/3\},&L=\mathrm{false}.
\end{cases}
\tag{3.3}
\]

Every eligible facing raise uses exactly (2.13), including the minimum raise as an actual candidate. There is no added explicit flop jam. The strict flop/turn snap $3(C+b_1)>200$, all guards, half-up rounding, minimum enforcement, sorting, and deduplication are unchanged.

The 11 ordinary preflop exits produce the following opening targets after resolution. In this table $L$ in a prefix abbreviates the finalized root call to 1, $X$ is check, and $C_b,R_b$ are call/raise to the displayed final target.

| Exact completed preflop action prefix | $C$ | $P$ | $100-C$ | Limp/check flag | Resolved flop bet targets |
| --- | ---: | ---: | ---: | --- | --- |
| $L,X$ | 1 | 2 | 99 | True | 1, 2 |
| $L,R_4,C_4$ | 4 | 8 | 96 | False | 3, 5 |
| $L,R_4,R_{12},C_{12}$ | 12 | 24 | 88 | False | 8, 16 |
| $L,R_4,R_{12},R_{28},C_{28}$ | 28 | 56 | 72 | False | 19, 37 |
| $R_2,C_2$ | 2 | 4 | 98 | False | 1, 3 |
| $R_2,R_8,C_8$ | 8 | 16 | 92 | False | 5, 11 |
| $R_2,R_8,R_{22},C_{22}$ | 22 | 44 | 78 | False | 15, 29 |
| $R_2,R_8,R_{22},R_{36},C_{36}$ | 36 | 72 | 64 | False | 24, 64 |
| $R_3,C_3$ | 3 | 6 | 97 | False | 2, 4 |
| $R_3,R_{11},C_{11}$ | 11 | 22 | 89 | False | 7, 15 |
| $R_3,R_{11},R_{28},C_{28}$ | 28 | 56 | 72 | False | 19, 37 |

Check is also available at each opening. These are all ordinary entries; preflop called-all-in exits never instantiate flop betting. The two $C=28$ rows remain distinct even if the flop and private hand happen to agree. A later lead/call and check/bet/call remain distinct in exactly the same way. [R1 §5.3]

### 3.4 F2 and F3 — Flop certificate and downstream obligations

Extract one complete average policy from the full flop solve and evaluate both BRs with all downstream decisions available to the responder. Include exact turn/river chance and exact all-in kernels. Only the upper-bound comparison F0 certifies the flop root.

The error budget is in BB relative to this fixed flop entry. A downstream turn's own target uses its own $P_f$; that number is not an automatic allowable error in the parent value. Section 5 proves how actual payoff or CFV error propagates, and §6 separates that question from the strategic loss caused by using an imperfect continuation.

---

<a id="preflop"></a>

## 4. Preflop: top-down derivation

Compare this street: [A](derivation-a.md#preflop) · [B](derivation-b.md#preflop) · C · [D](derivation-d.md#preflop) · [Reading map](#reading-map)

### P0 — Root obligation: certify the complete R1 game

At the initial preflop decision, the live entry pot is $P_e=1/2+1=1.5$ BB, even though the mechanics variable for completed-street pot is $P=2C=0$. The requested full-game certificate is

\[
\boxed{
\operatorname{Expl}_{\rm R1}(\bar\sigma)
\le0.005\cdot1.5
=0.0075\ {\rm BB},
\quad
\frac{\overline{\mathcal B}_{0}+\overline{\mathcal B}_{1}}2
\le\frac3{400}.
}
\tag{P0}
\]

Equivalently, total unilateral gain is at most 0.015 BB under the convention (0.1).

| Node | Parent | Required object / operation | Expansion |
| --- | --- | --- | --- |
| P0 | — | Full-game BR certificate at 0.0075 BB | P0 |
| P1 | P0 | Complete full-history, four-street average policy | §4.1 |
| P1.1 | P1 | Full-tree simultaneous tabular DCFR | §§1.1–1.3, rooted at private chance |
| P1.1.1 | P1.1 | Preflop action CFVs and flop continuation vectors | (1.9)–(1.10), (2.9), §4.2 |
| P1.1.1.1 | P1.1.1 | Exact fixed-profile flop/turn/river evaluator | §§3 → 2 → 1 |
| P1.1.1.2 | P1.1.1 | Exact flop reveal and called-preflop-all-in leaf | §§4.3–4.4 |
| P1.1.1.2.1 | P1.1.1.2 | Canonical triple enumeration, blockers, $1/\binom{48}{3}$, later $1/45,1/44$ | §§4.3–4.4 |
| P1.1.2 | P1.1 | Initial private distribution and own reaches | §4.5 |
| P1.1.3 | P1.1 | Complete preflop table with finalized actions | §4.2 |
| P2 | P0 | Two full-root information-set BR upper values | §4.6 |
| P2.1 | P2 | Entire legal tree, opponent reach, terminal reduction, max/sum backups | §§1.2, 2.3, 3.2, 4.3–4.5 |
| P3 | P0 | Total numerical and continuation allowance in BB | §§5–6 |

### 4.1 P1 — Full-game equilibrium solving

The baseline full solve initializes one regret row and one average row for every legal $(v,h_i,a)$ at every street. It runs the §1.3 loop from the original private chance distribution. No river, turn, or flop is permanently replaced by an equilibrium scalar.

One frozen iteration consists of:

1. Derive both players' complete behavioral profiles from the previous regrets.
2. Traverse preflop, flop, turn, and river **forward** for each player's own reaches and for the exact card/chance masks.
3. Evaluate net terminal payoffs, then propagate weighted CFVs **backward**, with later streets completed before earlier ones.
4. Compute the actor's CF advantage at each information set. Use the same profile and its own reach for the weighted average update.
5. Update all signed regrets and averages using (1.1), (1.6); synchronize.

These steps constitute equilibrium search. The backward sweep within step 3 alone computes only an expectation under the existing profile. Max-backups used for certification solve a one-player response problem against a fixed opponent; they are not two-player equilibrium updates.

Solving separate public-entry games is also well-defined when their boundary factors are supplied. Such local certificates describe those games. They neither uniquely determine the ancestor equilibrium ranges nor automatically provide a full-game certificate.

### 4.2 P1.1.3 — Complete preflop table and exact mechanics

Start after the private deal with

\[
(s,p,C,c_0,c_1,i,\Delta)
=(0,\mathrm{SB},0,\tfrac12,1,1,1).
\tag{4.1}
\]

The posted BB is aggression level 1, and its initial minimum increment is 1 rather than $1-1/2$. Preflop uses the fixed table below, not postflop fractional menus.

Here $L$ is a notation for the sole root call to 1; its finalized action is the JSON token C1. It is not an additional action or raw alias. $E_\alpha(C)$ means: retain this exact prefix $\alpha$, deal the flop, then activate the ordinary flop entry at matched total $C$. $U_\alpha$ means the exact called-all-in runout to showdown at 100. Every row shown has a distinct full public prefix. Fold entries are SB's net utility; BB's is its negative.

| Node | Complete preflop prefix | Actor | $(c_{\rm SB},c_{\rm BB})$ | $i$ | $\Delta$ | Fold $u_{\rm SB}$ | Passive edge | Finalized raise successors |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| P0 | Empty | SB | $(1/2,1)$ | 1 | 1 | $-1/2$ | $L\to L0$ | $R_2\to O2;\ R_3\to O3$ |
| L0 | $L$ | BB | $(1,1)$ | 1 | 1 | Absent | $X\to E_{LX}(1)$ | $R_4\to L4$ |
| L4 | $L,R_4$ | SB | $(1,4)$ | 2 | 3 | $-1$ | $C_4\to E_{L4C}(4)$ | $R_{12}\to L12$ |
| L12 | $L,R_4,R_{12}$ | BB | $(12,4)$ | 3 | 8 | $+4$ | $C_{12}\to E_{L12C}(12)$ | $R_{28}\to L28$ |
| L28 | $L,R_4,R_{12},R_{28}$ | SB | $(12,28)$ | 4 | 16 | $-12$ | $C_{28}\to E_{L28C}(28)$ | $R_{100}\to LJ$; raw 60 |
| LJ | $L,R_4,R_{12},R_{28},R_{100}$ | BB | $(100,28)$ | 5 | 72 | $+28$ | $C_{100}\to U_{LJ}$ | None |
| O2 | $R_2$ | BB | $(2,1)$ | 2 | 1 | $+1$ | $C_2\to E_{2C}(2)$ | $R_8\to O8$ |
| O8 | $R_2,R_8$ | SB | $(2,8)$ | 3 | 6 | $-2$ | $C_8\to E_{8C}(8)$ | $R_{22}\to O22$ |
| O22 | $R_2,R_8,R_{22}$ | BB | $(22,8)$ | 4 | 14 | $+8$ | $C_{22}\to E_{22C}(22)$ | $R_{36}\to O36;\ R_{100}\to O2J$; raws 36, 50 |
| O36 | $R_2,R_8,R_{22},R_{36}$ | SB | $(22,36)$ | 5 | 14 | $-22$ | $C_{36}\to E_{36C}(36)$ | $R_{100}\to O36J$; raw 50 |
| O2J | $R_2,R_8,R_{22},R_{100}$ | SB | $(22,100)$ | 5 | 78 | $-22$ | $C_{100}\to U_{O2J}$ | None |
| O36J | $R_2,R_8,R_{22},R_{36},R_{100}$ | BB | $(100,36)$ | 6 | 64 | $+36$ | $C_{100}\to U_{O36J}$ | None |
| O3 | $R_3$ | BB | $(3,1)$ | 2 | 2 | $+1$ | $C_3\to E_{3C}(3)$ | $R_{11}\to O11$ |
| O11 | $R_3,R_{11}$ | SB | $(3,11)$ | 3 | 8 | $-3$ | $C_{11}\to E_{11C}(11)$ | $R_{28}\to O28$ |
| O28 | $R_3,R_{11},R_{28}$ | BB | $(28,11)$ | 4 | 17 | $+11$ | $C_{28}\to E_{O28C}(28)$ | $R_{100}\to O3J$; raw 60 |
| O3J | $R_3,R_{11},R_{28},R_{100}$ | SB | $(28,100)$ | 5 | 72 | $-28$ | $C_{100}\to U_{O3J}$ | None |

All ordinary raise targets equal their raw targets. Raw 50 and 60 run through the ordered resolver and snap to 100 because the clamped preflop target exceeds 40. At O22, 36 is a full raise of 14; from O36, raw 50 exactly meets the next minimum and then snaps. The snap comparison is strict: a hypothetical candidate clamped to 40 remains ordinary; 41 snaps. Such illustrations do not add unlisted raw candidates. [R1 §§4.1, 5.2; K: _PREFLOP_RAW, resolve]

This table contains 16 player-decision prefixes, 15 fold exits, 11 ordinary flop exits, and four called-all-in exits. Every call except the initial limp closes preflop. The BB option check matches target 1 and sets the unique limp/check flag. The jam response rows remain explicit. The table's mechanics row ID is convenient metadata, but later strategy keys retain the complete prefix; the two paths closing at 28 never merge.

The preflop route used for raw-menu lookup resets after closure. The public transcript never resets. The kernel's internal route abbreviation C for the root limp is not a replacement for its public finalized action token C1. [R1 §§3.1, 5, 7; K: step, preflop_tree]

### 4.3 P1.1.1.2 — Derive exact flop chance from combinatorial enumeration

After an ordinary preflop closure, enumerate public candidate flops

\[
F=(F_1,F_2,F_3),\qquad 0\le F_1<F_2<F_3<52.
\]

There are $\binom{52}{3}=22{,}100$ candidates in the union support. For a fixed private pair, only the triples from the 48 remaining cards are legal:

\[
q_v(F\mid x,y)=
\frac{\mathbf1[F\cap(h_x\cup h_y)=\varnothing]}
{\binom{48}{3}},
\qquad \binom{48}{3}=17{,}296.
\tag{4.2}
\]

The numerator is a bit-mask test, and the denominator is an exact integer. Three increasing card-ID loops generate every canonical flop once. A GPU can enumerate these triples in immutable buffers or generate them in tiles. Sorting the triple represents its unordered identity; no factor $3!$ is added and no six flop-order histories are created.

For a general next public block $S$ with $k$ cards and current board length $b$, the complete formula is

\[
q_v(S\mid x,y)=
\frac{\mathbf1[S\cap(h_x\cup h_y\cup B_v)=\varnothing]}
{\binom{52-4-b}{k}},
\qquad
k=\begin{cases}3,&b=0,\\1,&b=3,4.\end{cases}
\tag{4.3}
\]

Events of the wrong length, duplicate cards, out-of-deck IDs, or a noncanonical flop have no edge. For every legal pair, the number of surviving candidates is exactly the denominator, proving normalization. There are no burn-card events. Thus the successive chance factors are exactly $1/17{,}296$, $1/45$, $1/44$. The dealer removes **both** private hands even though neither player observes the other one. [R1 §§2.1–2.3]

Update $\chi$ using (4.2), retain each player's own action reach, and use the chance sum (2.5). At the revealed flop entry use the exact originating prefix and the resolved menus in §3.3. Conditional public-flop probabilities under a strategic posterior are obtained by summing $\mu(x,y)q(F\mid x,y)$ over compatible pairs, not by changing the dealer's denominator.

### 4.4 P1.1.1.2 — Derive the complete preflop all-in payoff kernel

A called preflop all-in has no further player decisions. For a fixed pair of disjoint private hands,

\[
J_0^{\rm AI}(\varnothing,x,y)=
\frac{100}{\binom{48}{3}\,45\,44}
\sum_{\substack{F_1<F_2<F_3\\F\cap(h_x\cup h_y)=\varnothing}}
\ \sum_{\substack{t,r\notin F\cup h_x\cup h_y\\t\ne r}}
\operatorname{sgn}\!\left(
k_7(h_x,(F,t,r))-k_7(h_y,(F,t,r))\right),
\tag{4.4}
\]

with $J_1^{\rm AI}=-J_0^{\rm AI}$. There are exactly
$\binom{48}{3}\,45\,44=34{,}246{,}080$ legal labeled complete runouts per fixed private pair. The numerator sum uses the integer best-five evaluator already derived; it contains no equity-table black box.

The flop is unordered/canonical, while $t$ and $r$ retain distinct street identities. The full five-card board is never globally sorted in the history. Fusing (4.4) is an arithmetic implementation of the sequential chance-only EFG; ordinary flop/turn/river action histories remain separate. Every skipped betting street has the specified zero ledger entry, and the final matched contribution stays 100. An initial jam action alone does not select this kernel; only its subsequent call does. [R1 §§2.4, 3.4, 6.3]

### 4.5 P1.1.2 — Derive the root private distribution and initial tensor weights

Root chance first chooses an unordered canonical SB hand and then an unordered BB hand from the 50 remaining cards, with seats labeled:

\[
\mu_{\rm root}(x,y)=
\frac{\mathbf1[h_x\cap h_y=\varnothing]}
{\binom{52}{2}\binom{50}{2}}
=\frac{M_{\rm root}(x,y)}{1326\cdot1225}.
\tag{4.5}
\]

There are $1326\cdot1225=1{,}624{,}350$ legal ordered seat assignments. Every one has the displayed exact probability, proving normalization. There is no division by two for swapping seats.

This is the factor convention (0.4) with $a_0=a_1=1/H$ and

\[
Z_{\rm root}=\frac{1225}{1326}.
\tag{4.6}
\]

Initialize $\chi_e=\mu_{\rm root}$ and both own reaches to one. No player decision precedes this private draw. The public-node vectorization represents its hidden branches through the two hand indices; a strategy row depends only on the actor's own hand and the complete public transcript.

At every later chance edge, (4.3) removes all used physical cards. At every player edge, the exact finalized action and actor/street are appended. These inductions prove that the generated support and information partition are the original R1 EFG, even though arithmetic is batched.

### 4.6 P2 and P3 — Final full-root BR test and implementation scale

Extract $\bar\sigma$ using each information set's **full preflop-root own reach** in (1.1). Freeze its exact normalized interpretation. For responder 0 and responder 1 separately:

1. Propagate the fixed opponent's reach through every legal player edge and exact chance event.
2. Contract all terminal payoffs over the hidden opponent hand.
3. Maximize one action per own-hand/full-history information set, sum weighted opponent and chance children, and sum the resulting root hand values.
4. Add outward numerical allowances or use directly computed interval upper endpoints.

Accept only P0. This full-root test accounts for deviations that alter preflop ranges, enter an unused branch, change later bet sizes within the R1 menu, and change every later response. It is the direct global certificate; the local-to-global theorem in §6 is needed only when one attempts to infer a global result from partial certificates.

The persistent regret/average storage is proportional to the number of **actual information sets and legal actions**. With the padded representation it is $2N_DH\cdot6$ numbers for $R,S$ alone, plus policies and working storage. Tiling can reduce hand-pair and value-workspace memory; it cannot erase the distinct tabular states required by the full-history contract. No GPU capacity or runtime claim follows from these formulas.

The primitive operations are now fully exposed: integer card masks; increasing-combination enumeration; exact monetary resolve/sort/unique; fixed subset gathers; rank-count reductions; integer maxima and comparisons; masked matrix–vector terminal contractions; child gathers; elementwise reach products; segmented chance/opponent sums; six-slot weighted sums and maxima; signed regret arithmetic; and row normalization. Their ordering, masks, initialization, and zero rules are specified above.

---

## 5. Proofs of numerical and continuation-error propagation

These lemmas discharge R3, T3, F3, and P3. They distinguish structural correctness, fixed-policy evaluation error, strategic continuation error, and training error. An omitted action, merged information set, incorrect snap, or changed chance support is a different EFG, not a small floating-point error to ignore.

### 5.1 Freeze an exact interpretation of the submitted policy

At a certificate checkpoint, copy the stored average weights. Reject nonfinite entries; ensure legal entries are nonnegative and illegal entries are exactly zero. For each positive-sum row, interpret its finite stored weights as exact dyadic rationals and define the row probability as each weight divided by their exact sum. A zero row uses the exact uniform legal distribution. This specifies one precise legal real/rational policy even when its probabilities are not exactly representable in machine floating point.

The certifier either uses exact arithmetic on that interpretation or encloses every operation with outward rounding. It certifies this actual policy, not the ideal policy that an infinite-precision training run might have produced. The same principle fixes the input boundary factors. If the intended boundary ranges differ from the stored ones, their difference requires the separate range bound in §5.4.

Since every stored normalized policy is rational under this convention, the game is finite, chance/payoffs are rational, and BR consists of finite sums/products/maxima, exact rational certification is mathematically available. An efficient implementation can instead refine interval precision to decide the tolerance comparison. At exact equality with the threshold, intervals can remain inconclusive; exact rational comparison or training to a strict margin resolves that boundary case. If an upper bound remains above the target, it has not passed; a lower feasible-response value below target is insufficient.

### 5.2 Lemma: pairwise continuation error implies correctly scaled hand-value error

Fix a complete continuation policy and boundary factors. Suppose an approximate pair matrix satisfies

\[
|W_i(f,x,y)-\widehat W_i(f,x,y)|\le\delta_f
\]

for every compatible pair. From (2.1) and nonnegative weights,

\[
|g_i(h_i)-\widehat g_i(h_i)|
\le
\sum_{h_{-i}}M_fa_{-i}\delta_f
=m_i(h_i)\delta_f.
\tag{5.1}
\]

Multiplying by the own factor and dividing by $Z_f$ gives

\[
|F_i-\widehat F_i|\le\mu_{i,f}\delta_f.
\tag{5.2}
\]

For $m_i(h_i)>0$, division gives

\[
|\nu_i-\widehat\nu_i|\le\delta_f.
\tag{5.3}
\]

At a zero-probability own-hand event, this last statement concerns the explicit counterfactual extension of $\nu$, not an ordinary conditional expectation. If $m_i=0$, only the unnormalized zero statement is meaningful.

Summing (5.2) over hands proves $|U_i-\widehat U_i|\le\delta_f$. Applying the parent lift (2.9) proves the corresponding outer-CFV bound with its actual prefix counterfactual mass. Thus a local error in normalized equity or conditional payoff cannot be copied into the parent unnormalized CFV without the relevant mass factor.

This lemma concerns approximating a **specified policy's** payoff matrix. A small equilibrium gap alone does not imply a uniform pairwise bound on that matrix or on every hand's CFV.

### 5.3 Lemma: weighted CFV backups propagate error without a branching-factor shortcut

For a fixed opponent policy and responder/player $i$, define the exact counterfactual prefix mass

\[
\omega_i(v,h_i)=
\sum_{h_{-i}}\chi_v(h_0,h_1)r_{-i}(v,h_{-i}).
\tag{5.4}
\]

Its elementary conservation laws are:

- At an $i$-decision, $\omega_i(va,h_i)=\omega_i(v,h_i)$ for every legal action; own reach is excluded.
- At an opponent decision, $\sum_a\omega_i(va,h_i)=\omega_i(v,h_i)$ because the opponent's legal action probabilities sum to one.
- At chance, $\sum_S\omega_i(vS,h_i)=\omega_i(v,h_i)$ because the exact conditional chance support sums to one for every private pair.
- At the normalized root, $\sum_{h_i}\omega_i(e,h_i)=1$.

Let $E_i(v,h_i)$ be an absolute error envelope and $\eta_i(v,h_i)$ bound new arithmetic error injected at this node. Terminal contraction errors initialize $E$; subsequent backups obey

\[
E_i(v,h_i)\le
\begin{cases}
\eta_i+\sum_a\sigma_i(v,h_i,a)E_i(va,h_i),
 &\text{fixed-policy own node},\\
\eta_i+\max_aE_i(va,h_i),
 &\text{BR own node},\\
\eta_i+\sum_aE_i(va,h_i),
 &\text{opponent node},\\
\eta_i+\sum_SE_i(vS,h_i),
 &\text{chance node}.
\end{cases}
\tag{5.5}
\]

**Proof.** The linear cases follow by the triangle inequality. For the max case use

\[
\left|\max_a x_a-\max_a y_a\right|
\le\max_a|x_a-y_a|.
\tag{5.6}
\]

Now suppose every terminal error is at most $\omega_i(z,h_i)\delta$ and there is no internal arithmetic error. The mass laws and induction in (5.5) imply
$E_i(v,h_i)\le\omega_i(v,h_i)\delta$ at every node. Therefore the root scalar error is at most $\delta$, both for a fixed profile and for an exact BR.

This proof is needed because the vector CFV backup uses unweighted sums at opponent and chance nodes. One cannot simply call these sums convex combinations or bound them by the maximum raw child error. They become nonexpansive only after accounting for their mass conservation.

With inherited terminal error at most $\omega_i(z,h_i)\delta$ and internal injections $\eta_i(v,h_i)\le\omega_i(v,h_i)\epsilon_v$, (5.5) is itself an executable error-bound dynamic program. A crude consequence is root scalar error at most $\delta+\sum_{\text{internal depths }d}\max_{v\text{ at }d}\epsilon_v$. If at most $L_{\rm inj}$ internal levels inject error and every $\epsilon_v\le\epsilon$, this is at most $\delta+L_{\rm inj}\epsilon$. Alternatively, count terminal contractions as injection levels and include them explicitly. This is a level-count bound, not multiplication by the total number of nodes. A tighter calculation follows (5.5) directly.

For pairwise continuation replacements on a disjoint boundary cut $\mathcal E$, with errors $\delta_e$ and exact trunk operations, every fixed profile has error at most

\[
\sum_{e\in\mathcal E}\Pr_\sigma(e)\delta_e
\le\max_{e\in\mathcal E}\delta_e.
\tag{5.7}
\]

For a BR, take the supremum over the responder's possible entry reaches. For nested cuts, account for the sum of injected errors along a play; do not count a child's already included error a second time in its parent replacement.

### 5.4 Lemma: arithmetic, probabilities, and range normalization

For a reduction $s=\sum_{j=1}^m w_jv_j$, a conservative standard floating-point bound, assuming no unaccounted underflow/overflow and exact input operands, is

\[
|\widehat s-s|\le
\gamma_{2m}\sum_{j=1}^m|w_jv_j|,
\qquad
\gamma_k=\frac{ku}{1-ku},\quad ku<1,
\tag{5.8}
\]

where $u$ is unit roundoff. This follows by writing each rounded operation as its exact result times $(1+\theta)$, bounding products of at most $2m$ such factors, and applying the triangle inequality to the signed sum. A verified balanced reduction with one multiplication per leaf and height $L$ can use the tighter corresponding operation-path bound $\gamma_{L+1}$. Exact operation count, accumulation dtype, and fused operations must match the implementation.

Errors in the operands, including reach products, normalizers, or previously computed values, are additional terms propagated by (5.5). Signed utilities require the sum of absolute product magnitudes in (5.8); cancellation does not justify a small relative-error claim. Integer masks, integer rank comparisons, and exact monetary targets have no floating ambiguity.

For a normalized conditional backup with exact probability vector $p$, implemented normalized vector $\widehat p$, exact values bounded by $M=100$, and child errors $E_a$, write

\[
\sum_ap_av_a-\sum_a\widehat p_a\widehat v_a
=\sum_a(p_a-\widehat p_a)v_a
+\sum_a\widehat p_a(v_a-\widehat v_a).
\]

Consequently

\[
E_v\le\eta_v+100\|p-\widehat p\|_1
+\sum_a\widehat p_aE_a.
\tag{5.9}
\]

If probabilities are not nonnegative and normalized, first define the exact legal policy being certified or account for that defect explicitly. Do not silently treat an almost-stochastic row as exact. R1's chance probabilities are prescribed rationals; (5.9) bounds their numerical representation error, not a change of chance law.

For boundary distributions and any fixed profile,

\[
|U_i^\mu(\sigma)-U_i^{\widehat\mu}(\sigma)|
\le100\|\mu-\widehat\mu\|_1.
\tag{5.10}
\]

The same uniform bound applies to BR optima by (5.6), and hence to half-NashConv exploitability of the same stored profile.

If $\mu=w/Z$, $\widehat\mu=\widehat w/\widehat Z$, with nonnegative weights and both totals positive, then

\[
\begin{aligned}
\left\|\frac wZ-\frac{\widehat w}{\widehat Z}\right\|_1
&\le
\frac{\|w-\widehat w\|_1}{Z}
+\frac{|Z-\widehat Z|}{Z}\\
&\le\frac{2\|w-\widehat w\|_1}{Z}.
\end{aligned}
\tag{5.11}
\]

For normalized range factors and the exact same mask,

\[
\|M(a_0\otimes a_1)-M(\widehat a_0\otimes\widehat a_1)\|_1
\le\|a_0-\widehat a_0\|_1+\|a_1-\widehat a_1\|_1.
\tag{5.12}
\]

Expand the tensor-product difference into two terms and use each factor's unit $\ell_1$ norm to prove (5.12). These inequalities expose the instability of normalizing a tiny compatible mass $Z$. A positive lower bound on $Z$ is required for an interval normalization. Unnormalized counterfactual propagation avoids unnecessary divisions.

For very small reaches, use mantissa/exponent representations or exact power-of-two rescaling while carrying the full scale. Rescaling a stored regret table requires rescaling all future increments consistently. Flushing a nonzero reach or chance product to zero is either explicitly bounded as discarded mass times the utility bound or avoided; it is not a zero-reach rule. A large reduction can be tiled, but its total error includes tile accumulation and the final reduction.

An independent interval certifier is often simpler to specify than a global analytic roundoff count: enclose normalized policy entries, root factors, reach products, terminal contractions, sums, and max backups. Outward rounding plus induction in (1.27), (5.5) encloses the true root BR. Deterministic operation order helps reproducibility, but reproducibility alone is not a numerical bound.

### 5.5 Theorem: a numerical/continuation allowance produces the required certificate

Suppose computed BR estimates satisfy

\[
|\widehat{\mathcal B}_{i,e}-\mathcal B_{i,e}|
\le\delta_i^{\rm BR}.
\]

Then directly from (0.1),

\[
\operatorname{Expl}_e(\bar\sigma)
\le
\frac{\widehat{\mathcal B}_{0,e}+
\widehat{\mathcal B}_{1,e}
+\delta_0^{\rm BR}+\delta_1^{\rm BR}}2.
\tag{5.13}
\]

No baseline policy-value error appears, because the exact two-player zero-sum values cancel in the half-gap. For separate unilateral-gain certificates, use the appropriate upper BR and lower profile-value endpoints as well.

There is a sharper useful statement for a **zero-sum surrogate with the same strategy spaces**. Suppose for every profile $\tau$,

\[
|U_0(\tau)-\widehat U_0(\tau)|\le\delta,
\qquad U_1=-U_0,\quad \widehat U_1=-\widehat U_0.
\tag{5.14}
\]

Maximization is 1-Lipschitz under a uniform value bound, so each fixed-opponent BR optimum changes by at most $\delta$. Therefore

\[
\boxed{
\operatorname{Expl}_{\rm true}(\sigma)
\le\operatorname{Expl}_{\rm surrogate}(\sigma)+\delta.
}
\tag{5.15}
\]

This uses zero-sum cancellation; bounding two deviation gains separately yields the valid but looser $+2\delta$. A bound only on the candidate's nominal payoff, one equilibrium scalar, or one feasible response does **not** establish (5.14). The bound must cover the strategy families explored by BRs. A surrogate that removes all continuation deviations has a different strategy space and needs §6 instead.

For example, if a same-strategy-space surrogate has uniform continuation error $\delta_{\rm cont}$, the boundary distribution error is $\varepsilon_\mu=\|\mu-\widehat\mu\|_1$, and certifier arithmetic errors are $\eta_i$, a sufficient comparison is

\[
\frac{\widehat{\mathcal B}_0+\widehat{\mathcal B}_1+\eta_0+\eta_1}{2}
+\delta_{\rm cont}+100\varepsilon_\mu
\le0.005P_e.
\tag{5.16}
\]

Do not add an error twice if it is already enclosed in a BR endpoint. The exact full-tree baseline has no continuation-model approximation; only actual arithmetic/input bounds remain. One possible *budget choice*, not an achieved result, is candidate gap at most $0.004P_e$ and total verified error allowance at most $0.001P_e$. At preflop those are 0.006 BB and 0.0015 BB, summing to 0.0075 BB.

### 5.6 Lemma: DCFR arithmetic errors and what they do not prove

Let

\[
D_t(x)=
\begin{cases}d_t^+x,&x\ge0,\\d_t^-x,&x<0,\end{cases}
\quad d_t^+=\frac{t^{3/2}}{t^{3/2}+1},\quad d_t^-=\frac12.
\]

This function is continuous at zero and

\[
|D_t(x)-D_t(y)|\le d_t^{\max}|x-y|,
\qquad d_t^{\max}=\max(d_t^+,d_t^-)\le1.
\tag{5.17}
\]

If $x,y$ have the same sign this is immediate. If they straddle zero,
\[
|D_t(x)-D_t(y)|=d_t^+|x|+d_t^-|y|
\le d_t^{\max}(|x|+|y|)=d_t^{\max}|x-y|.
\]

For fixed exact policy weights, if every action CFV at an information set has error at most $e$, the weighted node value has error at most $e$, and the instantaneous regret error is at most $2e$. Let $\zeta_t$ bound that increment error, $\eta_t$ bound newly injected addition/discount arithmetic including discount-factor approximation, and $e_t$ the regret-state error. Then

\[
e_t\le d_t^{\max}(e_{t-1}+\zeta_t)+\eta_t,
\tag{5.18}
\]

\[
e_T\le
\left(\prod_{k=1}^Td_k^{\max}\right)e_0
+\sum_{s=1}^T
\left(\prod_{k=s+1}^Td_k^{\max}\right)
(d_s^{\max}\zeta_s+\eta_s).
\tag{5.19}
\]

The same reasoning handles average-accumulator errors with its nonnegative discount. These are comparisons along a specified policy/value sequence. Regret matching has no uniform Lipschitz bound when the total positive regret approaches zero; tiny regret perturbations can choose very different policies. Thus (5.19) alone does not bound the distance between two entire self-play trajectories.

This is why the final certificate evaluates the actual stored average policy directly. Training roundoff can affect convergence speed or the attained profile, but cannot invalidate an independently correct upper BR certificate for that profile.

### 5.7 Derivation of the weighted-regret connection, without misusing DCFR state

This subsection concerns the exact reach-weighted realization average of the frozen iteration policies. Rounded average accumulators may produce a different stored profile, which is independently certified under §5.1. Let $w_t=t^2$, $W_T=\sum_{t=1}^Tw_t=T(T+1)(2T+1)/6$, and define actual weighted external regret

\[
\mathcal R_i^{w,T}
=\max_{\tau_i}
\sum_{t=1}^Tw_t
\left[U_i(\tau_i,\sigma_{-i}^t)-U_i(\sigma^t)\right].
\tag{5.20}
\]

The behavioral average in (1.3) implements the weighted average realization plan. Expected payoff is linear in each player's realization plan when the other is fixed. Therefore

\[
\mathcal B_i(\bar\sigma_{-i})
=\frac1{W_T}
\max_{\tau_i}\sum_tw_tU_i(\tau_i,\sigma_{-i}^t).
\]

Sum over players and cancel $\sum_tw_t(U_0(\sigma^t)+U_1(\sigma^t))=0$ to obtain

\[
2\operatorname{Expl}(\bar\sigma)
=\frac{\mathcal R_0^{w,T}+\mathcal R_1^{w,T}}{W_T}.
\tag{5.21}
\]

For completeness, the counterfactual decomposition can also be derived directly. For any fixed deviation $\tau_i$, telescoping the effect of replacing own decisions one at a time from the prefix toward the leaves gives

\[
U_i(\tau_i,\sigma_{-i}^t)-U_i(\sigma^t)
=\sum_{I\in\mathcal I_i}r_i^{\tau_i}(I)
\sum_a\tau_i(I,a)\Delta R_i^t(I,a).
\tag{5.22}
\]

Each term uses the deviator's own prefix reach and the original profile's suffix value. The opponent/chance prefix remains inside $\Delta R$, exactly as (1.8) requires. Summing (5.22) with weights $w_t$, then bounding a convex action average and using $0\le r_i^{\tau_i}(I)\le1$, yields

\[
\mathcal R_i^{w,T}
\le
\sum_{I\in\mathcal I_i}
\max\!\left(0,\max_a\sum_{t=1}^Tw_t\Delta R_i^t(I,a)\right).
\tag{5.23}
\]

The telescoping identity follows as well by induction through the same own/opponent/chance backups used above, so no normal-form enumeration is hidden here. This is the counterfactual-regret framework of [CFR], specialized to these exact information sets.

Equations (5.20)–(5.23) explain why reach-weighted averaging is the relevant output and what a true regret-based bound would require. They do not turn the sign-dependent discounted state (1.6) into the weighted sums in (5.23). The specified stopping rule uses BRs and does not assume a numerical convergence rate or a sufficient iteration count.

---

## 6. Conditions for local certificates to imply a global bound

### 6.1 Why separately small street exploitabilities do not compose automatically

Three obstacles must be addressed before making a global claim:

1. A unilateral deviation can change which continuation is reached and with what probability.
2. It can change the deviator's private-hand factor at that continuation, including introducing hands with zero nominal own reach.
3. The local targets use different entry pots. A fraction of a large downstream pot is an absolute BB allowance that can greatly exceed 0.0075 BB.

In addition, a local certificate describes a **fixed stored continuation policy** at a stated boundary distribution. Re-solving to a different profile at a new distribution is not a proof that the originally stored profile was safe there. A best-response test keeps its opponent fixed; it does not let that opponent learn the deviator's hidden choices and re-equilibrate.

The following cut theorem states sufficient conditions without those ambiguities.

### 6.2 Theorem: a disjoint public-cut decomposition

Let $\mathcal E$ be a disjoint public boundary cut: every play enters at most one $e\in\mathcal E$, and the cut does not split an information set. Complete public-history street entries satisfy this information-set condition. Some plays may terminate before the cut.

Fix a complete stitched profile $\sigma$, including every continuation row. Construct a truncated **trunk** game that ends at the cut with the full fixed-policy pairwise payoff matrix
$W_i^{\sigma_e}(e,x,y)$, leaving pre-cut terminals unchanged. This trunk only permits deviations before the cut. Let $d_i^T$ be the maximal unilateral gain in that trunk.

For a trunk deviation $\tau_i^T$, let $p_e^\tau$ be its probability of reaching $e$, with the opponent fixed, and let $\mu_e^\tau$ be the induced conditional private distribution when $p_e^\tau>0$. Define the additional continuation gain against the stored opponent policy:

\[
d_{i,e}(\mu)=
\max_{\tau_i^e}
U_{i,e}^{\mu}(\tau_i^e,\sigma_{-i}^e)
-U_{i,e}^{\mu}(\sigma_i^e,\sigma_{-i}^e).
\tag{6.1}
\]

Terms with $p_e^\tau=0$ contribute zero and require no posterior. Then

\[
\boxed{
d_i^{\rm full}
\le d_i^T+
\sup_{\tau_i^T}
\sum_{e\in\mathcal E}p_e^\tau
d_{i,e}(\mu_e^\tau).
}
\tag{6.2}
\]

Consequently

\[
\boxed{
\operatorname{Expl}_{\rm full}(\sigma)
\le
\operatorname{Expl}_{T}(\sigma_T)
+\frac12\sum_{i=0}^1
\sup_{\tau_i^T}
\sum_{e\in\mathcal E}p_e^\tau d_{i,e}(\mu_e^\tau).
}
\tag{6.3}
\]

**Proof.** Take any full deviation $\tau_i$ and insert a hybrid strategy that uses its deviating trunk but retains $\sigma_i^e$ after every cut entry. The difference between the hybrid and the original profile is at most $d_i^T$. Condition the remaining difference between the full deviation and the hybrid on the mutually exclusive entries $e$. In each entry it is at most the local continuation optimum (6.1) for the distribution actually induced by the deviating trunk. Sum with entry probabilities, then maximize over trunk deviations. Add the two players' inequalities and divide by two. Every continuation can be chosen on its distinct public transcript, so no hidden-hand-dependent public choice is introduced. This proves (6.2)–(6.3).

The supremum in these inequalities is essential. On-policy reach probabilities and on-policy range certificates alone do not bound it.

### 6.3 Sufficient coverage and budget conditions

Suppose for each $i,e$ there is a verified bound $D_{i,e}$ such that

\[
d_{i,e}(\mu_e^\tau)\le D_{i,e}
\]

for **every** boundary distribution produced by an allowed unilateral trunk deviation against the fixed opponent. Then the added term in (6.3) is bounded by

\[
\frac12\sum_i\sup_{\tau_i^T}
\sum_ep_e^\tau D_{i,e}
\le\frac12\sum_i\max_{e\in\mathcal E}D_{i,e}.
\tag{6.4}
\]

The last inequality uses $\sum_ep_e^\tau\le1$ for a disjoint cut. It can be sharpened using actual admissible deviation reach bounds.

If all that is known uniformly is a local **half-gap**
$\operatorname{Expl}_e(\sigma_e;\mu)\le\varepsilon_e$, then
$d_{i,e}(\mu)\le2\varepsilon_e$. A safe added bound from (6.4) is therefore $2\max_e\varepsilon_e$. It is not automatically $\max_e\varepsilon_e$, because the two players' maximizing entry distributions can differ. If the stronger per-player bounds $d_{i,e}\le\varepsilon_e$ are verified uniformly, the added bound becomes at most $\max_e\varepsilon_e$.

For nominal local targets $\varepsilon_e=0.005P_e$, one must still prove the coverage premise and control the absolute expected pots under deviations. Four separate statements of the form $0.005P_e$ do not imply the preflop 0.0075 BB requirement.

Across flop, turn, and river cuts, apply (6.2) recursively. At each level allocate per-player absolute BB budgets and bound their sums along deviation-induced play. Do not sum a suffix certificate again if its bound already includes all deeper strategic errors. A sufficient final allocation, with $L_i$ the resulting worst-case additional continuation gain and $\delta_{\rm num}$ the final certified numerical allowance, is

\[
\operatorname{Expl}_T+\frac{L_0+L_1}{2}
+\delta_{\rm num}\le0.0075\ {\rm BB}.
\tag{6.5}
\]

Every quantity in this inequality must refer to the same fixed stitched profile and the original root chance law. The direct full-root BR test in §4.6 avoids estimating these intermediate worst-case budgets.

### 6.4 A useful R1-specific sufficient condition: per-hand continuation gaps

Fix an exact public boundary $e$ and the opponent's complete policy. A unilateral trunk deviation changes only the deviator's factor $a_i$ at that boundary; the opponent factor $a_{-i}$ is fixed along that same exact transcript. The blocker-conditioned opponent kernel for a known own hand is

\[
\Pr(h_{-i}\mid h_i,e)
=\frac{M_e(h_0,h_1)a_{-i}(h_{-i})}{m_i(h_i)}
\quad(m_i(h_i)>0),
\tag{6.6}
\]

independent of the own factor.

Compute two raw per-hand quantities using this opponent factor:
$g_i^{\sigma_e}$ by fixed-policy evaluation, and $g_i^{\rm BR}$ by the same BR recursion with root weight $M_ea_{-i}$, **without** multiplying by $a_i/Z_e$. This root measure need not sum to one across own hands; each row's conditional normalization is $m_i(h_i)$. Both quantities are defined even on nominal own-range-zero rows.

Define the typewise conditional gain

\[
\Delta_{i,e}(h_i)=
\frac{g_i^{\rm BR}(h_i)-g_i^{\sigma_e}(h_i)}
{m_i(h_i)}\ge0,\qquad m_i(h_i)>0.
\tag{6.7}
\]

Different own hands are distinguishable information sets, so a response can optimize all of them simultaneously. For any shifted own factor with positive entry mass,

\[
d_{i,e}(\mu_e^\tau)
=\sum_{h_i}\mu_{i,e}^\tau(h_i)\Delta_{i,e}(h_i).
\tag{6.8}
\]

This equality follows by conditioning on the own hand and observing that the opponent kernel and stored opponent strategy remain fixed. A verified pointwise bound
$\Delta_{i,e}(h_i)\le D_{i,e}$ on **every** hand with $m_i>0$ therefore covers every unilateral own-range shift. It can be conservative, but it is a genuine sufficient condition.

Another sufficient condition is posterior domination:

\[
\mu_{i,e}^\tau(h_i)\le
\kappa_{i,e}\mu_{i,e}^{\sigma}(h_i)
\quad\text{for every allowed deviation and hand}.
\tag{6.9}
\]

Since the typewise gains are nonnegative, (6.8) implies

\[
d_{i,e}(\mu_e^\tau)
\le\kappa_{i,e}d_{i,e}(\mu_e^\sigma).
\tag{6.10}
\]

No finite domination constant exists if a nominal zero-probability hand can enter under a deviation. Entry-probability changes still require the $p_e^\tau$ bound in (6.3). A nominal range solve that leaves such hands untrained is a valid local solve, but does not by itself meet the global coverage condition.

### 6.5 Counterexample to the unsupported local-to-global inference

The following small auxiliary game is a proof counterexample, **not a modification of R1**. Player 0 privately receives type A or B with equal probability and chooses Out, paying zero, or Enter. After Enter, player 0 chooses Safe or Loot. Type A gets zero either way; type B gets $-1$ for Safe and $+1$ for Loot. Player 1 receives the negative payoff and has no decision.

Consider a stored profile in which A enters and chooses Safe, B chooses Out, and B's off-path continuation is Safe.

- The conditional Enter continuation has only type A, so its exploitability is zero.
- The trunk with fixed Safe continuation is also solved: B would lose by entering.
- Yet B can jointly change its trunk and continuation to Enter then Loot, gaining $1/2$ ex ante. The full profile has half-NashConv exploitability $1/4$.

Thus even zero local residuals at nominal ranges and a solved fixed-continuation trunk can leave a positive global exploitability. The corresponding R1 danger is a hand whose own nominal entry reach is zero while its opponent-compatible counterfactual mass is positive. The all-hands BR and per-hand coverage tests explicitly retain it.

### 6.6 What can safely be reused

The following distinctions complete the continuation contract:

| Reused object | Range dependence | Exact use |
| --- | --- | --- |
| Card masks, integer hand ranks, exact monetary transition templates | None | Read-only arithmetic reuse; keep all history IDs |
| Called-all-in pair payoff matrix | None once cards/commitment are fixed | Exact chance-only terminal kernel; include numerical error if approximated |
| Fixed-profile pair continuation matrix $W^{\sigma_e}$ | Independent of ranges once the whole policy is fixed | Recontract for new factors, preserving prefix scales |
| Fixed-profile $g,F,\nu$ vectors | Depend on weights and their normalization | Recompute or transform with the stated exact factors |
| Equilibrium profile or equilibrium continuation values | Generally depend on both boundary factors | Certify at those factors; require coverage or new certification for reuse |
| Scalar local equilibrium value | Already averages over private types | Insufficient as a universal hand-specific parent payoff |

For fixed policies, the unnormalized scalar $\Phi_i=\sum M_ea_0a_1W_i$ has derivative with respect to the own factor equal to $g_i$. The normalized scalar $U_i=\Phi_i/Z_e$ instead satisfies

\[
\frac{\partial U_i}{\partial a_i(h_i)}
=\frac{g_i(h_i)-U_i\,m_i(h_i)}{Z_e},
\tag{6.11}
\]

where the unconstrained derivative is taken before imposing any simplex normalization on $a_i$. This follows by the quotient rule. It further explains why a normalized scalar, an unnormalized CF vector, and a range-dependent solved policy are different objects. If the policy itself changes with the ranges, (6.11) is only the fixed-policy partial derivative; it is not a claim of differentiability of an equilibrium-selection map.

---

## 7. Source audit, references, and completion criteria

<a id="71-governing-archive-and-fresh-mechanics-validation"></a>

### 7.1 Governing archive and historical mechanics validation

**Historical record:** The source identities and reported checks below come from
preparation of this derivation. See [source provenance](../provenance.md) for
current file locations and validation guidance.

The derivation used the three requested source files from the supplied archive. Their SHA-256 fingerprints are:

| File | SHA-256 |
| --- | --- |
| EFG.md | 0f3bfd197e79ed3d5520c776af320149a8a0d9e36ce201e0a07e7123d3e639c7 |
| kernel.py | dcb9d3f0f5ed2ac401816606af1643a50a4d7c3ebcfbfa15b6c59125082c20c2 |
| preflop.json | 135ca851c5db7d0db237422b3e6943ad7b9374b9d2130f54e874f590e277216a |

A fresh execution of the supplied complete validator, using Python 3.12.14 and the command **python3 -u validate.py**, returned exit code 0 and **RESULT=PASS** on November 17, 2026, from 11:29:24 to 11:30:55 Asia/Seoul. The source files were not modified. A separate data comparison also confirmed exact equality of the supplied preflop JSON and the kernel's freshly generated preflop expansion.

The validation scope reported by that run includes exhaustive independently generated reachable betting/control mechanics; all physical five-card evaluations; feasible five-, six-, and seven-card rank/flush semantic classes; complete root private-deal support; full conditional-board supports on the residual decks exercised by the validator; history/information-set separation; runout scheduling/probabilities; and settlement algebra. The specification's exact combinatorial construction and best-five composition lift those checks as described in R1 §9.

This is **not** literal enumeration of every card-labeled complete game history, a test of a GPU DCFR implementation, or an equilibrium/exploitability certificate. This document derives such an implementation and certificate; it does not report a trained strategy.

### 7.2 Source-to-derivation mapping

| Normative obligation | Source | Derived here |
| --- | --- | --- |
| Physical cards, canonical holes/flop, labeled turn/river | R1 §§2.1–2.4; K: chance_probability, chance_events, deal | §§0.3–0.4, 1.1.5, 2.3, 3.2, 4.3–4.5 |
| Full public-history infosets and perfect recall | R1 §7; K: Game, observation, infoset_key | §§0.3–0.4, 1.1.1, 1.2 |
| Half-up → minimum → snap → dedup | R1 §4.1; K: raw_targets, resolve, actions | §1.1.9 and each street compiler |
| Redundant caps and exact ledger updates | R1 §§3.3–3.4, 6; K: cap, step, _settle | §§1.1.9, 2.5, 3.3, 4.2 |
| Complete preflop action table and origins | R1 §5; preflop.json; K: preflop_tree | §§3.3, 4.2 |
| Net fold/showdown utility and best-five ordering | R1 §8; K: payoff, rank_five, evaluate | §§1.1.6–1.1.8 |
| All-in closure without skipped-street decisions | R1 §§2.4, 3.4, 6.3; K: runout_probability, advance_board | §§2.3, 3.2, 4.4 |
| CFR/DCFR method definitions | Primary papers [CFR], [DCFR] | §§1.1.1–1.1.4, 5.6–5.7 |
| R1 tensor specialization and certification/error proofs | Derived from the above finite EFG and displayed recurrences | §§0–6 |

### 7.3 Primary method references

**[CFR]** Martin Zinkevich, Michael Johanson, Michael Bowling, and Carmelo Piccione. *Regret Minimization in Games with Incomplete Information*. NeurIPS/NIPS 2007. [Primary paper](https://papers.neurips.cc/paper_files/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf).

**[DCFR]** Noam Brown and Tuomas Sandholm. *Solving Imperfect-Information Games via Discounted Regret Minimization*. AAAI 2019. [Primary paper](https://arxiv.org/pdf/1809.04040). [Publisher record and DOI](https://doi.org/10.1609/aaai.v33i01.33011829).

The papers supply the named regret-minimization framework and discount-family definition. The exact R1 compiler, tensor identities, continuation interfaces, numerical bounds, and local-to-global conditions in this document are derived explicitly rather than delegated to an unnamed evaluator or equilibrium oracle.

### 7.4 What an executed solution must return

For each claimed river, turn, flop, or preflop solve, retain the following together:

1. The exact public entry key and governing source fingerprints; its fixed $P_e$.
2. The boundary factors, their normalization/scales, $Z_e$, and whether they are locally supplied or induced by stated ancestor policies.
3. The complete stored average policy, including legal off-path fallback rows, with full-history indexing.
4. The DCFR parameters, iteration/update convention, initialization, number of iterations, and actual arithmetic interpretation.
5. The two BR upper values, optional lower values/response policies, the two unilateral gains when computed, and the final half-NashConv upper bound in BB and as a fraction of $P_e$.
6. Every numerical/continuation allowance used in the stopping comparison, including any range-coverage assumptions needed to stitch separate solves.

An ordinary river/turn/flop claim passes only its corresponding R0/T0/F0 test for the stated local game. The complete original-game claim passes P0 under the original private chance law. If the test has not passed, the result remains a candidate profile, regardless of how small a training diagnostic appears.
