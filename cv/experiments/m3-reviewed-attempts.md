# M3: reviewed attempts and a failed crop experiment

Date: September 28, 2026. We can evaluate the current failure without waiting for
new footage. The analyzer missed both reviewed attempts; the near-hoop detection
gap is a demonstrated upstream limitation.

## What was reviewed

The assistant inspected overview frames and enlarged consecutive hoop sequences.
These are provisional visual labels, not human-approved ground truth or a benchmark.
The outcomes were inferred from visible movement, not the filenames.

| Clip | Reviewed attempt window | Outcome | Evidence |
| --- | --- | --- | --- |
| threemade | frames 70-145 | made | In sampled frames 118-132, the ball enters the net and exits below it. |
| threemiss | frames 98-170 | missed | In sampled frames 132-146, the ball approaches the rim and rebounds upward/left away from it. |

Windows are deliberately broad review intervals, not exact release timestamps.
Only these windows are labeled. Other times and the longer clip have not received
shot-level labels. [shot-review.json](shot-review.json) stores the intervals,
evidence frame indices, reviewer status, and video checksums.

Local visual evidence is in `cv/output/shot-diagnosis/`: each clip has overview,
hoop, and close-up sheets. Close-up sheets contain every second frame in the
listed evidence interval. They do not supply per-frame bounding-box ground truth.

## Comparison with the current pipeline

| Clip | Reviewed attempts | Matched candidates | Missed attempts | Extra candidates in reviewed window |
| --- | --- | --- | --- | --- |
| threemade | 1 | 0 | 1 | 0 |
| threemiss | 1 | 0 | 1 | 0 |

There are no predictions whose outcome can be compared against the labels.
Zero extra candidates does not imply a useful detector: it predicted nothing.
We do not report overall accuracy or a full-video false-alarm rate.

In frames 118-132 of threemade (15 frames), the original log has **zero basketball
predictions** and the tracker has zero observed positions. The same is true in
frames 132-146 of threemiss. The ball is visibly present in the reviewed samples.
This identifies a detector failure before tracking or shot classification: the
tracker cannot select a ball box that does not exist. Presence counts alone would
not prove correctness if detections were present.

## Experiment: enlarge the near-hoop region

Hypothesis: making the ball occupy more model-input pixels might recover it.
We reused the same pinned E-BARD weights, CPU, confidence 0.25, and image size 704.
For each frame, choose the highest-confidence hoop. Let its width be w, center x
be cx, and top edge be t. Crop `[cx-3w, t-3w, cx+3w, t+3w]`, clamp to the image,
run the existing detector on that crop, and map any returned boxes back to the
original image by adding the crop's x/y offsets.

Tested inclusive ranges: threemade 110-140 and threemiss 130-160, 31 frames each.
**Result: zero basketball predictions in both crops at the existing cutoff.**
The exact crop bounds and results are saved locally as
`cv/output/shot-diagnosis/<clip>-crop-experiment.json`.

This one configuration did not help. We did not add a second inference pass or
change production thresholds, and it does not prove all cropping approaches fail.
The experiment result supports investigating model/input quality before relaxing
shot rules. Blurry screen recordings, small moving balls, and training-domain
mismatch are plausible causes; this experiment does not isolate which is decisive.

## Repeatable evaluation

From the project root:

```powershell
.\.venv\Scripts\python.exe cv/src/evaluate_shots.py threemade --output-dir cv/output/made-evaluation-rerun
.\.venv\Scripts\python.exe cv/src/evaluate_shots.py threemiss --output-dir cv/output/miss-evaluation-rerun
```

Use new output directories. Defaults read `cv/output/<clip>`, `<clip>-tracking`,
and `<clip>-shots/shots.json`. Override these with `--detections-dir`,
`--tracks-dir`, and `--shots` when comparing a new experiment.

The evaluator first verifies the reviewed video checksum and that the shot
results reference the exact detection and tracking logs. It checks frame counts,
source metadata, frame indices, and non-overlapping review/attempt windows.
The output `evaluation.json` records matches, missed attempts, extra candidates,
unreviewed candidates, visibility-window counts, and input checksums.

Matching is simple and explicit: use a candidate's crossing frame if available,
otherwise its start frame. Pair it with an unmatched attempt whose interval
contains that frame, in time order. Each attempt can match only once. Duplicates
inside reviewed windows count as extra candidates. Outside reviewed windows,
candidates are unreviewed rather than declared false alarms. An unknown predicted
outcome does not count as an agreed known make/miss. Unknown reference outcomes
are not scored for agreement.

This broad temporal match may pair an unrelated candidate with an attempt. It is
a small regression check, not proof that a candidate followed the right ball.
Review matched evidence visually before claiming improved recognition.

## Code and checks

`src/evaluate_shots.py` separates three jobs: `compare_attempts()` pairs events,
`validate_review()` checks labels, and `main()` loads files and writes the report.
This uses only Python's standard library. Ten additional tests cover missed
attempts, duplicates, unknown/wrong outcomes, excluded times, crossing timestamps,
false alarms in reviewed no-shot intervals, and invalid windows.

## Next evidence needed

We now have two known failure cases to compare against future changes. A useful
next detection experiment must recover the visible ball near the rim without
introducing unrelated false balls. The planned direct, fixed-camera footage will
help distinguish screen-recording quality from model limitations. M3 remains
in progress; no real-video recognition improvement is claimed from this work.
