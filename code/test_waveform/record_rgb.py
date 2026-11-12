#!/usr/bin/env python3
"""Minimal RGB video recorder for Jetson CSI IMX477."""
import argparse
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=30)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    pipeline = (
        f"nvarguscamerasrc num-buffers={int(args.duration * 30)} ! "
        f"'video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1' ! "
        f"nvvidconv ! 'video/x-raw,format=I420' ! "
        f"x264enc speed-preset=ultrafast ! "
        f"mp4mux ! filesink location={args.output}"
    )

    print(f"Recording ~{args.duration}s RGB video to {args.output}")
    try:
        subprocess.run(
            f"gst-launch-1.0 -e {pipeline}",
            shell=True,
            timeout=args.duration + 10,
            check=True
        )
        print("Done")
    except subprocess.TimeoutExpired:
        print("Stopped after duration")
    except subprocess.CalledProcessError as e:
        print(f"GStreamer error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
