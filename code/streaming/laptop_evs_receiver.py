#!/usr/bin/env python3
"""
Laptop-side receiver + EVT 3.0 decoder for Triton2 EVS.

Receives length-prefixed raw frames from the Jetson, decodes EVT 3.0
event words, and accumulates them into a live CD-style visualization.

All raw dumps and screenshots are saved under ./evs_output/

Usage:
    python laptop_evs_receiver.py [port=5000]

Requires: pip install opencv-python numpy
"""

import socket
import struct
import sys
import os
import numpy as np
import cv2

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
HOST = "0.0.0.0"
OUTPUT_DIR = "evs_output"

# Triton2 EVS IMX636 resolution
WIDTH, HEIGHT = 1280, 720

def recvall(sock, n):
    data = b""
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

class Evt3Decoder:
    """Minimal stateful EVT 3.0 decoder for CD events."""
    def __init__(self):
        self.time_high = 0
        self.time_low = 0
        self.y = 0
        self.base_x = 0
        self.polarity = 0

    def decode(self, raw_bytes):
        """Decode a chunk of EVT 3.0 words into a list of (x, y, p) events."""
        if len(raw_bytes) < 2:
            return []
        words = np.frombuffer(raw_bytes, dtype=np.uint16)
        events = []
        for w in words:
            etype = (w >> 12) & 0xF
            payload = w & 0xFFF

            if etype == 0x0:          # EVT_ADDR_Y
                self.y = payload & 0x7FF
            elif etype == 0x2:        # EVT_ADDR_X (single event)
                x = payload & 0x7FF
                p = (payload >> 11) & 1
                if 0 <= x < WIDTH and 0 <= self.y < HEIGHT:
                    events.append((x, self.y, p))
            elif etype == 0x3:        # VECT_BASE_X
                self.base_x = payload & 0x7FF
                self.polarity = (payload >> 11) & 1
            elif etype == 0x4:        # VECT_12
                for i in range(12):
                    if payload & (1 << i):
                        x = self.base_x + i
                        if 0 <= x < WIDTH and 0 <= self.y < HEIGHT:
                            events.append((x, self.y, self.polarity))
                self.base_x += 12
            elif etype == 0x5:        # VECT_8
                for i in range(8):
                    if payload & (1 << i):
                        x = self.base_x + i
                        if 0 <= x < WIDTH and 0 <= self.y < HEIGHT:
                            events.append((x, self.y, self.polarity))
                self.base_x += 8
            elif etype == 0x6:        # EVT_TIME_LOW
                self.time_low = payload
            elif etype == 0x8:        # EVT_TIME_HIGH
                self.time_high = payload
        return events

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output folder: {os.path.abspath(OUTPUT_DIR)}")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"Listening on {HOST}:{PORT} ...")

    conn, addr = srv.accept()
    print(f"Jetson connected from {addr}")

    decoder = Evt3Decoder()
    frame = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    frame_count = 0
    total_events = 0
    raw_saved = 0

    try:
        while True:
            len_bytes = recvall(conn, 4)
            if not len_bytes:
                break
            (length,) = struct.unpack("!I", len_bytes)
            payload = recvall(conn, length)
            if not payload:
                break

            events = decoder.decode(payload)
            total_events += len(events)

            # Save a few raw packets for debugging (first 10 only)
            if raw_saved < 10:
                raw_path = os.path.join(OUTPUT_DIR, f"raw_{raw_saved:04d}.bin")
                with open(raw_path, "wb") as f:
                    f.write(payload)
                raw_saved += 1

            # Accumulate into frame
            for x, y, p in events:
                frame[y, x] = 255 if p else 128

            # Decay
            frame = (frame * 0.95).astype(np.uint8)

            # Display
            disp = cv2.resize(frame, (960, 540))
            cv2.imshow("Triton2 EVS (decoded)", disp)

            # Save a screenshot every 60 frames
            if frame_count > 0 and frame_count % 60 == 0:
                img_path = os.path.join(OUTPUT_DIR, f"frame_{frame_count:04d}.png")
                cv2.imwrite(img_path, disp)

            if frame_count % 30 == 0:
                print(f"Frame {frame_count}: {len(events)} events  (total {total_events})")

            frame_count += 1
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        conn.close()
        srv.close()
        cv2.destroyAllWindows()
        print(f"Received {frame_count} frames, {total_events} events total")
        print(f"Files saved in: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    main()
