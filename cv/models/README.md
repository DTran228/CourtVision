# Model used for Milestone 2

We use the **E-BARD YOLOv8n basketball detector**, developed by **Gabriele Giudici**.
This is an existing trained model, not a model trained by CourtVision.

- Source and model card: https://huggingface.co/GabrieleGiudici/E-BARD-detection-models
- Upstream filename: `BODD_yolov8n_0001.pt`
- Revision: `3f4789c4431aa73269f60107a4ba0a5f86b7af8b`
- Local filename: `ebard-yolov8n.pt`
- SHA-256: `dfe3534d51bb21024d1a400c37f0c1fbf0c8b96ea9a56a5f3cb5454813bfd641`
- Model card license: **CC-BY-4.0**. We use the downloaded weights unchanged.
- Ultralytics code and base models have their own published licensing terms:
  https://github.com/ultralytics/ultralytics/blob/main/LICENSE

The loaded model reports four classes: basketball, hoop, player, and referee.
Our wrapper keeps only basketball and hoop. The model card describes training on
NBA broadcast footage and limitations for small balls and other camera setups.
Its published metrics do not measure performance on our videos.

Download from the project root:

```powershell
.\.venv\Scripts\python.exe cv/src/download_model.py
```

The script pins a repository revision and checks the exact file hash, making the
experiment reproducible. It downloads only weights; it does not upload footage.
Weights are excluded from Git. Commit this README and the download script instead.
Use only model files from sources you trust: PyTorch checkpoints can contain more
than numerical arrays. A matching hash verifies the chosen file, not its safety.
