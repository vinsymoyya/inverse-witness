# Research opportunity and open-source adoption

Research date: 3 November 2026. Decision: build a narrow, checkable inverse-physics toolkit that complements existing scientific ML libraries. The target is useful research software with a defensible technical note. Stars and forks are desired downstream outcomes, not scientific evidence or a forecastable entitlement.

## What the public evidence supports

| Project / ecosystem | GitHub stars displayed | Forks displayed | What it establishes |
|---|---:|---:|---|
| [DeepInverse](https://github.com/deepinv/deepinv) | 842 | 222 | A visible community exists for reusable learned inverse-problem tooling. |
| [PDEBench](https://github.com/pdebench/PDEBench) | 1.2k | 153 | Standardized scientific-ML benchmarks can attract reuse. |
| [NeuralOperator](https://github.com/neuraloperator/neuraloperator) | 4.0k | 941 | Reusable operator-learning methods have a larger adjacent developer audience. |
| [Mathlib4](https://github.com/leanprover-community/mathlib4) | 4.4k | 1.8k | Checkable mathematics has an established contributor ecosystem. |
| [The AI Scientist](https://github.com/SakanaAI/AI-Scientist) | 14.9k | 2.1k | Automated discovery has substantial public attention and strong competition. |

These are displayed GitHub-page snapshots retrieved during this research, including rounded counts. Search and page caches can lag; this is not an authenticated real-time analytics export. The sample is deliberately selected and is not a census. Counts are cumulative, not monthly active developers, current star velocity, genuine experiments, revenue, or proof of unsatisfied demand. No historical growth series was collected, so no momentum claim is made. Raw displayed values and source URLs are retained in [market-snapshot.json](market-snapshot.json).

The smaller inverse-tool communities are a more direct initial audience than the much larger general automated-discovery audience. That is a strategic inference from functional fit, not a causal relationship established by star counts. Fork behavior is particularly relevant only when a fork runs an experiment, contributes a new operator, or submits a verifiable counterexample.

## Where the thin, useful gap is

The gap is between producing a plausible physical reconstruction and demonstrating what the current measurements actually determine. Current work already studies hallucination bounds, constrained uncertainty, posterior fidelity and sensor design. The opportunity is therefore an accessible integration: a researcher can bring a bounded linear operator, ask one physical question, inspect two admissible conflicting states, and verify why one next measurement is preferable.

The research should earn attention through a result someone can reproduce quickly: **two different heat sources fit the same four thermometers; a certificate shows how much a local source estimate can vary; a ranked next thermometer addresses that uncertainty.** The same API should accept a small grounded resistor network so the idea is not tied to a single picture or neural architecture.

This is a packaging and benchmark hypothesis. The bounded search has not established that no existing package offers an equivalent workflow. In particular, the [2026 inverse-hallucination paper](https://arxiv.org/abs/2605.13146v1), [strict-bounds literature](https://doi.org/10.1029/92JB00739), and [2013 worst-case sensing paper](https://doi.org/10.1109/CDC.2013.6760894) constrain any novelty claim. They make a broad “first system to prove inverse ambiguity” claim indefensible.

## Alternatives considered

| Direction | Opportunity | Barrier in this project | Decision |
|---|---|---|---|
| Famous open physics/math conjecture | A valid proof could be highly significant. | No specific unresolved statement, independent proof or demonstrated new result. High chance of spending effort on false novelty or an incomplete argument. | Do not claim a breakthrough without one. |
| General autonomous scientist | Large visible audience. | Broad crowded scope, costly evaluation, weak differentiation from mature projects. | Avoid for the first release. |
| Another PDE prediction model | Clear existing adoption. | GPU/data cost and crowded benchmark comparisons; difficult to substantiate a useful advance immediately. | Potential later integration. |
| Symbolic equation or proof discovery | Checkability and mathematical depth. | Novel discovery and translation into a trusted formal system remain major tasks. | Adjacent route, not the current result. |
| Certified query ambiguity plus a next-measurement benchmark | Specific action, interpretable output, small CPU experiments, exact checking. | Established theory, small synthetic scope, uncertain adoption; external review required. | Selected for a reproducible initial contribution. |

The ranking is a qualitative project decision; no invented confidence score, numeric market size, or expected star count is assigned.

## Intended users and their concrete jobs

1. **Inverse-problem researchers:** test whether an attractive reconstruction answers a physically identifiable question; obtain challenging counterexamples for learned methods.
2. **Experimental-design researchers:** compare a proposed sensor policy with exact single-step labels on small problems; publish certified regret rather than a favorable visual example.
3. **Scientific-ML engineers:** run a lightweight check beside an existing model without retraining it; separate an assumed source class from a learned prior.
4. **Teachers and verification contributors:** reproduce a continuous Green-function example and inspect a certificate without installing the optimizer.

These are proposed user segments. No customer interviews, downloads, traffic, installs, willingness-to-pay measurements, or active-user counts have been collected. Accordingly this document is an ecosystem/opportunity analysis, not a commercial demand validation.

## Positioning and release design

Use the project name **Inverse Witness** and a plain promise: *Check what the measurements leave ambiguous. Choose the next measurement with a verifiable bound.* A naming search found an existing unrelated WitnessBench puzzle benchmark, so that name was rejected to avoid confusion. Do not imply that this project is affiliated with any cited library.

The first screen of the README should contain a real generated figure, a one-command example, one exact certificate command, and measured results with source links. Avoid generic benchmark badges, inflated “SOTA” statements and theorem-first marketing. A benchmark should state whether measurements were merely simulated and whether the reported comparison optimizes its own defining objective.

Use a modular API over rational matrices and box constraints. Include one clean custom-operator example, a declared JSON proof format, tests that reject modified certificates, citation metadata, a versioned release, and a short contribution guide. Let people contribute new operators and failed heuristics without requiring a GPU or proprietary API account. The exact checker should run with the Python standard library.

## A 30-day adoption experiment

These are proposed actions and evaluation criteria, not completed outreach or growth predictions. No automated messages should be sent to maintainers or communities.

| Period | Work | Evidence worth keeping |
|---|---|---|
| Days 1–3 | Publish code, actual result archive, manuscript, and a small tagged software release. Archive a reviewed release on Zenodo. | Anonymous fresh install, successful certificate replay, valid citation metadata and DOI. |
| Days 4–10 | Human-reviewed technical post explaining the ambiguous heat-source example. Seek feedback from relevant inverse and experimental-design communities where sharing is allowed. | Substantive technical comments; independently reproduced results; reported ambiguity or implementation errors. |
| Days 11–20 | Help early users add operators; review counterexamples; document a compatible integration seam with an established library. | External issue/PR activity; user-contributed operator; experiment run in an outside fork. |
| Days 21–30 | Assess adoption and revise the scope based on actual use. | Meaningful new contributors, outside reproducibility records, active experimental forks, citations, and issue resolution time. |

Define an **active experimental fork** as a distinct external fork with a recent commit that changes or adds an operator, policy, dataset or experiment and supplies an execution artifact. Count it once per owner. Exclude the author's forks and cosmetic-only changes. Stars are secondary cumulative bookmarks; measure new stars over a recorded 7-day or 30-day window only after a starting snapshot exists. Define meaningful contributors as distinct outside authors whose reviewed contributions improve code, evidence, documentation or scientific validity.

A practical continuation signal is at least one independent reproduction plus a substantive outside use case. This is a deliberately modest decision criterion, not a promised outcome. If there is attention without use, improve the install/demo. If there is use but no novel scientific result, present the project as research software. If there is a demonstrable limitation in existing methods, design a larger, independently reviewed follow-up study.

## Research publication route

GitHub hosts code; Zenodo can archive a release and assign a DOI; ORCID records works and connects them to the author. An ORCID entry does not peer-review or publish a paper. [Zenodo's official release-archiving guide](https://help.zenodo.org/docs/github/archive-software/github-upload/) and [ORCID's works guide](https://support.orcid.org/hc/en-us/articles/360006973133-Add-works-to-your-ORCID-record) describe the supported steps.

The immediately supportable output is a versioned software release and a clearly labeled technical note. A journal submission needs a venue-specific novelty argument and scope, external proof review, substantially broader validation, and author review. The initial package should carry no invented DOI, accepted-paper badge, journal claim or guaranteed publication language.

## Research stop and pivot conditions

Pause strong novelty claims if an equivalent existing workflow is found. Repair or withdraw a result if the independent checker fails, the original physical instance is not bound to its certificate, source/noise assumptions are violated, or a metric does not replay. Report minimax ties and unfavorable comparisons. Pursue the follow-up learned-policy idea only after the exact benchmark exposes a meaningful speed–regret tradeoff on held-out operators.
