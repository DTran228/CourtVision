# M3 validation baseline: threepointshootout25.mkv

Date: September 30, 2026. This is a new-video run with the existing settings.
No detection, tracking, recovery, or shot rules were changed for this experiment.
The video remains local and ignored by Git.

## Input and run

- 1920x1080, reported 60 FPS, 3,772 processed frames: approximately 62.87 seconds.
- MKV opened directly in OpenCV; conversion was not needed.
- E-BARD model, confidence 0.25, inference size 704, CPU.
- Experimental near-hoop recovery enabled; shot gap allowance 0.25 seconds.
- Model-stage processing time: 290.85 seconds, excluding later stages.
- Camera framing changes during the drill, playback overlays/held imagery appear,
  and the footage cuts to another scene near 60 seconds.

Reproduce from the project root with a new output folder:

```powershell
.\.venv\Scripts\python.exe cv/src/run_pipeline.py cv/sample_videos/threepointshootout25.mkv --recover-ball --output-dir cv/output/shootout-rerun
```

To reuse this experiment's completed model pass, add
`--reuse-detections cv/output/m3-threepointshootout25/model-detections`.
The original input and existing outputs are not overwritten.

## Automatic output: provisional, not the actual score

| Measurement | Result |
| --- | --- |
| Attempt candidates | 8 |
| Possible makes | 1 |
| Possible misses | 2 |
| Unknown outcomes | 5 |
| FG percentage | null: unresolved outcomes |
| Frames containing any model ball prediction | 3,232 |
| Frames containing a hoop prediction | 3,432 |
| Recovery observations | 3 |
| Tracking segments | 54 |

The event times are 6.1167, 11.6833, 15.2167, 18.5833, 26.2667, 30.0833,
33.3333, and 54.7000 seconds. These are proxy crossing/candidate timestamps,
not exact releases. Eight candidates does not establish that only eight shots
were taken. Model presence counts include spare balls and are not accuracy.

Local results are under `cv/output/m3-threepointshootout25/`:

- `tracking/tracked.mp4`: silent tracking video with boxes and selected trajectory.
- `session.json`: provisional totals and timestamped results.
- `shots/review.md`: per-candidate reasons and times.
- `evaluation/evaluation.json`: comparison with the two reviewed early attempts.

## Provisional visual review

Overview sheets sample the full clip once per second. A separate early-hoop sheet
samples 2.8-5.8 seconds, and a closer first-shot sheet covers 3.5-4.23 seconds.
The sheets are local under `cv/output/threepointshootout25-inspection/`.

The assistant labeled only two early attempt windows in
[threepointshootout25-review.json](threepointshootout25-review.json):

| Reviewed window | Visual outcome | Pipeline comparison |
| --- | --- | --- |
| Frames 200-255 (3.33-4.25 s) | Made: ball enters and exits below the net. | No matched candidate. |
| Frames 312-370 (5.20-6.17 s) | Missed: ball approaches rim then rebounds upward/right. | Candidate 1 matches by time window and predicts a miss at 6.1167 s. |

These are assistant judgments, not human-approved ground truth. The temporal
match for the second shot is late relative to rim contact; it does not establish
precise event timing. Seven other candidates fall outside these reviewed windows
and remain unreviewed. Do not extrapolate this two-attempt result to whole-video
accuracy, total attempts, or a false-alarm rate. The filename does not establish
how many attempts occurred.

## Confirmed tracking limitation

In frames 200-255, nine frames have a basketball candidate within the diagnostic
near-hoop region, but the selected track is never in that region. In frames
312-370, 30 frames have a near-hoop candidate, but the selected track only reaches
that region in frames 356-370, after the rebound.

For this diagnostic, near hoop means a center within two hoop widths horizontally
and from three widths above to two widths below the highest-confidence hoop's
top edge. These counts describe location, not manually verified box correctness.
Recovery supplied no observations in either reviewed window.

The original full-frame tracking rule follows one candidate and can stay attached
to a spare ball in a rack or on the floor. This new footage contains several balls,
unlike the favorable short development examples. The first missed make shows why
high ball-presence counts alone do not mean the right ball was tracked.

## Verification and next step

All four per-frame logs contain 3,772 sequential records with aligned timestamps.
The tracking video decodes all 3,772 frames at 1920x1080 and 60 FPS. The evaluation
checks the source video and prediction hashes. No source-code changes were needed
to run the experiment; no new accuracy claim is based on the existing unit tests.

Next, review the complete shot sequence and improve selection of the shot ball
when several balls are visible. Keep this run as the unchanged baseline for that
comparison. M3's broader accuracy validation remains incomplete: the first newly
reviewed make was missed, and five generated outcomes remain unknown.
