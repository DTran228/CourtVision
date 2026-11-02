# Dataset contract v1

JSONL: one object per video, with `schema_version: 1`, `video_sha256`,
`recording_session_id`, `split` (dev/test), `duration_seconds`, `reviewer`,
`review_status` (human_reviewed/provisional/pending), `fully_reviewed` (boolean),
`reviewed_intervals` ([[start,end], ...] in source seconds), and `attempts`.
Each attempt has `id`, `contact_window` ([earliest,latest] seconds at rim approach),
`outcome` (made/missed/unknown), `visibility_tags`, and `occlusion_tags` (lists).
Keep a dataset version in the filename; never edit a frozen test version after tuning.

`recording_session_id` groups every crop from the original recording. No recording
session can appear in both splits. Do not infer sessions from neighboring filenames:
the recorder must confirm provenance. Existing AI reviews remain provisional dev
artifacts, unchanged; they do not become human labels by conversion.

Fully reviewed negatives use an empty attempts list and [[0,duration]]. Partial
reviews support metrics only inside explicit intervals. Whole-clip FP/min requires
full review. Unknown outcomes count in all-attempt denominators and confusion;
known-outcome coverage is reported separately. No unknown-to-miss conversion.

Matching rule frozen before test evaluation: greedily match nearest contact-window
distance (then midpoint distance, then input order), within 0.15 seconds; each
prediction and attempt used once. Duplicate predictions become false positives;
unmatched labels become false negatives. Timestamp error is both distance to the
window and distance to its midpoint (the midpoint is not precise ground truth).

Run from repository root:
```powershell
.\.venv\Scripts\python.exe -m cv.src.dataset --labels data/labels-v1.jsonl --predictions data/run/result.json --split dev --output data/eval-v1.json
```
The command refuses existing output and nonhuman labels unless
`--allow-provisional` is explicitly supplied for development. For frame-level
association review use video hash, frame number, expected_detection_id and
selected_detection_id with `track_selection_accuracy()`; manually identify the
active ball, never treat any observed track as correct automatically.

Collection needed: start with 30–50 human-reviewed attempts across confirmed
recording sessions; expansion goal 150–300 attempts and at least six sessions,
including held-out sessions and negatives. These are goals, not collected counts.
Current repo has no human-reviewed held-out set. Reserve it before parameter tuning.
