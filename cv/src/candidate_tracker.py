"""Experimental bounded multi-ball association; predictions are never evidence."""
from collections import deque
import math

from cv.src.tracker import box_center


class CandidateTracker:
    def __init__(self, fps, diagonal, max_tracks=8, gap_seconds=0.20):
        self.fps, self.diagonal = fps, diagonal
        self.max_tracks, self.gap = max_tracks, gap_seconds
        self.tracks = {}
        self.next_id = 1
        self.selected = None
        self.previous_hoop = None
        self.last_time = None
        self.trail = deque(maxlen=max(2, round(fps*.5)))

    def update(self, detections, timestamp, shot_active=False):
        if self.last_time is not None and timestamp <= self.last_time:
            raise ValueError("Timestamps must increase")
        self.last_time = timestamp
        hoops = [d for d in detections if d["class"] == "hoop"]
        hoop = max(hoops, key=lambda d: d["confidence"] or 0) if hoops else None
        if hoop:
            center = box_center(hoop)
            width = hoop["bbox"][2]-hoop["bbox"][0]
            if self.previous_hoop:
                old_center, old_width = self.previous_hoop
                if math.dist(center, old_center) > .5*old_width or not .67 <= width/old_width <= 1.5:
                    self.tracks.clear()
                    self.selected = None
                    self.trail.clear()
            self.previous_hoop = (center, width)
        for ident in list(self.tracks):
            if timestamp-self.tracks[ident]["time"] > self.gap + 1e-6:
                del self.tracks[ident]
        balls = [d for d in detections if d["class"] == "basketball"][:32]
        edges = []
        ambiguous_tracks = set()
        predictions = {}
        for ident, track in self.tracks.items():
            dt = timestamp-track["time"]
            predicted = [track["center"][k] + track["velocity"][k]*dt for k in (0, 1)]
            predictions[ident] = predicted
            distances = []
            gate = self.diagonal*(.012 + .7*dt)
            for index, ball in enumerate(balls):
                w = ball["bbox"][2]-ball["bbox"][0]
                h = ball["bbox"][3]-ball["bbox"][1]
                size = math.sqrt(max(0, w*h))
                distance = math.dist(predicted, box_center(ball))
                if track["size"] > 0 and .45 <= size/track["size"] <= 2.2 and distance <= gate:
                    cost = distance/gate + .15*abs(math.log(size/track["size"]))
                    edges.append((cost, ident, index, size))
                    distances.append(cost)
            distances.sort()
            if len(distances) > 1 and distances[1]-distances[0] < .12:
                ambiguous_tracks.add(ident)
        used_tracks, used_balls = set(), set()
        observed = {}
        for _, ident, index, size in sorted(edges):
            if ident in used_tracks or index in used_balls or ident in ambiguous_tracks:
                continue
            track = self.tracks[ident]
            center = box_center(balls[index])
            dt = timestamp-track["time"]
            track["velocity"] = [(center[k]-track["center"][k])/dt for k in (0, 1)]
            track.update(center=center, time=timestamp, size=size)
            track["history"].append((timestamp, center))
            observed[ident] = balls[index]
            used_tracks.add(ident)
            used_balls.add(index)
        if self.selected in ambiguous_tracks:
            # No identity assertion through a crossing; force a new segment ID.
            self.tracks.clear()
            self.selected = None
            self.trail.clear()
            return self.empty("ambiguous", None)
        for index, ball in enumerate(balls):
            if index in used_balls or len(self.tracks) >= self.max_tracks:
                continue
            center = box_center(ball)
            w, h = ball["bbox"][2]-ball["bbox"][0], ball["bbox"][3]-ball["bbox"][1]
            ident = self.next_id
            self.next_id += 1
            self.tracks[ident] = {"center": center, "time": timestamp, "velocity": [0, 0],
                                  "size": math.sqrt(max(0, w*h)), "history": deque([(timestamp, center)], maxlen=round(self.fps)+2)}
            observed[ident] = ball
        if self.selected not in self.tracks:
            self.selected = None
            self.trail.clear()
        if self.selected is not None and hoop and not shot_active:
            x, y = self.tracks[self.selected]["center"]
            if y > hoop["bbox"][1] + width*2:
                self.selected = None
                self.trail.clear()
        if self.selected is None and hoop:
            target = ((hoop["bbox"][0]+hoop["bbox"][2])/2, hoop["bbox"][1])
            plausible = []
            for ident in observed:
                history = self.tracks[ident]["history"]
                first_t, first = history[0]
                last_t, last = history[-1]
                if last_t-first_t < .05 or len(history) < 3:
                    continue
                movement = math.dist(first, last)
                approaching = math.dist(first, target)-math.dist(last, target)
                above = target[1]-3*width <= last[1] <= target[1]+.3*width
                if movement > .12*width and approaching > .08*width and above and abs(last[0]-target[0]) <= 2*width:
                    plausible.append((-approaching, ident))
            if plausible:
                self.selected = min(plausible)[1]
        ident = self.selected
        if ident in observed:
            ball = observed[ident]
            center = list(box_center(ball))
            self.trail.append((round(timestamp*self.fps), center))
            return {"track_id": ident, "status": "observed", "center": center,
                    "predicted_center": predictions.get(ident), "bbox": ball["bbox"],
                    "confidence": ball["confidence"], "source": ball.get("source", "model"), "missing_frames": 0}
        return self.empty("missing" if ident else "searching", predictions.get(ident))

    def empty(self, status, prediction):
        return {"track_id": self.selected, "status": status, "center": None,
                "predicted_center": prediction, "bbox": None, "confidence": None, "missing_frames": 1}
