# Milestone 3, step 1: follow the ball across frames

M2 implementation is complete; its representative-clip quality review is deferred
with your approval. M3 starts with tracking. The [next lesson](SHOTS.md) now adds separate provisional
shot-candidate rules. This tracker itself does not decide makes or misses.

## Why tracking comes next

A detector answers "Where might the ball be in this image?" A tracker asks "Which
candidate is likely to continue the ball I was following?" A path through several
frames will eventually help us reason about movement near the hoop.

We reuse M2's saved detections. This makes tracking experiments faster and keeps
model predictions fixed while we change the tracking rules. No new dependencies,
training, mobile integration, or server changes are needed.

## Run from the project root

```powershell
.\.venv\Scripts\python.exe cv/src/track_video.py cv/sample_videos/20secplay.mp4 --detections-dir cv/output/20secplay --output-dir cv/output/20secplay-tracking
```

That output folder was created during development. Choose a new output name when
running it again; the script refuses to overwrite earlier experiments. A different
clip needs its own M2 detection folder first. The summary's source video path,
resolution, FPS, record indices, timestamps, and frame counts must match.
These checks do not prove file identity if a video was replaced at the same path;
use the exact unchanged original video that produced the detection log.

| Output | Meaning |
| --- | --- |
| `tracked.mp4` | Silent video with original detection boxes plus a cyan trail. |
| `tracks.jsonl` | One tracking result for every frame, including missing positions. |
| `summary.json` | Settings, number of segments, and counts of each state. |
| `preview.jpg` | First annotated frame. |

A summary is written only after processing succeeds. If an error occurs, output
may be partial; read the error and rerun into a new folder after fixing it.
The original footage and M2 outputs are unchanged. All generated outputs stay
local under the Git-ignored `cv/output` folder.

## Understand the algorithm

1. **Start:** keep only basketball candidates and select the highest-confidence
   one. A false detection can still win; this is an initial heuristic, not proof.
2. **Match:** calculate each box's center and its straight-line distance from the
   last observed ball center. Choose the nearest candidate within the allowed
   radius; confidence breaks equal-distance ties.
3. **Wait briefly:** if nothing matches, retain the previous center internally
   for matching, but write `null` for this frame's center, box, and confidence.
   We do not invent a position or draw a line through the missing interval.
4. **Lose and restart:** after the missing-frame allowance is exceeded, clear
   the old trail. The next frame with a candidate starts a new track ID.

The radius defaults to 5% of the image diagonal, about 110 pixels at 1920x1080.
The diagonal is calculated from width and height with `math.hypot`. Using a
fraction makes the radius scale with resolution. This remains an unvalidated
heuristic: motion speed, camera movement, and FPS also affect a useful radius.
The radius stays fixed during gaps; it does not grow with time or predict velocity.

The gap allowance defaults to 0.20 seconds. At 60 FPS this permits 12 consecutive
unmatched frames; the 13th ends the track. A candidate matching after 12 missing
frames may continue the same ID. We round the allowance down to whole frames.

The cyan trail stores a bounded number of observed points (30 at 60 FPS). It only
connects observations from adjacent video frames. Older observed pieces may stay
visible during short gaps; no cyan circle marks a current ball until it is matched.
Orange boxes are all original ball predictions, including rejected candidates;
the cyan circle identifies the selected candidate. Green boxes still mark hoops.

## Read the code in this order

- `src/tracker.py`: `box_center()` and `BallTracker.update()` contain the rules.
  The class remembers the last center, missing count, ID, and recent trail.
  A `deque` is a container that automatically drops old points when full.
- `src/track_video.py`: pairs each source frame with one saved detection record,
  calls the tracker, and saves the result. `finally` releases video resources.
- `src/visualize.py`: `draw_track()` adds the cyan trail and status text.
- `tests/test_tracker.py`: small invented examples explain expected behavior.

A saved record has `frame`, `timestamp_seconds`, `track_id`, `status`, `center`,
`bbox`, `confidence`, and `missing_frames`. Coordinates are original image pixels.
The confidence is the selected detector score, not a tracking reliability score.

| Status | Meaning |
| --- | --- |
| `searching` | No active track and no candidate to start one. |
| `observed` | A candidate was selected in this frame. |
| `missing` | No candidate matched, but the old track is still remembered. |
| `lost` | This frame exceeded the gap allowance; the old track was cleared. |

IDs count track segments, not balls, players, shots, makes, or misses. A single
physical ball may receive many IDs because detections disappear.

The [first tracking experiment](experiments/m3-tracking-baseline.md) records the
measured results and visual-review limitations.

## Checks and limitations

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s cv/tests -v
```

Tracking tests cover initial selection, ignoring hoops, nearby versus confident
candidates, distance gating, short gaps, expiration, new IDs, zero-gap settings,
the distance boundary, bounded history, and empty frames. These test the rules,
not real-world tracking accuracy.

This baseline has no motion prediction, smoothing, automatic camera-cut detection,
or multi-ball handling. A nearby false detection can steal the track. A fast ball
or camera pan can fall outside the radius. A cut to a new scene may falsely keep
an old ID if a new candidate is nearby. Do not interpret such paths as shot evidence.

Before adding shot logic, inspect the output where the ball disappears or the
camera moves. Confirm what observed versus missing means, why IDs restart, and
why filtering predictions cannot fix all detection errors. The deferred M2 review
remains necessary before trusting shot statistics.
