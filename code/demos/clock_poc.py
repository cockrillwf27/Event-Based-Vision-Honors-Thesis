import cv2
import numpy as np
import time
from datetime import datetime

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=1280,
    capture_height=720,
    display_width=640,
    display_height=360,
    framerate=30,
    flip_method=0,
):
    return (
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            sensor_id,
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

def draw_analog_clock(img, center, radius, hour, minute, second):
    # Draw clock face
    cv2.circle(img, center, radius, (50, 50, 50), -1)
    cv2.circle(img, center, radius, (200, 200, 200), 3)
    cv2.circle(img, center, 5, (255, 255, 255), -1)

    # Hour marks
    for i in range(12):
        angle = np.deg2rad(i * 30 - 90)
        x1 = int(center[0] + (radius - 15) * np.cos(angle))
        y1 = int(center[1] + (radius - 15) * np.sin(angle))
        x2 = int(center[0] + (radius - 5) * np.cos(angle))
        y2 = int(center[1] + (radius - 5) * np.sin(angle))
        cv2.line(img, (x1, y1), (x2, y2), (220, 220, 220), 2)

    # Hour hand
    hour_angle = np.deg2rad((hour % 12) * 30 + minute * 0.5 - 90)
    hx = int(center[0] + (radius * 0.5) * np.cos(hour_angle))
    hy = int(center[1] + (radius * 0.5) * np.sin(hour_angle))
    cv2.line(img, center, (hx, hy), (100, 200, 255), 6)

    # Minute hand
    minute_angle = np.deg2rad(minute * 6 - 90)
    mx = int(center[0] + (radius * 0.75) * np.cos(minute_angle))
    my = int(center[1] + (radius * 0.75) * np.sin(minute_angle))
    cv2.line(img, center, (mx, my), (100, 255, 100), 4)

    # Second hand
    second_angle = np.deg2rad(second * 6 - 90)
    sx = int(center[0] + (radius * 0.85) * np.cos(second_angle))
    sy = int(center[1] + (radius * 0.85) * np.sin(second_angle))
    cv2.line(img, center, (sx, sy), (50, 50, 255), 2)

def main():
    print("Opening CSI camera...")
    cap = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("Error: Could not open CSI camera")
        return

    print("Camera opened successfully!")
    print("Press 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Create a wider canvas (camera on left, clock GUI on right)
        h, w = frame.shape[:2]
        canvas = np.zeros((h, w + 400, 3), dtype=np.uint8)
        canvas[:, :w] = frame

        # === Right side: Clean GUI ===
        # Background
        cv2.rectangle(canvas, (w, 0), (w + 400, h), (30, 30, 30), -1)

        # Title
        cv2.putText(canvas, "Clock Proof of Concept", (w + 30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (220, 220, 220), 2)

        # Get current system time (placeholder - later we replace this with detected time)
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        second = now.second

        # Digital time
        digital_time = now.strftime("%H:%M:%S")
        cv2.putText(canvas, digital_time, (w + 80, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 180), 3)

        cv2.putText(canvas, "Digital Time", (w + 120, 160),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

        # Analog clock
        clock_center = (w + 200, 320)
        draw_analog_clock(canvas, clock_center, 110, hour, minute, second)

        cv2.putText(canvas, "Analog Clock", (w + 130, 460),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

        # Status
        cv2.putText(canvas, "Status: Using system time", (w + 40, h - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 255), 1)
        cv2.putText(canvas, "(Next: detect real clock hands)", (w + 40, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 100, 100), 1)

        # Show the combined window
        cv2.imshow("Clock Proof of Concept", canvas)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
