# Inverse Witness: checkable ambiguity and the next measurement in bounded inverse physics

Vinsy Moyya · [ORCID 0009-0003-0042-3556](https://orcid.org/0009-0003-0042-3556)

Research software and technical note, version 0.1.0, 3 November 2026. This is a synthetic research pilot. It does not resolve a famous open conjecture or establish a new general theory of inverse problems. External scientific review is pending.

## Research question and contribution

Given incomplete measurements of a physical system, can a reconstruction system distinguish an unsupported answer from a quantity that is determined by the available data? If a quantity remains ambiguous, which single measurement should be acquired next?

Our contribution is a small reproducible implementation and benchmark joining three outputs: an admissible pair of conflicting physical states; an exact, solver-independent bracket on a requested linear quantity; and a finite-candidate minimax decision for the next measurement. Floating-point optimization searches for certificates. A separate standard-library rational checker verifies every reported objective bracket. This is an engineering and benchmark contribution built on established strict-bounds, optimal-recovery, and worst-case sensing ideas. The combination's novelty remains provisional until reviewed against broader prior work.

## 1. Assumptions

Let the source vector be $x\in[0,1]^n$. Its coordinates represent declared bounded source amplitudes, not an unknown distributional prior. Observe $y=Ax+e$, where $|e_i|\leq\epsilon_i$. All stored matrix entries, readings, bounds and query coefficients are rational numbers. Define the nonempty feasible polytope

$$F_y=\{x\in[0,1]^n:Ax\leq y+\epsilon,\;-Ax\leq-y+\epsilon\}.$$

We ask for a scalar physical quantity $q(x)=c^\top x$. Neither the true source nor the next reading is available to the sensor selector. Synthetic ground truth is used by the evaluator to generate observations and measure realized performance.

The source box and the noise budget are substantive physical assumptions. A valid certificate cannot rescue a false source bound, wrong boundary conditions, unmodeled nonlinearity, or underestimated noise. The checker establishes a mathematical claim about the encoded operator; physical provenance must also be checked.

## 2. Exact outer bounds from inexact dual candidates

Write $F_y=\{x\in[0,1]^n:Bx\leq b\}$. For any nonnegative vector $\lambda$, including rounded floating-point solver multipliers, set

$$U(c,\lambda)=b^\top\lambda+\sum_{j=1}^n\max\{0,c_j-(B^\top\lambda)_j\}.$$

**Proposition 1 (box-support certificate).** Every $x\in F_y$ satisfies $c^\top x\leq U(c,\lambda)$.

**Proof.** Decompose $c^\top x=\lambda^\top Bx+(c-B^\top\lambda)^\top x$. Nonnegative multipliers give $\lambda^\top Bx\leq\lambda^\top b$. Each remaining coordinate is bounded by its positive part because $0\leq x_j\leq1$. Summing proves the bound. All checker operations are exact rational additions, products and comparisons. No approximate dual equality is assumed. □

A rational feasible witness $x_w$ also gives $c^\top x_w\leq\sup_{F_y}c^\top x$. We publish both numbers, so their difference is an exact optimization-gap bound. A failed or loose certificate is not called optimal. Applying the construction to $-c$ gives the lower endpoint. Rounded primal points are used only after exact feasibility checking; when necessary they are blended toward an exactly checked strict interior point. Search may fail on degenerate polytopes, in which case the software raises an error rather than relaxing feasibility.

## 3. What cannot be recovered from the existing data

Let $L=\min_{F_y}c^\top x$ and $U=\max_{F_y}c^\top x$. Compactness gives attained endpoints; convexity gives every intermediate scalar value.

**Proposition 2 (conditional minimax error).** At this fixed observation, the smallest worst-case absolute error of any scalar point estimate is $(U-L)/2$, attained by $(L+U)/2$.

**Proof.** Any estimate $z$ has $\max\{|z-L|,|z-U|\}\geq(U-L)/2$. The midpoint attains that value for every quantity in $[L,U]$. □

Two checked witnesses with query values $l_w\leq u_w$ prove a lower bound $(u_w-l_w)/2$ on that unavoidable error even when the outer endpoints are not exact optima. This is a fixed-data worst-case statement. It is not a claim that a learned estimator must have large average error under every probability distribution.

These propositions are elementary consequences of established optimal recovery and strict bounds. They are included to make the implementation's guarantees explicit, not claimed as novel theorems.

## 4. Eliminating the unknown future measurement

A candidate sensor has row $a^\top$ and future observation $z=a^\top x+\nu$, $|\nu|\leq\eta$. Let $F_{y,z}=F_y\cap\{x:|a^\top x-z|\leq\eta\}$ and consider the largest posterior query width over all attainable future readings.

**Proposition 3 (one-step width LP).** This width equals

$$W(a)=\max_{u,v\in F_y}\{c^\top(u-v): |a^\top(u-v)|\leq2\eta\}.$$

**Proof.** Any pair sharing a reading has sensor intervals $[a^\top u-\eta,a^\top u+\eta]$ and $[a^\top v-\eta,a^\top v+\eta]$ that intersect, hence satisfies the additional inequality. Conversely any pair satisfying that inequality shares the reading $z=(a^\top u+a^\top v)/2$. The extremal query difference for a fixed reading is its posterior width. Taking maxima in either order therefore gives the same result. Compactness ensures attainment. □

The displayed optimization is a linear program in $2n$ box-constrained variables. Enumerating a finite candidate list gives the optimal single measurement for this objective. It does not solve unrestricted nonlinear experimental design or a multi-step sensing problem.

For candidate brackets $L_j\leq W(a_j)\leq U_j$, select $k=\arg\min_jU_j$. Then

$$0\leq W(a_k)-\min_j W(a_j)\leq U_k-\min_j L_j.$$

The right side is a checkable decision-regret upper bound. The worst-case posterior minimax point-estimation error is $W(a_k)/2$. A realized reading can reduce uncertainty more than this worst-case prediction, never more slowly than its valid upper bound allows.

## 5. Why a familiar sensor score can choose poorly

A small analytic example distinguishes the objectives. Let $0\leq x_1,x_2\leq1$, $|x_1+x_2-1|\leq0.1$, and ask for $x_1$. Compare sensors $a_1=(1,0)$ and $a_2=(100,100)$, both with future error bound $0.05$.

Reading $a_1$ makes the worst-case query width $0.1$. Reading $a_2$ leaves width $1$: the states $(1,0)$ and $(0,1)$ have identical readings. With the ridge used in our D-optimal heuristic, the very large redundant row can nevertheless score higher. This illustrates that whole-state covariance objectives and a bounded-noise query objective differ. It is not a claim that D-optimal design is generally defective.

## 6. Physical models

### Continuous steady heat-source inversion

On $s\in[0,1]$, solve $-u''(s)=f(s)$ with $u(0)=u(1)=0$. The source is piecewise constant on 16 equal cells and each cell amplitude belongs to $[0,1]$. A temperature sensor measures $u(s_i)$ in nondimensional units. The exact Green function is $G(s,t)=\min(s,t)[1-\max(s,t)]$ and

$$A_{ij}=\int_{j/16}^{(j+1)/16}G(s_i,t)\,dt.$$

At rational sensor positions these integrals are rational; the software integrates the two quadratic antiderivatives exactly. There is no quadrature or finite-difference error for this specified source class. Initial sensors are at $1/8,3/8,5/8,7/8$; 16 candidate positions are the odd multiples of $1/32$.

This exact continuum forward map still restricts the unknown source to a finite-dimensional class. Guarantees do not extend to arbitrary subcell source variation. Grid refinement alone is not a proof of continuum coverage for a larger source class.

### Grounded resistor network

Use a $4\times4$ square network of unit conductances. Each node has four conductances, with missing lattice neighbors connected to exterior ground. The Kirchhoff matrix $K$ has diagonal 4 and off-diagonal -1 for adjacent nodes. For bounded injected currents $x$, voltage satisfies $Kv=x$. We compute $K^{-1}$ with exact rational elimination. Initial readings are the four corner voltages; the remaining 12 nodes are candidates. This is a discrete physical network, not a certified continuum approximation to a material.

## 7. Noise, model error and adaptivity

The pilot uses deterministic uniform noise within the declared box: two budgets per operator family. Certificates require bounded noise, not a Gaussian distribution. Experimental coverage counts check implementation consistency; they are not estimated probabilities of correctness under arbitrary model error.

If $|(A_{true}-A)_{ij}|\leq\Delta_{ij}$ and $0\leq x_j\leq1$, then $|[(A_{true}-A)x]_i|\leq\sum_j\Delta_{ij}$. Adding this amount to $\epsilon_i$ conservatively includes the operator error. The project provides this transformation and a vertex-based test, but does not claim a real instrument's $\Delta$ has been established.

Adaptive selection is valid pathwise when every acquired error satisfies its stated bound. Gaussian errors are unbounded; replacing the pilot noise with Gaussian noise requires an appropriate simultaneous or sequential coverage construction. Reusing a nominal 95% bound independently after adaptive selection does not automatically preserve 95% coverage.

## 8. Declared experiment

The pilot crosses two physical families, two noise levels, two source distributions, four source seeds, and three queries: local source mean, center-minus-edge contrast, and total mean. That gives 96 query instances but only 16 distinct test sources, repeatedly measured and queried. These rows are correlated and must not be treated as 96 independent scientific replicates.

Five next-sensor policies share the same readings, candidates, noise bounds and query: minimax width; a deterministic pseudorandom candidate; regularized D-optimal covariance reduction; maximum separation of the current pair of query witnesses; and maximum sensor-row norm. Each is assessed by the same worst-case width LP and by realized posterior width after a zero-noise future reading. Candidate results are computed before the true next reading is exposed to the selector.

The learning baseline is random-feature nonlinear regression with 64 fixed tanh features plus linear inputs. Only the output weights are trained. It uses 1,024 training sources, 128 separate tuning sources, and 256 separate split-conformal calibration sources from the smooth distribution. Regularization is selected from three fixed values using tuning error. Inputs are scaled from training measurements only. Test seeds are disjoint. This is an inexpensive learned baseline, not a frontier foundation model, PINN, diffusion model or state-of-the-art inverse solver.

At nominal 95% split-conformal coverage, the calibration order statistic is $\lceil257\times0.95\rceil=245$. The corresponding statistical guarantee requires exchangeability with the smooth calibration data. The shifted distribution consists of sparse, nearly binary sources inside the same physical box and deliberately violates that distributional assumption. A failure there illustrates a controlled prior shift; it does not disprove conformal prediction under its assumptions.

All instances, compressed certificates, source vectors, readings, metric rows, configuration hashes and environment versions are retained. The publication's result table must be generated from the completed run, not this protocol.

## 9. What remains research

The immediate release is a reproducible software artifact and technical note. Stronger journal or conference claims need external novelty review, more independent source families, measured instruments with justified model-error bounds, additional inverse solvers, and scaling evidence. A useful next contribution would be an approximate learned sensor selector trained against these exact candidate labels, reporting certified decision regret on genuinely held-out operators. It has not been trained or evaluated here.

Multi-step policies, nonlinear physics, latent nuisance parameters, continuum source classes beyond the cell model, and experimental performance remain open extensions. The release should invite counterexamples and operator contributions rather than claim universal scientific discovery.

## References

1. Philip B. Stark. *Inference in infinite-dimensional inverse problems: Discretization and duality*. JGR, 1992. [DOI](https://doi.org/10.1029/92JB00739). Establishes essential prior art and the risk of overly narrow uncertainty after discretization.
2. Yin Wang, Mario Sznaier, Fabrizio Dabbene. *A convex optimization approach to worst-case optimal sensor selection*. CDC, 2013. [Author-hosted paper](https://robustsystems.coe.neu.edu/sites/robustsystems.coe.neu.edu/files/systems/papers/Yin_CDC13.pdf), [DOI](https://doi.org/10.1109/CDC.2013.6760894). Worst-case bounded-noise sensing is established prior work.
3. Pau Batlle, Pratik Patil, Michael Stanley, Houman Owhadi, Mikael Kuusela. *Optimization-based frequentist confidence intervals for functionals in constrained inverse problems: Resolving the Burrus conjecture*. [arXiv:2310.02461v3](https://arxiv.org/abs/2310.02461v3). Relevant constrained inference; its Gaussian statistical problem differs from our deterministic noise box.
4. David Iagaru, Nina M. Gottschling, Anders C. Hansen, Josselin Garnier. *On Hallucinations in Inverse Problems: Fundamental Limits and Provable Assessment Methods*. [arXiv:2605.13146v1](https://arxiv.org/abs/2605.13146v1), 2026. Direct recent overlap: feasible-set ambiguity and provable hallucination assessment. Our project must be evaluated in that context.
5. Xiaoyu Qiu, Taewon Yang, Zhanhao Liu, Guanyang Wang, Liyue Shen. *Beyond Accuracy: Evaluating Posterior Fidelity of Diffusion Inverse Solvers*. [arXiv:2602.04189v2](https://arxiv.org/abs/2602.04189v2), 2026. Addresses posterior fidelity of stochastic inverse solvers; our certificate addresses deterministic admissibility and one-step measurements instead.

## Research assistance and responsibility

Automated research and coding assistance was used to search literature, derive the implementation, create the synthetic experiments and draft this note. Vinsy Moyya is the named human author and must review and take responsibility for the released claims. Exact certificate checking is a computational check of specified finite problems; it is not external peer review or a proof that the research is novel.
