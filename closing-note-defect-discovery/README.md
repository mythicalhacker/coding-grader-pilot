# Do closing notes help reviewers find defects?

On the same **six of eight** SWE-bench Verified issues, a reviewer who saw the authors' last verification commands and outputs found an issue-related defect, and a different reviewer who also saw their closing notes found one. Neither condition found an issue-related defect on the other two. All 16 proposed tests ran and passed on the original maintainers' fixes.

The reviews and test executions took place on November 13, 2026. The patch pairs, commands, outputs and notes are from the October 2024 Claude 3.5 Sonnet and Haiku archive submissions. Pranav Lakhwara requested the comparison. Codex designed and executed the pilot, including the packet assignment and test replays. Sixteen fresh Codex model-reviewer contexts each saw one packet. Separate model scorers assessed relevance after execution.

## What the comparison measured

A reviewer saw the issue, both candidate diffs and both authors' historical commands and outputs. Only the treatment reviewer also saw the original closing notes. Both got the same instructions and one proposed behavioral test, with no tools for trying or revising that test. Candidate order was held fixed within each pair and balanced across issues within each repository. Reviewers had no benchmark verdict, maintainer fix, or access to their counterpart's work. They could see whether their own packet contained notes. The reviewers had the same test budget; the note packets contained more input text.

Each proposed test ran unchanged in four fresh Python processes, against the original repository, candidate A, candidate B and the maintainer fix. A qualifying test had to pass on the maintainer fix and expose a candidate's failure on behavior required by the issue. We counted an issue only once per condition. Two scorers divided the anonymized cases by repository. Another scorer independently assessed all 16 tests. The second pass agreed on every label. Scorers could see the code variants and execution outcomes; they had no notes or treatment key. Some SymPy warning paths still exposed the historical patch author's name. A second execution of all 64 replays reproduced every exit status. [Repeat-run check](replay-check.json) · [Locked protocol](PROTOCOL.md) · [Paired results](results.json) · [Archived requests and source pins](inputs/source-manifest.json) · [Django source pins](infra-django/source-pins.json)

| SWE-bench issue | Commands and outputs | Same evidence plus notes | What the tests established |
|---|---|---|---|
| SymPy 12419 | Outside reported behavior | Outside reported behavior | Both candidates miscounted selected entries of an identity matrix. The issue concerned the sum over the whole matrix. |
| SymPy 14531 | Found | Found | Generated Python failed to reconstruct a symbolic equality. |
| SymPy 14976 | Found | Found | A candidate lost precision converting a rational number for numerical evaluation. |
| SymPy 15809 | Found | Found | A candidate reversed the expected results for the minimum and maximum of an empty input. |
| Django 11211 | Found | Found | Neither patch retrieved a related object when its UUID was stored as unhyphenated text. The maintainer fix retrieved it. |
| Django 11532 | Outside reported behavior | Outside reported behavior | The tests detected a change in email subject encoding. Both supplied an ASCII Message-ID, bypassing the reported hostname failure. |
| Django 11740 | Found | Found | A generated migration omitted the dependency needed when converting a UUID field into a foreign key. |
| Django 12193 | Found | Found | An array of checkboxes failed to respect the supplied rule for checking individual boxes. |

The paired difference was **0/8**. Six issues were found by both reviewers, zero only by the commands reviewer, zero only by the notes reviewer, and two by neither. All 16 tests also failed on at least one candidate. Counting any difference from a maintainer fix would have produced 8/8 in each condition. The stricter result measures discovery of the reported defect.

## What the result can support

The sample deliberately selected cases with authentic paired records and different published benchmark outcomes. All eight happened to have the same archival benchmark winner, Sonnet. One of those winning patches failed both independent Django UUID tests. The November run measures defect discovery by model reviewers on archived code. It does not compare the capabilities of today's coding agents, estimate a general effect of notes, or measure a training effect. There was one reviewer per issue per condition, shared model provenance and potential prior exposure to public problems. The sample includes four issues per repository and offers little information about small effects or harder cases.

## Replay and inspect

The assignment files link every packet to its case and condition. Raw proposals are in `responses/`. `runs-sympy.json` and `runs-django.json` contain the process outcomes and SHA-256 digests of the exact scripts. The `audit/` directory holds masked scoring inputs and all three sets of decisions. These commands rerun the checks from the saved inputs; fresh model sampling may produce different proposals.

1. Restore the SymPy trees using `python restore_sympy.py /tmp/notes-sympy-trees`. Use Python 3.8.20 with mpmath 1.1.0 for the historical source. Follow the [Django restoration instructions](infra-django/README.md) for its Python 3.10.20 environment and source trees.
2. Run `python run_probes.py sympy --trees /tmp/notes-sympy-trees --python /path/to/sympy-env/bin/python` and the equivalent `django` command with the Django trees and environment.
3. Run `python summarize.py` to reproduce the issue-level counts from saved scores, assignments and test digests. Use `python prepare_packets.py sympy` or `django` to verify packet construction. Use `python mask_audit.py sympy` or `django` to reconstruct the scoring input.

## Source and release notes

The [historical outcome records](historical-outcomes.json) identify the archived submissions. The source manifests identify the public issue texts, patches, and commands. Historical patch excerpts retain the upstream notices. [Django](licenses/Django-LICENSE.txt) · [SymPy 12419](licenses/SymPy-12419-LICENSE.txt) · [SymPy 14531, 14976](licenses/SymPy-14531-LICENSE.txt) · [SymPy 15809](licenses/SymPy-15809-LICENSE.txt)

Local filesystem prefixes in the execution logs and scoring packets were shortened for this release. The original reviewer inputs and proposed tests retain their recorded hashes.
