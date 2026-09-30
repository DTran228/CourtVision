"""Experimental near-hoop ball recovery for reddish balls in our local clips.

Align a small view to the detected hoop, remove a short-term background, then
follow a moving color blob. This is a heuristic, not a second trained model.
"""

from collections import deque
import math

import cv2
import numpy as np


class MotionPath:
    """Require three descending observations before following a proposal."""

    def __init__(self, fps):
        self.max_gap = max(1, math.floor(0.25 * fps))
        self.previous_candidates = deque(maxlen=2)
        self.last = None
        self.velocity = (0, 0)
        self.contact = False

    def update(self, index, candidates):
        selected = None
        if self.last is not None and index - self.last["frame"] > self.max_gap:
            self.last = None
            self.contact = False
        last = self.last
        if last is not None:
            elapsed = index - last["frame"]
            predicted = [last["relative"][k] + self.velocity[k] * elapsed for k in range(2)]
            nearby = []
            for item in candidates:
                dx = item["relative"][0] - last["relative"][0]
                dy = item["relative"][1] - last["relative"][1]
                if not self.contact and dy < -0.05:
                    continue  # Do not jump upward to a spectator before rim contact.
                if abs(dx) > 0.35 and abs(dy) < 0.12:
                    continue  # Reject a sudden sideways jump to a rim fragment.
                if math.hypot(dx, dy) / elapsed < 0.04:
                    continue  # A nearly stationary orange fragment is weak evidence.
                if math.dist(item["relative"], predicted) <= 0.65:
                    nearby.append(item)
            if nearby:
                selected = min(nearby, key=lambda item: math.dist(item["relative"], predicted))
        elif len(self.previous_candidates) == 2:
            starts = []
            for first in self.previous_candidates[0]:
                for second in self.previous_candidates[1]:
                    for third in candidates:
                        ax, ay = first["relative"]
                        bx, by = second["relative"]
                        cx, cy = third["relative"]
                        if (max(abs(ax), abs(bx), abs(cx)) <= 0.9 and -3 <= ay < -0.15
                                and -0.35 <= cy <= 0.35 and by-ay > 0.04 and cy-by > 0.04
                                and cy-ay >= 0.2 and math.dist(first["relative"], second["relative"]) < 0.9
                                and math.dist(second["relative"], third["relative"]) < 0.9):
                            starts.append((cy-ay, third, second))
            if starts:
                _, selected, second = max(starts, key=lambda item: item[0])
                last = {**second, "frame": index-1}
        self.previous_candidates.append(candidates)
        if selected is None:
            return None  # Predicted coordinates are never emitted as observations.
        if last is not None:
            elapsed = index-last["frame"]
            self.velocity = tuple((selected["relative"][k]-last["relative"][k])/elapsed for k in range(2))
        self.last = {**selected, "frame": index}
        self.contact |= selected["relative"][1] >= -0.05
        return selected


class NearHoopRecovery:
    """Normalize hoop size to 64 pixels so the color/motion rules share a scale."""

    def __init__(self, fps):
        self.fps = fps
        self.index = -1
        self.history = deque(maxlen=9)
        self.path = MotionPath(fps)
        self.previous_hoop = None

    def reset(self):
        self.history.clear()
        self.path = MotionPath(self.fps)
        self.previous_hoop = None

    def update(self, frame, detections):
        self.index += 1
        hoops = [item for item in detections if item["class"] == "hoop"]
        if not hoops:
            self.reset()
            return None
        left, top, right, _ = max(hoops, key=lambda item: item["confidence"])["bbox"]
        width = right-left
        if width <= 0:
            raise ValueError("Hoop width must be positive.")
        center = (left+right)/2
        if self.previous_hoop is not None:
            old_x, old_y, old_width = self.previous_hoop
            if math.hypot(center-old_x, top-old_y) > old_width/2 or not 0.67 <= width/old_width <= 1.5:
                self.reset()
        self.previous_hoop = (center, top, width)
        scale = 64/width
        transform = np.array([[scale, 0, 192-center*scale], [0, scale, 192-top*scale]], dtype=np.float32)
        patch = cv2.warpAffine(frame, transform, (384, 384))
        candidates = []
        if len(self.history) >= 5:
            background = np.median(np.stack(self.history), axis=0).astype(np.uint8)
            difference = cv2.absdiff(patch, background).max(axis=2)
            hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
            # Red wraps around the hue scale; include both ends as well as orange.
            color = cv2.inRange(hsv, np.array([0, 35, 55]), np.array([25, 255, 255]))
            color = cv2.bitwise_or(color, cv2.inRange(hsv, np.array([165, 35, 55]), np.array([179, 255, 255])))
            mask = cv2.bitwise_and(color, (difference > 25).astype(np.uint8)*255)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                relative = [(x+w/2-192)/64, (y+h/2-192)/64]
                if (abs(relative[0]) <= 2 and -3 <= relative[1] <= 1.5 and 7 <= w <= 52
                        and 7 <= h <= 65 and 0.3 <= w/h <= 2 and area > 35 and area/(w*h) > 0.3):
                    bbox = [(x-192)/scale+center, (y-192)/scale+top,
                            (x+w-192)/scale+center, (y+h-192)/scale+top]
                    candidates.append({"relative": relative, "bbox": [round(v, 2) for v in bbox]})
        self.history.append(patch)
        selected = self.path.update(self.index, candidates)
        if selected is None:
            return None
        return {"class": "basketball", "bbox": selected["bbox"],
                "confidence": None, "source": "color_motion"}
