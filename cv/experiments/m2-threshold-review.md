# M2: reviewing the confidence threshold

Date: September 27, 2026. Decision: **keep the detector default at 0.25**.
This experiment uses the saved predictions from [20secplay](m2-20secplay.md).
No model, inference size, or detector code changed.

## What we reviewed

The assistant inspected enlarged crops from 20 sampled frames. These labels are
provisional visual judgments, not human-approved ground truth. Eleven frames have
clear basketball candidate judgments: 11 correct predictions and 2 incorrect ones
on players' arms. One repeated opening image and eight uncertain frames were
excluded. A missing prediction in an uncertain frame is not automatically a miss.
Hoop predictions were not scored in this experiment.

[20secplay-review.json](20secplay-review.json) records each judgment and exclusion.
Candidate index 0 means the first **basketball** prediction in that frame; hoop
predictions do not count toward this index. The prediction-file SHA-256 checksum
binds labels to the exact log, so changed predictions cannot silently reuse them.
The video checksum records which input was reviewed.

Earlier frames form the tuning group (8 reviewed frames); later frames form the
checking group (3 reviewed frames). Both groups come from the same already-viewed
clip. This is an exploratory comparison, not an independent blind test.

## Results and decision

We compared five thresholds on the tuning group:

| Threshold | Correct kept | Incorrect kept | Correct removed |
| --- | --- | --- | --- |
| 0.25 | 8 | 2 | 0 |
| 0.35 | 7 | 1 | 1 |
| 0.40 | 7 | 0 | 1 |
| 0.50 | 4 | 0 | 4 |
| 0.60 | 3 | 0 | 5 |

We selected 0.40 as a candidate because it removed both observed false alarms
while losing fewer correct predictions than 0.50 or 0.60. Then we compared only
the baseline and this candidate on the later checking group:

| Threshold | Correct kept | Incorrect kept | Correct removed |
| --- | --- | --- | --- |
| 0.25 | 3 | 0 | 0 |
| 0.40 | 2 | 0 | 1 |

The higher cutoff removed a correct low-confidence prediction with no observed
false-alarm benefit in the checking group. Evidence is too limited to justify
changing the default. This does not prove 0.25 is optimal; it explains why we
kept it for now.

## Understand the measurements

- **Confidence cutoff:** the minimum model score allowed to remain. A higher
  cutoff filters predictions; it does not teach the model to recognize balls.
- **Precision here:** correct retained candidates / all retained candidates,
  restricted to our reviewed examples. This is not full-video precision.
- **Retention:** correct retained candidates / correct candidates in the saved
  baseline. This is not recall. We have not counted every visible real ball.
- **Recall:** would require labeling visible objects even when the model missed
  them. Ground-truth boxes and an overlap matching rule are also needed for a
  reproducible detection benchmark. We have neither in this small experiment.

The evaluator reuses saved boxes and filters their scores. It does not rerun
YOLO or test how rerunning inference could affect postprocessing. It cannot
score thresholds below 0.25 because those candidates were never saved.

## Reproduce from the project root

```powershell
.\.venv\Scripts\python.exe cv/src/evaluate_review.py --split tune
.\.venv\Scripts\python.exe cv/src/evaluate_review.py --split check --thresholds 0.25 0.40
.\.venv\Scripts\python.exe -m unittest discover -s cv/tests -v
```

Read `load_review()` first: it loads labels and checks they match the saved log.
Then read `score_threshold()`: it counts which correct and incorrect predictions
survive a cutoff. `main()` handles command-line options and prints the table.
No new dependencies are required. The unit tests use tiny invented examples to
check metric arithmetic, cutoff equality, undefined fractions, split/exclusion
handling, changed logs, and incomplete labels.

Labels and this report can be committed; footage and output files stay local.
The default command requires the original ignored prediction log. A regenerated
log with a different checksum needs a fresh review; do not just replace the hash.

## Before moving to tracking

Confirm the provisional candidate judgments by viewing the original footage,
and label ambiguous frames where the ball is actually visible. Then evaluate a
30-60 second clip from the intended camera setup, including visible-ball misses.
M2's pipeline runs, but its detection-quality checkpoint is still pending.
