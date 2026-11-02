# C2 experimental association

The existing BallTracker remains baseline and the product default. CandidateTracker
maintains at most eight constant-velocity tracks. Matching is one-to-one greedy
with elapsed-time motion gates and size compatibility. Sustained observed motion
toward the hoop selects a shot track; selection locks through the active shot.
Crossing ambiguity and hoop/camera jumps break identity; predictions stay in a
separate field and cannot satisfy ShotAnalyzer's observed-evidence requirement.
The experimental analyzer converts motion thresholds to a 30 FPS reference clock;
baseline behavior and old CLI defaults are preserved.

Development-only comparison (same 3,772 saved model-detection rows):

| Mode | possible make | possible miss | unknown |
| --- | ---: | ---: | ---: |
| baseline | 1 | 2 | 5 |
| candidate | 2 | 1 | 15 |

These are candidate counts, **not accuracy**. More candidates/unknowns can mean
more false positives. This experiment does not establish an improvement and is
not promoted. Raw evidence: `docs/evidence/association-development.json` (includes
source hashes). No held-out or frame-selection labels were available. Next bounded
experiment: label active-ball identity and contact windows for distinct recording
sessions, then compare association-only and time-aware variants separately. The
initial candidate variant combines those two changes and cannot attribute effects.
The follow-up `association-factorial-development.json` separates association-only
and association + time-aware thresholds: both produce 2/1/15 on this same clip.
That still establishes no quality improvement without independently reviewed labels.

Reproduce from root (choose a fresh output filename):
```powershell
.\.venv\Scripts\python.exe -m tools.ablate --detections cv/output/m3-threepointshootout25/model-detections --output data/association-run.json
```
The historical logs use frame/FPS timestamps. They remain development diagnostics;
new product uploads require validated PTS. Candidate regression tests cover
stationary spares, ambiguous crossings, gaps, camera cuts, locked rebound and
30/60 FPS acquisition. Existing shot tests cover rebound and duplicate events.
