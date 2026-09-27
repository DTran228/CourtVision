# CourtVision

A learning project for building an app that analyzes basketball practice videos.

## Lesson 1 — Python foundations for Milestone 1

The project currently includes a `/health` API and an OpenCV video reader.
The reader has been verified with the local videos `threemade.mp4` and `threemiss.mp4`.
The Expo mobile app now has Home and video-selection screens. M1 is **not complete
yet**: the mobile flow still needs verification on your iPhone. The API, mobile
app, and Python script run independently; upload and integration are later work.

```text
backend/app/main.py     Minimal API
backend/requirements.txt
mobile/                Expo app: Home and video selection
cv/src/video.py         Read video one frame at a time
cv/requirements.txt
cv/sample_videos/       Local videos, excluded from Git
```

## Set up Python

Use Python 3.12. Open PowerShell in `C:\dev\CourtVision`.
If Python is already on your PATH, create a virtual environment:

```powershell
python -m venv .venv
```

On this machine, Codex found its bundled Python 3.12 runtime and used it to create
`.venv`. This is a temporary runtime for the first lesson. Once you install Python
3.12 yourself, you can recreate the environment using the command above. You do
not need to change PATH or PowerShell's execution policy to run the commands below.

A **virtual environment** (`.venv`) is a directory containing a Python environment
and libraries for this project, keeping its dependencies separate from other
projects. Do not commit it to Git.

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -r cv/requirements.txt
```

The requirements files constrain major versions. They are not lockfiles that
guarantee identical dependency versions on every installation.

## Run the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Keep this terminal open and visit <http://127.0.0.1:8000/health>.
Expected response: `{"status":"ok"}`. Press Ctrl+C to stop the server.

- **FastAPI** defines how the API responds to HTTP requests.
- **Uvicorn** runs the API server and accepts connections.
- `@app.get("/health")` routes GET requests for `/health` to the `health()` function.
- `127.0.0.1` refers to the machine running the code. It is not the address to use
  when connecting from your phone.

## Read a video

Open a second terminal and read the existing sample (or substitute your own path):

```powershell
.\.venv\Scripts\python.exe cv/src/video.py "cv/sample_videos/threemade.mp4"
```

The script prints the decoded frame count, resolution, FPS, and approximate
duration. A **frame** is one image in a video; FPS means frames per second.
`capture.read()` retrieves one frame per loop iteration, so the script does not
need to load the entire video into RAM. The `finally` block releases the video
file when processing finishes or an error occurs.

### Follow the code in `cv/src/video.py`

The script uses one `main()` function that you can read from top to bottom:

1. **Get the path:** `argparse` reads the filename from your terminal command.
   `Path.is_file()` checks that it exists. `parser.exit(1, ...)` prints an error
   and stops; exit code `1` tells the terminal the command failed.
2. **Open the video:** `cv2.VideoCapture` opens it, and `capture.get` reads its FPS.
3. **Count frames:** `capture.read()` returns a success flag and an image.
   `break` ends the loop when reading stops. `frame.shape[:2]` gives the image's
   height and width. `frames_read += 1` adds one to the counter.
4. **Print results:** ordinary variables hold the measurements; there is no
   separate result dictionary. `:.2f` formats a number with two decimal places.

The `try`/`except`/`finally` block handles OpenCV errors and always releases the
file. The last two lines call `main()` only when you run this file directly.
This is a standalone learning script for now; we can extract a reusable function
when the backend actually needs to call it.

Note: `read()` reports failure both at the end of a video and when decoding fails.
The decoded frame count therefore does not prove that the entire file is intact.
Duration calculated as frame count / FPS is also only an estimate, especially for
videos with a variable frame rate.

## Before moving on

1. Run `/health` yourself and explain why it does not process videos yet.
2. Run the script with a real video and identify the frame count and FPS.
3. Try a nonexistent file path to see the error message.

## Lesson 2 — Select a video on your iPhone

The mobile app uses Expo, React Native, and TypeScript. It has two small screen
components, with comments explaining state, props, permissions, and async code.

Follow [the mobile setup and code walkthrough](mobile/README.md) to sign in to
Expo Go, start the app, and complete the device checklist. You do not need to run
the backend while trying the mobile app at this stage.

Test the same video on the phone and in Python. Selecting a video on the phone
does not send it to the computer. Move to M2 only after all parts of M1 work.

## Roadmap

1. Minimal mobile app, API health endpoint, and video reading.
2. Ball and hoop detection.
3. Shot detection and make/miss classification.
4. Shooter location and shot chart.
5. Connect the mobile app, backend, and computer vision pipeline into an MVP.
6. Background processing, deployment, and advanced analytics when needed.

Official documentation: [FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/),
[OpenCV video](https://docs.opencv.org/4.12.0/dd/d43/tutorial_py_video_display.html).
