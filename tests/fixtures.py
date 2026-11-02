"""Explicitly synthetic media/detections. Never used by the production worker."""
from fractions import Fraction
from pathlib import Path

import av
import numpy as np


def make_video(path, pts=None, fps=30, width=200, height=200):
    path = Path(path)
    pts = pts if pts is not None else list(range(36))
    with av.open(str(path), "w", format="mp4") as output:
        stream = output.add_stream("mpeg4", rate=fps)
        stream.width, stream.height = width, height
        stream.pix_fmt = "yuv420p"
        stream.time_base = Fraction(1, fps)
        for t in pts:
            frame = av.VideoFrame.from_ndarray(np.zeros((height, width, 3), dtype=np.uint8), format="bgr24")
            frame.pts, frame.time_base = t, Fraction(1, fps)
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)
    return path


class ScriptedDetector:
    def __init__(self):
        self.index = 0

    def detect(self, frame):
        i = self.index
        self.index += 1
        hoop = {"class": "hoop", "confidence": .9, "bbox": [80, 100, 120, 120]}
        if i >= 10:
            return [hoop]
        y = 60 + i*8
        return [hoop, {"class": "basketball", "confidence": .9, "bbox": [97, y-3, 103, y+3]}]
