# M2 baseline: September 27, 2026

## Setup

- Model: E-BARD YOLOv8n, provenance recorded in `cv/models/README.md`.
- Runtime: Python 3.12.14, Ultralytics 8.4.164, PyTorch 2.14.0, OpenCV 4.14.0.
- Device: CPU on AMD Ryzen 5 5625U.
- Confidence threshold: 0.25.
- Input: two local 1024 x 576 broadcast clips, approximately 30 FPS.
- No fine-tuning, tracking, or shot classification was performed.

## Observed output counts

These counts describe predictions, not correct detections or accuracy.

| Clip | Inference size | Frames processed | Frames with ball prediction | Frames with hoop prediction | Processing time |
| --- | --- | --- | --- | --- | --- |
| threemade | 704 | 159 | 52 | 159 | 11.84 s |
| threemiss | 704 | 178 | 42 | 177 | 11.81 s |
| threemade | 1024 | 159 | 47 | 149 | 14.91 s |

Processing time excludes Python startup/import time and will vary by machine.
The larger input produced fewer predictions and took longer. Without ground-truth
labels, this does not establish which setting is more accurate. We retain the
model's documented 704 input size as the baseline.

## Visual review

Six sampled frames from the made clip show plausible hoop localization and some
ball detections, with missing ball boxes during parts of the play. This is a
qualitative observation, not a measured recall score. The hoop boxes cover the
rim/net region rather than providing exact rim-opening geometry.

Local artifacts (ignored by Git):

- `cv/output/threemade/detected.mp4`
- `cv/output/threemiss/detected.mp4`
- `cv/output/threemade/review.jpg` (six sampled frames)
- `cv/output/threemade-1024/detected.mp4` (comparison run)

## Verification completed

- Both baseline output videos decode fully: 159 and 178 frames, matching input counts.
- Each baseline output frame is 1024 x 576.
- JSONL record counts and sequential frame indices match output video frames.
- Logged timestamps match frame index / reported FPS.
- Boxes use supported classes, valid original-frame bounds, and thresholded scores.
- Missing files, invalid video bytes, and videos with no frames exit with errors.
- Invalid confidence/image-size arguments are rejected.
- Existing output folders are rejected rather than overwritten.
- Model checksum matches the documented weights; `pip check` passes.
- Git ignores weights, footage, and generated outputs.

## Next checkpoint

Review around 20 spaced frames and record correct predictions, false positives,
and visible missed objects separately for basketball and hoop. Use a longer
30-60 second clip before declaring M2 complete. The two current clips alone are
not enough to judge reliability across a practice session.
