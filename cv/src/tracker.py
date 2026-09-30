"""A small single-ball tracker: associate nearby detections across frames.

No model, image processing, or invented positions live here. Keeping this logic
separate lets us test it with simple dictionaries instead of running YOLO.
"""

from collections import deque
import math


def box_center(detection):
    """Convert [left, top, right, bottom] into the box's (x, y) center."""
    left, top, right, bottom = detection["bbox"]
    return ((left + right) / 2, (top + bottom) / 2)


class BallTracker:
    """Follow one candidate until too many consecutive frames cannot match it."""

    def __init__(self, max_distance, max_missing=6, trail_length=30):
        if not math.isfinite(max_distance) or max_distance <= 0:
            raise ValueError("Maximum distance must be positive and finite.")
        if max_missing < 0 or trail_length < 1:
            raise ValueError("Missing-frame allowance must be nonnegative; trail length must be positive.")
        self.max_distance = max_distance
        self.max_missing = max_missing
        self.center = None
        self.missing = 0
        self.track_id = 0
        self.frame_number = -1
        # deque drops the oldest point when its fixed capacity is reached.
        self.trail = deque(maxlen=trail_length)

    def update(self, detections):
        """Call exactly once per frame, including frames with no detections.

        Returns an observed position only when a candidate was matched. Track IDs
        identify continuous segments, not a proven physical ball identity.
        """
        self.frame_number += 1
        balls = [item for item in detections if item["class"] == "basketball"]
        selected = None
        if self.center is None:
            if balls:
                selected = max(balls, key=lambda item: (item["confidence"] or 0))
                self.track_id += 1
        else:
            # Gate: reject candidates too far from the last observed position.
            previous_center = self.center
            nearby = [item for item in balls
                      if math.dist(box_center(item), previous_center) <= self.max_distance]
            if nearby:
                # Confidence breaks ties; distance is the main matching rule.
                selected = min(nearby, key=lambda item: (
                    math.dist(box_center(item), previous_center), -(item["confidence"] or 0)))

        if selected is not None:
            self.center = box_center(selected)
            self.missing = 0
            self.trail.append((self.frame_number, self.center))
            return {"track_id": self.track_id, "status": "observed",
                    "center": list(self.center), "bbox": selected["bbox"],
                    "confidence": selected["confidence"], "source": selected.get("source", "model"), "missing_frames": 0}

        status = "searching"
        if self.center is not None:
            self.missing += 1
            status = "missing"
            if self.missing > self.max_missing:
                # A later candidate starts a new segment, with no line to the old one.
                self.center = None
                self.trail.clear()
                status = "lost"
        return {"track_id": self.track_id if self.center is not None else None,
                "status": status, "center": None, "bbox": None,
                "confidence": None, "missing_frames": self.missing}
