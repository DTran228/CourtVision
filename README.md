![CourtVision — basketball practice video review](docs/assets/courtvision-cover.png)

<h1 align="center">CourtVision</h1>

<p align="center">
  <strong>Your basketball practice review app.</strong><br>
  Put in the reps. Give your practice a second look.
</p>

<p align="center">
  <a href="#why-courtvision">Why CourtVision?</a> ·
  <a href="#see-the-workflow">How it works</a> ·
  <a href="#quick-start--installation">Get started</a> ·
  <a href="#frequently-asked-questions">FAQ</a>
</p>

CourtVision turns your shooting clips into practice sessions you can review,
correct, and revisit. Upload a video, jump to suggested shot attempts, and
save a record of what happened on the court.

Made for **recreational players, student coaches, and anyone who records
their shooting practice.**

---

## Why CourtVision?

Your practice videos have more to offer than a place in your camera roll.
CourtVision gives you a way to move through the footage, check each attempt,
and keep your reviewed sessions together.

- 🎯 **Find your next shot to review.** Get suggested attempts with timestamps
  that take you back to the original footage.
- ▶️ **Watch the moment behind the result.** Jump just before an attempt,
  replay the action, and decide what happened.
- ✏️ **Make the final call.** Change made, missed, or unknown results. Add an
  attempt the app missed, adjust its timestamp, or remove a false positive.
- 💾 **Keep your practice log.** Save your edits and reopen past sessions
  from the Home screen.
- 📊 **Compare reviewed sessions.** Look back at makes, attempts, and shooting
  percentages once your reviews are complete.
- 💻 **Analyze on your own computer.** The current local mode runs without
  a Modal account or GPU cloud setup.

**You stay in control of the review.** Suggested results are automatic estimates.
CourtVision keeps an outcome **unknown** when it cannot make a clear call, so
you can check the video yourself.

---

## See the workflow

**Pick a clip → Analyze → Review the shots → Save your session**

| Step | What you do |
| --- | --- |
| **1. Pick your clip** | Open **Get started**, choose a video, and tap **Upload and analyze on computer**. |
| **2. Follow the analysis** | Leave the analysis running while CourtVision prepares timestamped suggestions. You can reopen submitted jobs from Home. |
| **3. Review your shots** | Tap **Review results**, then choose an attempt to play from just before its timestamp. Correct, add, or remove attempts as you watch. |
| **4. Save your session** | Save your edits. When you have watched the full clip, confirm **All attempts reviewed** and save again. |
| **5. Come back to your practice** | Open **Session history** on Home to revisit a session or compare completed reviews. |

Shooting percentage appears when the review is complete and every outcome is
resolved. Watch the whole clip before confirming completeness so you can catch
attempts the app may not have suggested.

---

## Quick Start & Installation

The current version runs **locally from source**, with your computer handling
analysis and your phone providing the review interface.

### What you'll need

| On your computer | On your phone |
| --- | --- |
| Python **3.12** | Expo Go compatible with **Expo SDK 57**, or a compatible development build |
| Node.js and npm | Access to your practice video |
| A connection to your private Wi-Fi network | The same Wi-Fi network as your computer |

These instructions use **Windows PowerShell**. For additional setup details,
see the [full setup guide](docs/RUNBOOK.md).

### 1. Download CourtVision

```powershell
git clone https://github.com/DTran228/CourtVision.git
cd CourtVision
```

Already cloned the project? Start in your existing CourtVision folder.

### 2. Set up video analysis

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt -r cv/requirements.txt
.\.venv\Scripts\python.exe cv/src/download_model.py
```

The last command downloads the pretrained detector used for shot suggestions.
You only need to download it once. If you already have a working `.venv`,
reuse it.

### 3. Set up the mobile app

```powershell
cd mobile
npm ci
cd ..
```

### 4. Start CourtVision

Open **three terminals** and keep them running while you use the app.
Terminals 1 and 2 start from the CourtVision folder.

**Terminal 1 · Start the backend**

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Open [the health check](http://127.0.0.1:8000/health) on your computer.
If you see `{"status":"ok"}`, the backend is ready.

**Terminal 2 · Start video processing**

```powershell
.\.venv\Scripts\python.exe -m backend.app.worker
```

This process picks up submitted videos and analyzes them.

**Terminal 3 · Open the mobile app**

```powershell
cd mobile
npm start
```

Open the project in your compatible Expo Go app or development build.

### 5. Connect your phone

1. Run `ipconfig` on your computer and find the **IPv4 Address** for your
   Wi-Fi adapter.
2. On the CourtVision Home screen, enter that address with port **8000**.
   For example, `http://192.168.1.10:8000`.
3. Tap **Connect / refresh history**.
4. Tap **Get started**, choose a clip, and begin your first review.

Use **your computer's actual IP address** in place of the example. If your
firewall prompts you, allow the backend port on your trusted private network.

**That's your setup. For future sessions, start the three terminals and open
CourtVision on your phone.**

<details>
<summary><strong>Optional: remember the initial backend address</strong></summary>

Create `mobile/.env` using [mobile/.env.example](mobile/.env.example) as a guide:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.10:8000
```

Replace the address with your computer's IP, then restart Expo. You can still
change the connection address on the Home screen.

</details>

---

## Get the best from your footage

Start with a short shooting drill where the camera stays mostly still and
one target hoop remains visible.

| Clip setting | Current support |
| --- | --- |
| **Length** | Up to **2 minutes** |
| **Size** | Up to **250 MiB** |
| **Resolution** | Up to **1080p**, landscape or portrait |
| **Format** | MP4, MOV, or a decodable MKV |
| **Frame rate** | Constant frame rate (CFR), **1–120 FPS** |
| **Scene** | One visible hoop and one active shot at a time |

**A quick note about phone recordings:** some phones record at a variable frame
rate (VFR). If CourtVision rejects the timing of your clip, export a
**constant-frame-rate copy with its timeline starting at 0:00** and try that
copy. Keep the original recording.

Fast camera cuts, simultaneous shots, and a heavily obscured hoop are outside
the current supported scope.

---

## Try a demo on your computer

Want to explore the workflow before connecting a phone? After installing the
Python dependencies, run this from the CourtVision folder:

```powershell
.\.venv\Scripts\python.exe -m tools.demo --synthetic --output data/my-first-demo
```

This uses a tiny generated video and scripted detections to walk through
upload, analysis jobs, result storage, and a saved review. It writes a
`demo.json` file containing the result location.

The demo uses a separate database, so your normal sessions stay untouched.
Use a **new output folder** each time. The generated example demonstrates
the workflow; it does not measure basketball accuracy.

<details>
<summary><strong>Try the real detector on your own video</strong></summary>

Download the model during setup, then place a supported clip at
`cv/sample_videos/my-practice.mp4`:

```powershell
.\.venv\Scripts\python.exe -m tools.demo --video cv/sample_videos/my-practice.mp4 --output data/my-practice-demo
```

CPU analysis may take several minutes. Your clip and generated analysis
artifacts are excluded from Git. More demo options are in the
[setup guide](docs/RUNBOOK.md).

</details>

---

## Frequently asked questions

**Do I need a cloud account or a dedicated GPU?**

No. The local workflow runs on your computer's CPU. An optional Modal adapter
is available for development experiments; it is not needed to get started.

**Are the suggested results final?**

You make the final call. Review the original video, correct uncertain results,
and check for attempts the app missed. An unknown result means the app did not
have enough clear evidence to choose made or missed.

**Why can't my phone connect?**

Check that both devices are on the same private Wi-Fi network. Enter your
computer's IPv4 address, including `:8000`. `localhost` on a phone points to
the phone itself. Also check that the backend is running and the firewall
allows the connection.

**Why is my video still queued?**

Make sure the video-processing terminal is running. Both backend processes
must use the same data folder; the default is `data/` inside the checkout.

**Why isn't a shooting percentage showing?**

Finish the review, resolve every unknown outcome, and save with
**All attempts reviewed** enabled. A session with no attempts has no percentage.

**Can I leave and return to a session?**

Yes. Save your review, then reopen it from Home. Submitted jobs also remain
available there. If a local analysis was interrupted, restart the worker and
use **Retry failed analysis**. If saving reports a review conflict, reload the
latest saved version before editing again.

---

## Growing with your practice

CourtVision is in **active development**, with the local upload, analysis,
review, and session-history workflow implemented.

The next focus is broader phone testing, evaluating shot quality across more
practice recordings, and measuring whether optional GPU processing improves
the full wait from upload to review.

The full phone workflow still needs physical-device validation. Accuracy,
cloud speedup, and review-time improvements have not yet been established.
Follow [development progress](docs/PROGRESS.md) for the supporting evidence
and upcoming work.

---

<details>
<summary><strong>For developers: stack, checks, and project guides</strong></summary>

### Built with

- **Expo, React Native, and TypeScript** for the phone interface
- **FastAPI** for uploads, processing status, sessions, and reviews
- **SQLite and local files** for saved jobs, results, and review revisions
- **Python, OpenCV, PyAV, and Ultralytics YOLO** for video analysis
- **Modal, optionally**, for GPU execution experiments

CourtVision uses the pretrained **E-BARD YOLOv8n detector by Gabriele Giudici**.
See [model provenance and licensing](cv/models/README.md) for attribution.
The baseline tracker is the default; the candidate tracker remains experimental.

### Run checks

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m tools.checks
```

For the mobile app:

```powershell
cd mobile
npm run typecheck
```

Ordinary tests make no paid cloud calls. The
[recorded verification](docs/evidence/final-checks.json) contains the previous
89-test passing run. Remaining Expo dependency advisories are recorded in the
[dependency audit](docs/evidence/npm-audit.json).

### Configuration

If you change `COURTVISION_DATA`, set the same value in both backend terminal
sessions. Backend variables are not automatically loaded from `.env`.
The current app is for single-user use on a trusted local network. If the
backend is exposed beyond that, configure `COURTVISION_ACCESS_TOKEN` and
enter it in the app. Keep Modal credentials server-side.

### Project guides

| Guide | What you'll find |
| --- | --- |
| [Runbook](docs/RUNBOOK.md) | Detailed setup, demos, and operational help |
| [Progress](docs/PROGRESS.md) | Milestones and verification history |
| [Dataset](docs/DATASET.md) | Labels, recording-session splits, and evaluation |
| [Tracking](docs/ASSOCIATION.md) | Association experiments and comparisons |
| [Modal](docs/MODAL.md) | Optional GPU adapter and validation prerequisites |
| [Benchmarks](docs/BENCHMARKS.md) | Timing protocol and reproducible evidence |
| [Learning archive](docs/history/README-learning.md) | Original lessons and early development notes |

The cover is AI-generated conceptual artwork, not a screenshot of the app.

</details>
