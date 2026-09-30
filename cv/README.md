# Milestone 2: basketball and hoop detection

M1 proved we could read frames. M2 asks whether we can locate the ball and hoop
in those frames. This implementation is a **first detection experiment**. It does
not count shots or decide makes and misses.

## Run it

Open PowerShell at `C:\dev\CourtVision`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r cv/requirements.txt
.\.venv\Scripts\python.exe cv/src/download_model.py
.\.venv\Scripts\python.exe cv/src/detect_video.py cv/sample_videos/threemade.mp4 --output-dir cv/output/made-review
```

Dependencies and model weights are already installed on this machine. Use a new
output folder each time: the script refuses to overwrite an earlier experiment.
For the other clip:

```powershell
.\.venv\Scripts\python.exe cv/src/detect_video.py cv/sample_videos/threemiss.mp4 --output-dir cv/output/miss-review
```

Open `detected.mp4` in the resulting folder with a video player. Boxes are orange
for basketball and green for hoop. The output is a silent diagnostic video; OpenCV
rewrites frames and does not copy audio. The original footage is unchanged.

Each output folder contains:

| File | Purpose |
| --- | --- |
| `detected.mp4` | Original frames with predicted boxes and confidence scores. |
| `preview.jpg` | The first annotated frame for a quick check. |
| `detections.jsonl` | One JSON record per frame, including frames with no detections. |
| `summary.json` | Settings, frame counts, and processing time for the run. |

If processing fails, an output folder may contain partial results. A successful
run writes `summary.json` at the end. Read any terminal error and rerun into a new
folder after fixing it.

## Why these choices?

- **A basketball-specific model:** a standard COCO YOLO model has a `sports ball`
  category but no hoop category. Renaming a category cannot teach it a new object.
  We use the small E-BARD YOLOv8n model, which has both target classes. Attribution,
  source revision, and the weight checksum are in [models/README.md](models/README.md).
- **CPU first:** this laptop has AMD integrated graphics. CPU inference works with
  the installed packages; we can assess whether acceleration is needed later.
- **One frame at a time:** this reuses the idea from M1 without loading a whole
  video into memory. The model is loaded only once, because loading it is expensive.
- **704-pixel inference size:** this matches the model card's training setting.
  Ultralytics resizes/letterboxes internally, then returns boxes in the original
  frame's pixel coordinates.
- **No tracking yet:** a box in one frame is independent of a box in the next.
  Tracking and make/miss reasoning belong to M3.

## Read the code in this order

1. `src/detect_video.py`: the overall flow and the familiar `capture.read()` loop.
2. `src/detector.py`: load the model, predict, convert results into dictionaries.
3. `src/visualize.py`: draw rectangles and text on a copy of each frame.
4. `src/download_model.py`: download exactly the weights we tested.

`video.py` remains the simple M1 reader. Keeping it lets you compare reading alone
with the extra work needed for inference.

The `Detector` class is just a way to keep one loaded model and its settings
between calls. `__init__` runs when we create it; `self.model` holds the model.
`detector.detect(frame)` returns a list, such as this illustrative prediction:

```python
[
    {
        "class": "basketball",
        "confidence": 0.68,
        "bbox": [414.7, 472.2, 436.4, 496.0],
    }
]
```

A **bounding box** is `[left, top, right, bottom]`. In an image, `(0, 0)` is the
top-left corner; x increases rightward and y increases downward. These coordinates
are pixels, not positions on a basketball court.

**Weights** are numbers learned during training. **Inference** means using those
weights to predict objects in a new image. PyTorch performs the neural-network
calculations; Ultralytics provides the model API; OpenCV reads and writes images.

### Why check the model result?

YOLO's `predict()` supports several tasks and return formats. We set `stream=False`
to request a list, then use `isinstance` to check its type before reading the first
result. We also check that the result contains detection boxes. These checks help
both the editor and a person reading the code understand what values are valid.

`boxes is None` means detection boxes are unavailable for that result. An empty
collection of boxes is different: detection ran but found no objects, so our
function correctly returns an empty list.

The video writer uses `cv2.VideoWriter.fourcc("m", "p", "4", "v")` to select its
codec. A codec is the format used to encode video frames. This method is present
in OpenCV's type definitions; its older `VideoWriter_fourcc` alias is not present
in the installed definitions, even though it works at runtime.

## Confidence and mistakes

The default confidence threshold is `0.25`: predictions below that score are
omitted. A score of `0.80` does not establish an 80% chance of correctness.
Try a stricter threshold on the same clip:

```powershell
.\.venv\Scripts\python.exe cv/src/detect_video.py cv/sample_videos/threemade.mp4 --confidence 0.50 --output-dir cv/output/made-conf050
```

Increasing the threshold often removes uncertain false alarms, but can also hide
real balls. Lowering it often reveals more candidates and more false alarms.
Compare the actual boxes instead of choosing the setting with the largest count.

`frames_with_basketball` means frames containing at least one predicted basketball.
It is **not** the number of balls, shots, correct predictions, precision, or recall.

To begin evaluating, inspect about 20 frames spaced throughout a clip:

1. Decide whether the ball and hoop are actually visible.
2. For each class, count correct boxes (TP), incorrect extra boxes (FP), and visible
   objects with no matching box (FN). Match at most one prediction to each object.
3. Record a note for occlusion, blur, an overly large box, or a camera cut.
4. Compute precision = TP / (TP + FP), and recall = TP / (TP + FN). If a denominator
   is zero, report the metric as undefined rather than inventing a percentage.

This visual review is informal. Reproducible automated metrics require manually
labeled boxes and a declared overlap rule, such as IoU >= 0.5. IoU is the area
shared by two boxes divided by the area covered by either box. Do not report a
benchmark accuracy until those labels and matching rules exist.

The measured run settings, counts, and checks are recorded in
[the first experiment report](experiments/m2-baseline.md). The longer broadcast
clip is documented in [the 20secplay review](experiments/m2-20secplay.md).

## Compare thresholds using saved predictions

The [threshold review](experiments/m2-threshold-review.md) explains our first
small comparison and why the default remains 0.25. Run these from the project root:

```powershell
.\.venv\Scripts\python.exe cv/src/evaluate_review.py --split tune
.\.venv\Scripts\python.exe cv/src/evaluate_review.py --split check --thresholds 0.25 0.40
```

`src/evaluate_review.py` reads saved predictions and provisional judgments from
`experiments/20secplay-review.json`; it does not load the model. Its retention
column counts known correct predictions that survive filtering, **not recall**.
Uncertain frames and a repeated opening image are excluded. Read the report's
limitations before treating these small-sample numbers as model performance.

Run the evaluator's dependency-free tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s cv/tests -v
```

## Milestone 3 has started

With the M2 quality review deferred, the next lesson is [single-ball tracking](TRACKING.md).
It reuses saved predictions and adds a trajectory without changing detector settings.
M2 validation is still pending. The [current M3 workflow](M3.md) adds optional
recovery and provisional outcomes; it matches both reviewed development shots.
The broader practice-video validation remains open.

## Limits and next checkpoint

The first clips are about five and six seconds long; `20secplay.mp4` adds a
23.47-second test. These are useful experiments, but do not yet satisfy the
roadmap's 30-60 second evaluation clip.
Before declaring M2 complete, review detection quality and test a longer clip,
ideally from the fixed camera angle you intend to use for practice sessions.

The hoop class can cover the rim/net area; it does not precisely locate the rim
opening needed for future make/miss logic. Broadcast camera motion, small balls,
blur, occlusion, and filming a screen can all change results.

The writer preserves reported FPS and frame dimensions. Timestamps are frame index
/ FPS, so variable-frame-rate video timing is approximate. OpenCV can stop on a
decoding failure as well as the natural end of the video. No-detection frames are
kept in both the video and log; they are not silently skipped.

Model weights, source footage, and results stay local and are ignored by Git.
Nothing in this lesson connects to the mobile app or uploads videos.

References: [COCO categories](https://docs.ultralytics.com/datasets/detect/coco),
[Ultralytics prediction API](https://docs.ultralytics.com/modes/predict).
