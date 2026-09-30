# M3 tracking baseline: 20secplay

Date: September 28, 2026. This is M3's tracking foundation, not completed shot
or make/miss detection. M2 quality validation remains deferred.

## Settings and result

The tracker reused the existing E-BARD predictions without rerunning YOLO.
Distance gate: 5% of the image diagonal (110.15 pixels). Gap allowance: 0.20
seconds (12 missing frames at 60 FPS). Detection confidence stays at 0.25.

| Measurement | Count |
| --- | --- |
| Processed frames | 1,408 |
| Observed candidate selected | 797 |
| Missing, previous track remembered | 445 |
| Track lost this frame | 21 |
| Searching without an active track | 145 |
| Track segments started | 22 |

These counts describe algorithm states, not accuracy, shots, or distinct balls.
Compared with the 889 frames containing ball predictions, 92 had candidates but
no selected match. Rejecting candidates may remove false alarms or real balls;
we have not labeled those rejections as correct.

## Verification and visual inspection

All 1,408 output frames were decoded at 1920x1080 and 60 FPS. The track log has
one aligned record per frame. Every observed result belongs to that frame's saved
basketball predictions; its center matches its box and same-ID movement stays
within the configured radius. Missing results contain no invented position,
box, or confidence. State totals match the summary.

The review sheet uses frames 0, 370, 741, and 763. Selected ball candidates have
cyan circles, while orange boxes retain all original detections. Frame 763 is
marked missing, with historical trail pieces and no current selected-ball circle.
The trail is visibly jagged; no smoothing is implemented. Frequent segment
restarts show that this baseline is not yet a reliable full-possession trajectory.

Local output: `cv/output/20secplay-tracking/`. Open `tracked.mp4` to inspect the
whole result and `tracking-review.jpg` for the four-frame sheet.

## Next lesson

Inspect loss/reacquisition intervals and confirm provisional ball judgments.
Then develop a simple shot-candidate state machine using ball movement relative
to the hoop, with explicit unknown outcomes when evidence disappears. Do not
report trusted make/miss statistics before validating detection and tracking.
See [the tracking walkthrough](../TRACKING.md) for code explanations and commands.
