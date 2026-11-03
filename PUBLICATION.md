# Publication record and route

Author: Vinsy Moyya. ORCID: https://orcid.org/0009-0003-0042-3556 (supplied by the author; also linked from the GitHub profile).

This package supports a research-software release and an accompanying technical note. Its theory builds on established work. A peer-reviewed novelty claim, a solution of a famous open problem, and general real-world performance are not established.

## GitHub

Review the completed code, declared experiment, actual result table, licenses and author metadata. Publish a dedicated repository under `vinsymoyya` after local validation. Create a tagged software release containing the source and checksummed result archive. Run hosted CI and distinguish its result from the local test result. Set topics appropriate to the code, such as `inverse-problems`, `experimental-design`, `uncertainty-quantification`, `scientific-machine-learning` and `exact-arithmetic`.

## DOI and ORCID

[Enable the repository in Zenodo](https://help.zenodo.org/docs/github/) and [archive a GitHub release](https://help.zenodo.org/docs/github/archive-software/github-upload/). Inspect the generated software record, author, ORCID, license, version and actual DOI. Do not put a placeholder DOI in the citation file. Add the verified DOI to `CITATION.cff` and the README in a later release.

ORCID is a researcher record, not a journal or peer-review system. Use [Works → Add DOI](https://support.orcid.org/hc/en-us/articles/360006973133-Add-works-to-your-ORCID-record) after the archive exists, or add the software URL manually. The author controls visibility and must authenticate to make the account change. No ORCID record has been changed merely by writing this file.

## Technical note

The methods, proofs, scope, related work and generated result report form the manuscript source. A public technical note is citable as an unreviewed output; it must retain that status. Before selecting a journal, obtain external mathematical and novelty review and broaden the evidence to match the chosen venue's requirements.

## Credential handling

Use `gh auth login --hostname github.com --web` for CLI access. Do not paste tokens in chat or save them in this repository. GitHub, Zenodo and ORCID authentication are separate. Never infer that a successful local build means the repository, DOI or ORCID work is already public.
