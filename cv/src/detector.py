"""Load our basketball model once, then detect objects in individual frames."""

from pathlib import Path

from ultralytics import YOLO
from ultralytics.engine.results import Results

# Resolve the default relative to this file, not the terminal's current folder.
DEFAULT_WEIGHTS = Path(__file__).resolve().parents[1] / "models" / "ebard-yolov8n.pt"


class Detector:
    """Keep the loaded model and its settings together between frames."""

    def __init__(self, weights=DEFAULT_WEIGHTS, confidence=0.25, image_size=704):
        if not Path(weights).is_file():
            raise ValueError("Model weights not found. Follow cv/models/README.md first.")
        self.model = YOLO(str(weights))
        self.confidence = confidence
        self.image_size = image_size

        # Read class IDs from the model instead of assuming what 0 or 1 means.
        self.labels = {}
        for class_id, name in self.model.names.items():
            name = name.lower().strip()
            if name in ("basketball", "ball"):
                self.labels[class_id] = "basketball"
            elif name in ("hoop", "basketball hoop"):
                self.labels[class_id] = "hoop"
        if set(self.labels.values()) != {"basketball", "hoop"}:
            raise ValueError(f"This model must contain basketball and hoop classes: {self.model.names}")

    def detect(self, frame):
        """Return plain dictionaries: class, confidence, and pixel bounding box."""
        results = self.model.predict(
            frame,
            conf=self.confidence,
            imgsz=self.image_size,
            classes=list(self.labels),
            device="cpu",  # Runs on this laptop without installing CUDA.
            verbose=False,
            stream=False,  # Return a list instead of yielding results one at a time.
        )

        # YOLO supports other tasks too. Check the result before using its boxes.
        if not isinstance(results, list) or not results:
            raise ValueError("Expected a non-empty list of YOLO results.")
        result = results[0]
        if not isinstance(result, Results):
            raise ValueError("Expected detection results, not feature tensors.")
        boxes = result.boxes
        if boxes is None:
            raise ValueError("This model did not return object-detection boxes.")

        detections = []
        for box in boxes:
            class_id = int(box.cls.item())
            # xyxy is [left, top, right, bottom] in the ORIGINAL frame's pixels.
            detections.append({
                "class": self.labels[class_id],
                "confidence": round(float(box.conf.item()), 4),
                "bbox": [round(value, 2) for value in box.xyxy[0].tolist()],
            })
        return detections
