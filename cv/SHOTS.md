# Milestone 3, step 2: possible shots and provisional outcomes

**Historical baseline lesson:** see [the current M3 workflow](M3.md) for optional
motion recovery, bounded gaps, rebound handling, and the successful two-clip
comparison. The strict no-gap rules and zero-candidate results below describe the
earlier baseline; use `--gap-seconds 0` to reproduce strict shot analysis.

We now have a baseline that reads saved ball tracks and hoop detections, looks
for a descending near-hoop pattern, and records reviewable candidates. It does
not yet provide validated shot totals, makes, misses, or shooting percentages.
M2's representative-clip detection-quality review remains deferred.

## The idea: a state machine

A state machine is a small set of named situations and rules for moving between
them. Instead of deciding everything from one frame, the analyzer remembers what
it saw earlier. This is different from training another machine-learning model.

| State | What it means | What happens next |
| --- | --- | --- |
| `waiting` | No candidate is active. | Look for two adjacent observations descending near the hoop. |
| `candidate` | A possible shot has started. | Look for an above-to-below crossing and a later observation below. |
| `cooldown` | A candidate just ended. | Wait one second before searching again to reduce duplicates. |

A candidate can finish as `possible_make`, `possible_miss`, or `unknown`. The word
possible matters: a 2D image does not prove that the ball went through the actual
rim. A pass, rebound, false ball detection, or camera movement can fool these rules.

## Run it

Run from `C:\dev\CourtVision`, after generating detections and tracks for the same
unchanged video:

```powershell
.\.venv\Scripts\python.exe cv/src/analyze_shots.py --detections-dir cv/output/20secplay --tracks-dir cv/output/20secplay-tracking --output-dir cv/output/20secplay-shots-rerun
```

Choose a new output folder for each run. The development results already live in
`cv/output/20secplay-shots`, `cv/output/threemade-shots`, and
`cv/output/threemiss-shots`. No model or video decoding is needed for this command:
it reuses the JSONL logs. It adds no dependencies and changes no detector settings.

| File | Purpose |
| --- | --- |
| `shots.json` | Candidate timestamps, provisional outcomes, reasons, and evidence snapshots. |
| `shot_states.jsonl` | One state record per frame for debugging. |
| `review.md` | A readable table of candidates and timestamps to check in the original video. |

The command checks source-folder/video references, dimensions, FPS, frame counts,
indices, and timestamps. Observed track boxes must exist in the corresponding
saved detections, and their centers must match. SHA-256 hashes record the exact
input logs used for each completed analysis. They do not certify that detections
are correct or detect every possible source-file replacement.

If a run fails, any state log may be partial; `shots.json` is written only after
input processing succeeds. A candidate still active at the end is finalized as
unknown in `shots.json`, after writing the last frame's state record.

## Coordinates and rules, with an example

Image coordinates start at the top-left. Increasing y means moving **downward**.
For this experiment we use the top edge of the detected hoop box as a rough rim
line. This is an assumption: the model box includes the rim/net area and does not
locate the exact opening. We must validate or replace this proxy later.

Distances are divided by hoop-box width. If the hoop is 100 pixels wide, a vertical
change of 0.5 means 50 pixels. Horizontal zero is the middle of the hoop; its left
and right edges are -0.5 and +0.5. This makes the rules less tied to one resolution.

For a hoop box `[100, 100, 200, 160]`, a ball centered at x=150 with successive y
values `40, 70, 110, 160` moves from above the proxy line to below it. This synthetic
sequence produces a possible make. It demonstrates the rule, not model accuracy.

The exact baseline rules are deliberately visible in `src/shots.py`:

1. Use the highest-confidence hoop in the current frame and an **observed** ball.
   Missing or remembered-only ball positions cannot supply crossing evidence.
2. Compare adjacent frames with the same track ID. Discontinuity, a hoop-center/top
   jump greater than half its previous width, or a width ratio outside 0.67-1.5
   interrupts an active candidate as unknown. These are crude checks, not full
   camera-cut detection or reliable hoop identity matching.
3. Start when the previous ball is 0.15-3 hoop widths above the proxy, within two
   widths horizontally, and the next point descends by more than 0.02 widths.
   The current point must remain within two widths horizontally and between three
   widths above and one width below the proxy. This per-frame motion threshold is
   sensitive to FPS and has not been calibrated.
4. Detect a downward crossing of the proxy line from two adjacent observations.
   Linear interpolation estimates horizontal crossing position along that segment.
   No interpolation is allowed through a missing frame.
5. Require a **later** descending observation at least half a hoop width below the
   proxy. A crossing within +/-0.5 widths and continuation within +/-0.75 produces
   `possible_make`. A crossing and continuation both at least 0.75 widths from the
   center produce `possible_miss`. Edge cases remain unknown.
6. Missing ball/hoop evidence, changed tracks, a reference jump, video end, or an
   active duration over two seconds produce `unknown`. After any completed event,
   pause for one second. This can suppress closely spaced real attempts too.

These constants are starting assumptions, not experimentally optimized settings.
A ball disappearing without an active candidate creates no event. Therefore,
**zero candidates is not the same as zero shots**, and unknown is not a miss.
Airballs far from the hoop, slow descents, short tracks, or occlusion may never
start a candidate. No release detection, player detection, or depth reasoning is
implemented.

## Read the code

Start with `ShotAnalyzer.update()` in `src/shots.py`. `previous` holds the last
usable observation; `active` holds the current candidate; `crossing` remembers
where it passed the proxy. `finish()` creates an event and resets the state.
The class keeps that memory between frames, just as `BallTracker` does.

Then read `src/analyze_shots.py`. Its job is file validation, feeding records into
the analyzer, and saving reports. Separating the rules from file handling lets us
test simple invented paths without YOLO, OpenCV, or a real video.

## Verification and current limitations

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s cv/tests -v
```

The suite includes synthetic possible makes/misses, ambiguous crossings, missing
observations, track changes, hoop jumps, upward motion, dribbling below the hoop,
cooldown, timeouts, and end-of-video handling. Full-command tests check generated
files, timestamps, edited centers, extra records, and overwrite protection.

The [baseline report](experiments/m3-shot-baseline.md) records runs on all three
existing clips. None produced candidates. The short clips lack selected ball
observations in the required starting region; we must improve/validate the input
evidence before claiming real shot recognition. Passing synthetic tests proves
that our code follows its rules, not that those rules recognize basketball shots.

Before moving on, explain why descending means increasing y, why a missing ball
cannot be called a miss, and why a test using invented boxes cannot measure model
accuracy. Next, manually review ball visibility around a known shot, compare that
timing with the saved track, and evaluate the planned fixed-camera footage.


## Compare against visually reviewed attempts

We have now [reviewed one make and one miss](experiments/m3-reviewed-attempts.md)
in the short clips and confirmed that the baseline misses both. The report
explains the detector gap and the crop experiment that failed to recover it.

```powershell
.\.venv\Scripts\python.exe cv/src/evaluate_shots.py threemade --output-dir cv/output/made-evaluation-rerun
.\.venv\Scripts\python.exe cv/src/evaluate_shots.py threemiss --output-dir cv/output/miss-evaluation-rerun
```

`experiments/shot-review.json` contains provisional visual labels.
`src/evaluate_shots.py` compares candidate times with those reviewed windows and
writes `evaluation.json`. A missed attempt is different from a missed basket:
the former means our software failed to identify an attempt at all. Unreviewed
times are excluded, and unknown outcomes are not treated as successful make/miss
classifications. Read the report's matching limitations before using its counts.
