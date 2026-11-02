![CourtVision — basketball practice video review](docs/assets/courtvision-cover.png)

# CourtVision

### Your basketball practice review app.

**Turn your practice footage into a session you can revisit.**

Upload a shooting clip, jump to suggested shot attempts, and review each result
alongside the original video. Correct the calls, add attempts the app missed, and
keep a history of your reviewed sessions.

Built for recreational players and student coaches who want a clearer way to
look back at practice.

[Get started](#get-started) · [How it works](#how-it-works) ·
[Try a demo](#try-a-demo) · [Project status](#project-status)

> **Local prototype:** the app provides automatic estimates for you to review.
> The local pipeline has been exercised with real footage; the complete workflow
> still needs a physical-phone walkthrough.

## Your footage. Your review.

| What you want to do | How CourtVision helps |
| --- | --- |
| Find possible attempts | Suggests shot candidates with timestamps. |
| Check what happened | Plays the original clip and lets you jump to a candidate. |
| Make the final call | Change a result to made, missed, or unknown. |
| Fix the attempt list | Add missed attempts, edit timestamps, and remove false positives. |
| Pick up where you left off | Saves reviews and keeps submitted jobs available from Home. |
| Look back at practice | Shows session history and compares completed, resolved reviews. |

Automatic estimates and your corrections are stored separately. Shooting
percentage appears only after you confirm the review is complete and resolve
all unknown outcomes.

## How it works

**Choose a clip → Upload → Analyze → Review → Save**

1. **Choose your practice video.** Select a short clip from your phone.
2. **Send it to your computer.** The backend accepts the upload and queues the analysis.
3. **Follow the progress.** See the job stage and processed frames as the worker runs.
4. **Review the moments.** Tap a candidate to seek just before its timestamp.
   Watch the full clip to catch attempts the app may have missed.
5. **Make it your session.** Correct results, add or remove attempts, and save.
   Mark **All attempts reviewed** when you have checked the full clip.
6. **Come back later.** Open a saved session from Home to revisit your review.

Local CPU mode works without a Modal account. An optional GPU adapter is available
for future cloud experiments.

## Get started

### What you need

- **Python 3.12**
- **Node.js and npm**
- **A phone with Expo Go compatible with Expo SDK 57**, or a compatible development build
- Your phone and computer on the **same trusted local network**
- A short basketball practice clip that meets the [video requirements](#choose-the-right-clip)

The commands below use **Windows PowerShell**. Run them from the repository root
unless a step says otherwise. The full setup notes are in the [runbook](docs/RUNBOOK.md).

### 1. Get the project

```powershell
git clone https://github.com/DTran228/CourtVision.git
cd CourtVision
```

Already have the repo? Open a terminal in your existing checkout.

### 2. Set up Python and the detector

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt -r cv/requirements.txt
.\.venv\Scripts\python.exe cv/src/download_model.py
```

Reuse an existing working virtual environment if you already have one. Calling
its Python executable directly means you do not need to activate it.

The model download is a one-time setup step. CourtVision uses the pretrained
**E-BARD YOLOv8n detector by Gabriele Giudici**, with pinned weights and a hash
check. See [model attribution and licensing](cv/models/README.md).

### 3. Install the mobile dependencies

```powershell
cd mobile
npm ci
cd ..
```

### 4. Start the app

Keep these **three terminals** open.

**Terminal 1 — API, from the repository root**

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Check [API health](http://127.0.0.1:8000/health) on your computer.
It should return `{"status":"ok"}`.

**Terminal 2 — analysis worker, from the repository root**

```powershell
.\.venv\Scripts\python.exe -m backend.app.worker
```

The worker processes queued videos. Keep it running alongside the API.

**Terminal 3 — Expo**

```powershell
cd mobile
npm start
```

Open the project in a compatible Expo Go app or development build.

### 5. Connect your phone

On your computer, run:

```powershell
ipconfig
```

Find the IPv4 address of the adapter connected to your local network. On the
CourtVision Home screen, enter a backend URL such as:

`http://192.168.1.10:8000`

Replace the example IP with **your computer's address**, then tap
**Connect / refresh history**. If prompted by your firewall, allow the backend
port on your trusted private network.

You can also set the initial address through
[mobile/.env.example](mobile/.env.example). Put your value in `mobile/.env`
and restart Expo after changing it.

You're ready to choose a clip and start a review.

## Choose the right clip

CourtVision currently works within these limits:

| Requirement | Supported scope |
| --- | --- |
| Length | Up to 120 seconds |
| File size | Up to 250 MiB |
| Resolution | Up to 1080p, including portrait orientation |
| Video type | MP4, MOV, or MKV that the backend can decode |
| Timing | Constant frame rate (CFR), 1–120 FPS, with a zero video start |
| Scene | One visible target hoop, a mostly stationary camera, one active shot at a time |

**What is CFR?** A constant-frame-rate video uses evenly spaced frame times.
Some phone videos use a variable frame rate (VFR). The current app rejects those
files so candidate timestamps do not silently point to the wrong moment.
Export a CFR copy with a zero start before uploading, and keep your original.

Broadcast cuts, simultaneous shots, and heavily obscured footage are outside
the initial supported scope.

## Try a demo

### Explore the workflow without footage or model weights

From the repository root, after installing the Python dependencies:

```powershell
.\.venv\Scripts\python.exe -m tools.demo --synthetic --output data/my-first-demo
```

This creates a tiny generated video, uses scripted detections, and exercises
upload, jobs, result storage, and a saved review. It writes `demo.json` with
the result location.

**This demo verifies the workflow; it does not measure basketball accuracy.**
It uses its own database and does not modify your normal app sessions.
Choose a new output directory each time you run it.

### Analyze your own clip with the real model

After downloading the model, place a supported clip at
`cv/sample_videos/my-practice.mp4`, then run:

```powershell
.\.venv\Scripts\python.exe -m tools.demo --video cv/sample_videos/my-practice.mp4 --output data/my-practice-demo
```

This runs real CPU inference and may take several minutes. Videos and generated
analysis files are excluded from Git. For the phone workflow, use the three
running processes described above and select the clip in the app.

More demos, evaluation commands, and process-level checks are in the
[runbook](docs/RUNBOOK.md).

## Built with

- **Expo, React Native, and TypeScript** — phone interface and video review
- **FastAPI** — uploads, analysis status, sessions, and reviews
- **SQLite and local files** — persistent jobs, review revisions, videos, and results
- **Python, OpenCV, PyAV, and Ultralytics YOLO** — video timing, detection, tracking, and shot estimates
- **Modal, optionally** — prepared GPU execution adapter

The local architecture stays small:

```text
Expo app → FastAPI → SQLite + local files
                         ↓
                   One job worker
                         ↓
               Video analysis pipeline
```

## Checks

Run the offline Python suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m tools.checks
```

Check the mobile TypeScript code:

```powershell
cd mobile
npm run typecheck
```

Ordinary tests use small fixtures and mocked cloud transport. They do not make
paid GPU calls. The [recorded verification](docs/evidence/final-checks.json)
contains the previous 89-test passing run; see
[progress](docs/PROGRESS.md) for the full check history.

## Need a hand?

| What you see | What to try |
| --- | --- |
| Phone cannot connect | Use the computer's LAN IPv4 address. `localhost` on a phone points to the phone. Check Wi-Fi and firewall settings. |
| A job stays queued | Start the worker in a second terminal. API and worker must use the same data directory. |
| Upload rejected | Check file size, duration, resolution, and CFR timing against the requirements above. |
| Shooting percentage is missing | Complete the review and resolve every unknown result. Empty sessions also have no FG%. |
| Saving returns a 409 conflict | Reload the latest saved review before editing again. |
| A local analysis was interrupted | Restart the worker, open the failed job from Home, and retry. After a pipeline code change, submit a new job. |

The default data directory is `data/` inside the checkout. If you set
`COURTVISION_DATA`, use the same value in both API and worker terminals.
Backend environment variables are not automatically loaded from `.env`.

The MVP is for a single user on a trusted local network. If you expose the
backend beyond that, configure `COURTVISION_ACCESS_TOKEN` and enter it in the
app. Keep Modal credentials server-side.

## Project status

**The local review workflow is implemented.** Real footage has passed local
CPU smoke runs, and a separate API/worker check verified that a saved review
survives an API restart. Mobile typechecking and iOS JavaScript/Hermes export
have also passed.

Work still to validate:

- The full upload, playback, and review experience on a physical phone
- Shot quality on independently labeled, session-held-out footage
- Live CPU/Modal parity, cold and warm latency, and cloud cost
- Review-time impact with actual players or coaches

The baseline tracker remains the default; the candidate tracker is experimental.
No GPU speedup or accuracy improvement is claimed. Results remain suggestions
to review. Some Expo dependency advisories also remain recorded in the
[dependency audit](docs/evidence/npm-audit.json).

## Explore the project

| Document | What's inside |
| --- | --- |
| [Runbook](docs/RUNBOOK.md) | Setup, demo workflow, checks, and operational details |
| [Progress](docs/PROGRESS.md) | Milestones, exact checks, and remaining work |
| [Dataset guide](docs/DATASET.md) | Annotation format, splits, and evaluation rules |
| [Tracking experiments](docs/ASSOCIATION.md) | Baseline and candidate association comparisons |
| [Modal guide](docs/MODAL.md) | Optional cloud setup and validation prerequisites |
| [Benchmark protocol](docs/BENCHMARKS.md) | Reproducible timing experiments and raw evidence |
| [Model provenance](cv/models/README.md) | Pretrained weights, attribution, and licensing |
| [Learning archive](docs/history/README-learning.md) | The original lessons and early development notes |

The cover is AI-generated conceptual artwork, not a screenshot of the app.
