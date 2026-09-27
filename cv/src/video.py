"""Read a video and print basic information. No ball or shot detection yet.

Run from the CourtVision project root:
    .venv/Scripts/python.exe cv/src/video.py "cv/sample_videos/threemade.mp4"
"""

import argparse
from pathlib import Path

import cv2


def main():
    # 1. Get the video path typed after the script's name in the terminal.
    parser = argparse.ArgumentParser(description="Read a video with OpenCV.")
    parser.add_argument("video", type=Path, help="Path to a local video file")
    args = parser.parse_args()

    if not args.video.is_file():
        parser.exit(1, f"Error: Video file not found: {args.video}\n")

    # 2. Open the file. FPS means frames (individual images) per second.
    capture = cv2.VideoCapture(str(args.video))
    frames_read = 0
    # Start with defaults; each decoded frame supplies the actual dimensions.
    width = 0
    height = 0
    try:
        if not capture.isOpened():
            parser.exit(1, "Error: OpenCV could not open this video.\n")

        fps = capture.get(cv2.CAP_PROP_FPS)

        # 3. Read one image at a time instead of loading the whole video into RAM.
        while True:
            success, frame = capture.read()
            if not success:
                # This can mean the end of the video or a decoding failure.
                break
            # Image dimensions are stored in height, width order.
            height, width = frame.shape[:2]
            frames_read += 1
    except cv2.error as error:
        parser.exit(1, f"Error: OpenCV could not read this video: {error}\n")
    finally:
        # Always close the video, including when an error stops the script.
        capture.release()

    if frames_read == 0:
        parser.exit(1, "Error: No frames could be decoded.\n")

    # 4. Print the results. Duration is approximate: frame count divided by FPS.
    print(f"Video: {args.video}")
    print(f"Frames decoded: {frames_read}")
    print(f"Resolution: {width} x {height}")
    if fps > 0:
        print(f"FPS reported by file: {fps:.2f}")
        print(f"Approximate decoded duration: {frames_read / fps:.2f} seconds")
    else:
        print("FPS and duration: unavailable")


# Start only when this file is run directly, not when another file imports it.
if __name__ == "__main__":
    main()
