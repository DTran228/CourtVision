"""Bounded full decode and real PTS validation. MVP accepts CFR only."""
import math
from pathlib import Path

import av

MAX_BYTES = 250 * 1024 * 1024
MAX_SECONDS = 120
MAX_FPS = 120


def inspect_video(path, enforce_limits=True):
    path = Path(path)
    if enforce_limits and path.stat().st_size > MAX_BYTES:
        raise ValueError("Video exceeds 250 MiB")
    times = []
    with av.open(str(path)) as container:
        if len(container.streams.video) != 1:
            raise ValueError("Exactly one video stream is required")
        stream = container.streams.video[0]
        fps = float(stream.average_rate or 0)
        width, height = stream.width, stream.height
        if not math.isfinite(fps) or not 1 <= fps <= MAX_FPS:
            raise ValueError("Unsupported or missing FPS (1–120 required)")
        if enforce_limits and (min(width, height) > 1080 or max(width, height) > 1920):
            raise ValueError("Video exceeds 1080p")
        if not width or not height:
            raise ValueError("Missing video dimensions")
        for frame in container.decode(stream):
            if frame.pts is None or frame.time_base is None or frame.is_corrupt:
                raise ValueError("Missing timestamps or corrupt frame")
            if (frame.width, frame.height) != (width, height):
                raise ValueError("Video dimensions changed")
            timestamp = float(frame.pts * frame.time_base)
            if not math.isfinite(timestamp) or (times and timestamp <= times[-1]):
                raise ValueError("Video timestamps must increase strictly")
            times.append(timestamp)
            if enforce_limits and (len(times) > MAX_SECONDS * MAX_FPS or timestamp - times[0] > MAX_SECONDS):
                raise ValueError("Video exceeds 120 seconds/frame limit")
        if len(times) < 2:
            raise ValueError("Video needs at least two decoded frames")
        if stream.frames and len(times) != stream.frames:
            raise ValueError("Truncated video (declared frame count differs)")
    # One millisecond permits normal container timestamp quantization (e.g. MKV).
    # Compare against the full timeline, not just average rate or neighboring frames.
    tolerance = max(0.0011, 0.02 / fps)
    is_cfr = all(abs((t - times[0]) - i / fps) <= tolerance for i, t in enumerate(times))
    duration = times[-1] - times[0] + 1 / fps
    start_ok = abs(times[0]) <= tolerance
    if enforce_limits and (not is_cfr or not start_ok):
        raise ValueError("Variable frame rate/nonzero start unsupported; export CFR with zero start before uploading")
    if enforce_limits and duration > MAX_SECONDS + tolerance:
        raise ValueError("Video exceeds 120 seconds")
    return {"fps": fps, "width": width, "height": height, "frames": len(times),
            "duration_seconds": duration, "source_start_seconds": times[0],
            "constant_frame_rate": is_cfr, "zero_start": start_ok,
            "pts_seconds": times, "mapping": "decoded presentation timestamps; no transforms"}
