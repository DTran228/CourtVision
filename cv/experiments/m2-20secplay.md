# M2 experiment: 20secplay.mp4

Date: September 27, 2026. Model: the same pinned E-BARD YOLOv8n documented in
[the model README](../models/README.md). No detector settings or source code were
changed for this experiment.

## Input and settings

- Duration from decoded frames / FPS: 23.47 seconds.
- Resolution: 1920 x 1080; reported frame rate: 60 FPS.
- Frames decoded and processed: 1,408.
- Confidence threshold: 0.25; inference image size: 704; device: CPU.
- Processing time: 110.20 seconds (excludes Python startup/import time).

## Results

| Observation | Count |
| --- | --- |
| Frames with at least one basketball prediction | 889 / 1,408 |
| Frames with at least one hoop prediction | 1,195 / 1,408 |

These are prediction counts, not precision or recall. Some objects are off-screen
or obscured, and some predicted boxes are incorrect.

## Visual review of 20 spaced frames

Reviewed frame indices: 0, 74, 148, 222, 296, 370, 444, 518, 592, 666, 741, 815,
889, 963, 1037, 1111, 1185, 1259, 1333, 1407. Review sheets are local files
`cv/output/20secplay/review-1.jpg` through `review-5.jpg`.

- Frames 0 and 74 (0.00 and 1.23 seconds): a plausible ball box follows the
  dribbler, but an extra box labels another player's arm as a basketball. These
  are two sampled instances of a clear false positive, not an exhaustive count.
  The hoop is off-screen, so its missing box here is expected.
- Frame 370 (6.17 seconds): two basketball candidates appear again, including an
  extra candidate near an off-ball player. The detector has no concept of which
  ball belongs to the current possession.
- Frames 444, 741, and 889 show plausible basketball boxes during dribbling.
- Several later samples have no basketball box. Occlusion and blur make some
  cases ambiguous; these have not been labeled as definite false negatives.
- Hoop boxes generally align with the rim/net region in sampled frames where it
  is visible. They do not identify the exact rim opening for make/miss analysis.
- The first two sampled images look held or repeated. Video playback controls
  appear in other samples, and the last sample cuts to a different game. Frame
  counts therefore should not be interpreted as independent test examples.

This is a qualitative assistant review. No ground-truth bounding boxes were drawn,
no IoU matching was performed, and no benchmark precision/recall is claimed.
The exact visible-ball misses still need closer frame-by-frame human review.

## Verification

All 1,408 output frames decode at 1920 x 1080 and 60 FPS. Every frame has a matching
JSONL record, including no-detection frames. Indices, approximate timestamps,
class names, confidence scores, box bounds, and summary counts were checked.
The output is silent; the original clip was not changed.

## Next step

Follow-up: [the provisional threshold review](m2-threshold-review.md) now records
clear candidate judgments and a comparison. The default remains 0.25; ambiguous
visible-ball misses still need human review.

Use the identified false-positive frames and ambiguous ball misses to build a
small labeled review set before changing thresholds or models. Keep some other
frames aside to check whether a change helps beyond the examples used to tune it.
The roadmap's 30-60 second target-camera test is still outstanding; this 23.47
second edited broadcast clip provides useful evidence but does not replace it.

To reproduce with a new output folder, run from the project root:

```powershell
.\.venv\Scripts\python.exe cv/src/detect_video.py cv/sample_videos/20secplay.mp4 --output-dir cv/output/20secplay-rerun
```

Outputs, review images, and source videos remain ignored by Git. This report can
be committed without uploading the footage.
