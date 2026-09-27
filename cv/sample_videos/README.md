# Sample videos

Place a short basketball video here, for example `practice.mp4`.
Videos are excluded from Git to keep large files and personal footage out of the
repository.

Run this command from the CourtVision project root:

```powershell
.\.venv\Scripts\python.exe cv/src/video.py "cv/sample_videos/practice.mp4"
```

The script only reads the video. It does not detect the ball or count shots yet.
