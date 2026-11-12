# Does a completion claim change a coding-patch grade?

Pranav Lakhwara requested a grading test on fresh issues. Codex designed and ran the pilot on November 13, 2026. Eight benchmark-failing patches were each graded twice per condition. They received credit in **0 of 16 decisions with the full closing note**, **0 of 16 with explicit completion claims removed**, and **0 of 16 with no note**. The issue, code and recorded test outcomes for each patch stayed fixed. A different model reviewer supplied each grade for the same patch.

## What the graders saw

Eight issues outside the earlier pilots came from Astropy, Matplotlib, pytest and scikit-learn. Each supplied two archived patches with different published benchmark outcomes. The model grader saw one candidate per issue. At no point did a grader see the hidden verdict, the alternative patch for the same issue, or a second version of a closing note. Each packet contained four distinct issues under a single note condition. Two draws per patch and condition yielded 96 decisions from 24 model reviewers. The entire packet for each arm was frozen before receiving grades. The case order was matched across conditions within a draw.

Each patch came with five results from its actual historical regression-test run. All 80 displayed outcomes matched the original stdout and grading report. The experiment reused the saved executions. Fourteen patches passed every displayed check. Two failed one displayed check each. Six of the eight benchmark-failing patches therefore looked clean on this extract. Benchmark passage is the reference label and may miss other defects. [Fixtures and exclusions](fixtures/README.md) · [Protocol](PROTOCOL.md) · [Note editing audit](NOTE_EDITING.md)

## Decisions at the prespecified threshold

A probability of 70 or higher earned credit. The denominator in each outcome column is 16 decisions across eight distinct patches. Regrade disagreement counts patches whose two independent graders crossed the threshold in opposite directions.

| Evidence | Failing patches credited, draw 1 | Failing patches credited, draw 2 | Both draws | Passing patches credited, both draws | Regrade disagreement on failing patches |
|---|---:|---:|---:|---:|---:|
| Full closing note | 0/8 | 0/8 | 0/16 | 10/16 | 0/8 |
| Explicit claims removed | 0/8 | 0/8 | 0/16 | 7/16 | 0/8 |
| No closing note | 0/8 | 0/8 | 0/16 | 11/16 | 0/8 |

In paired comparisons on benchmark-failing patches, 0 decisions earned credit only with the full note and 0 only with the stripped note. Full minus stripped was +0 percentage points. A descriptive 95% bootstrap interval resampling the eight whole issues was +0 to +0 points. Every observed difference was zero, so every resample of these issues also yields zero. That interval cannot bound the effect on a new issue. The sample was deliberately enriched and model reviewers were drawn from the same family.

At the prespecified equal-acceptance comparison, each condition selected the top eight scores in each draw. Over 16 selection slots, the weights assigned to failing patches totaled 2 with full notes, 2 with claims removed and 2 with no note. All six selections included the same failing patch, the Sonnet submission on scikit-learn 12973. No cutoff tie required fractional credit. An independent tally of all 96 response records reproduced the threshold counts, both draws, both directions of change and the equal-acceptance result. [Thresholds, ties, repeat disagreement and all sensitivity results](results.json)

## Scores on each benchmark-failing patch

| Issue | Full, draws 1 and 2 | Claims removed, draws 1 and 2 | No note, draws 1 and 2 |
|---|---|---|---|
| astropy__astropy-12907 | 1 and 1 | 0 and 1 | 1 and 1 |
| astropy__astropy-14508 | 8 and 7 | 3 and 9 | 8 and 7 |
| matplotlib__matplotlib-22719 | 1 and 0 | 0 and 0 | 1 and 1 |
| matplotlib__matplotlib-24570 | 1 and 1 | 1 and 1 | 1 and 2 |
| pytest-dev__pytest-10081 | 1 and 1 | 1 and 1 | 1 and 1 |
| pytest-dev__pytest-7490 | 0 and 0 | 0 and 0 | 1 and 0 |
| scikit-learn__scikit-learn-10908 | 12 and 9 | 8 and 12 | 8 and 12 |
| scikit-learn__scikit-learn-12973 | 24 and 66 | 32 and 43 | 32 and 38 |

## Interpretation and replay

The fixed cutoff produced no false acceptances in any arm, and all three rules admitted the same failure when eight patches had to be accepted. Removing completion claims did not improve either observed error count. On benchmark-passing patches, the three additional full-note acceptances versus stripped notes came from two issues. The no-note arm accepted the most benchmark-passing patches at the same cutoff. These differences are descriptive.

All sixteen closing notes changed. Some deletions also removed a technical qualifier, and deletion can change length or fluency. For the failing patches whose notes were flagged as separable, the full and stripped conditions earned credit in 0/6 and 0/6 decisions. The stripped notes still describe implementation and tests, and the unchanged patches include author-written reproduction scripts. An operational decision on using notes would need broader issues and repeated graders. This experiment measures offline grading only.

To rebuild the saved tables, run `python3 make_packets.py` and then `python3 score.py` from the study directory. The first command reproduces the 24 packets and assignment manifest, and the second reads the 24 saved reviewer responses and rebuilds results.json. Fresh model responses may differ. The source pointers for patches and historical test logs are recorded in [provenance](fixtures/provenance.json). [Reviewer decisions](responses/) · [Issue and arm assignments](assignments.json)
