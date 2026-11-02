# Run CourtVision locally

All PowerShell commands below start at `C:\dev\CourtVision` unless noted.
Use Python 3.12 and Node.js with the existing Expo SDK 57 project.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt -r cv/requirements.txt
.\.venv\Scripts\python.exe cv/src/download_model.py
cd mobile
npm ci
cd ..
```

The pinned E-BARD model is third-party pretrained, not trained by CourtVision.
See cv/models/README.md. No Modal installation or credentials are needed locally.
If .venv already exists, reuse it rather than replacing your environment.

Terminal 1, API (one process):
```powershell
$env:COURTVISION_DATA='C:/dev/CourtVision/data'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Terminal 2, worker (same data directory):
```powershell
$env:COURTVISION_DATA='C:/dev/CourtVision/data'
.\.venv\Scripts\python.exe -m backend.app.worker
```

Keep the worker running: API acceptance alone does not analyze a clip. The OS
lock prevents a second worker on the same data directory. Stop with Ctrl+C.
Restarting API preserves jobs/reviews; restarting worker marks local in-flight
attempts interrupted and resumes a known Modal call. Failed local jobs can retry
from the app. Attempts use new directories; partial artifacts remain inspectable.
After code changes, submit a new job rather than retrying an old code hash.

Terminal 3, mobile:
```powershell
cd mobile
npm run typecheck
npm start
```

Connect iPhone/Expo Go to the same trusted LAN. Enter the computer's IPv4 URL,
e.g. `http://192.168.1.10:8000`, on Home and tap Connect. `localhost` on the phone
is the phone. Allow the backend port through your local firewall if needed.
`EXPO_PUBLIC_API_URL` can set the initial URL; restart Expo after changing it.
Backend `.env.example` is documentation; the Python process does not auto-load it.
Set variables in **both server terminal sessions**. If exposed beyond trusted
local access, set the same `COURTVISION_ACCESS_TOKEN` in the API/worker shells
and enter it in the app. Modal credentials never belong in the app.

## Main workflow

1. Home → Get started → choose a short video → Upload and analyze on computer.
2. Watch queued/running stage and actual processed/total frames. Navigate Home
   and reopen recent jobs to resume after app/API restart.
3. Review results → play original clip → tap a candidate to seek one second before
   contact. Outcomes are automatic estimates. Watch the entire clip for misses.
4. Correct made/missed/unknown, edit time, add an attempt at the player position
   (or typed seconds), remove false positives. Save review. Reload checks persistence.
5. Confirm All attempts reviewed only after inspecting the clip. FG% appears only
   with completeness and no unknown outcomes. Home shows recent reviewed sessions
   and compares their percentages/counts. Automatic output remains unchanged.

Source support: one visible hoop, mostly stationary camera, one active shot at a
time, <=120 seconds, <=250 MiB, <=1080p, validated CFR and zero video start.
The original threemade/threemiss files are VFR and deliberately rejected by the
product. Export a CFR copy before upload; preserve the original and treat any
transformed file as a different hash requiring its own timestamp-aware labels.
20secplay.mp4 and threepointshootout25.mkv pass current timebase checks.

## Offline checks and demos

```powershell
.\.venv\Scripts\python.exe -m tools.checks
.\.venv\Scripts\python.exe -m unittest discover -s cv/tests -v
cd mobile
npm run typecheck
cd ..
.\.venv\Scripts\python.exe -m tools.demo --synthetic --output data/my-synthetic-demo
```

The synthetic demo uses blank video and scripted detections; it proves plumbing,
not basketball accuracy. It prints result_path and creates synthetic-labels.jsonl.
Evaluate deterministically with those exact generated paths:
```powershell
$demo = Get-Content data/my-synthetic-demo/demo.json | ConvertFrom-Json
.\.venv\Scripts\python.exe -m cv.src.dataset --labels data/my-synthetic-demo/synthetic-labels.jsonl --predictions $demo.result_path --split dev --allow-provisional --output data/my-synthetic-evaluation.json
```

Real CPU smoke, which can take several minutes:
```powershell
.\.venv\Scripts\python.exe -m tools.demo --video cv/sample_videos/20secplay.mp4 --output data/my-real-smoke
```

Choose a **fresh output directory** on every demo/run. The demo uses an isolated
SQLite database and local in-process HTTP; it does not touch the normal app DB,
upload footage externally or measure phone latency. To inspect its session on the
phone, launch API/worker with COURTVISION_DATA pointing to its app-data directory.

Optional real-process smoke with tiny synthetic video and the actual model:
```powershell
.\.venv\Scripts\python.exe -m tools.http_smoke --output data/my-http-smoke
```
This starts API/worker child processes on loopback, runs the benchmark HTTP client,
saves a review, restarts API and checks persistence, then stops its own processes.
It verifies process boundaries, not basketball accuracy or phone behavior.

Old CLI remains available as documented in cv/M3.md. New callable CLI:
```powershell
.\.venv\Scripts\python.exe -m cv.src.pipeline cv/sample_videos/20secplay.mp4 --output data/my-pipeline-run
```

For evaluation/data collection see DATASET.md; cloud setup is in MODAL.md;
benchmark commands and limits are in BENCHMARKS.md. Phone walk-through checklist:
two clips, cancel upload, invalid/VFR/oversized upload, backend restart, worker
interruption/retry, duplicate submission, edit/reload, add/remove, unresolved FG%.
Automated tests cover these server behaviors; actual device use is still pending.

## What to understand before moving on

- Detection finds boxes; association chooses which box belongs to the active ball;
  outcome classification interprets observed motion near the hoop.
- Predicted positions help match tracks but cannot prove a rim crossing. Unknown
  preserves uncertainty instead of turning missing evidence into a miss.
- SQLite transactions make job acceptance and review revisions durable. A revision
  conflict (409) protects a newer review; reload before replacing it.
- Model time differs from user wait: decode, transfer, queue, cold initialization,
  result download and polling also count. GPU speed alone does not establish impact.
- Hold out entire recording sessions before tuning; provisional app corrections
  and AI development reviews are not automatically benchmark ground truth.
