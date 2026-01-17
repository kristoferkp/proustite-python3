import cv2
import numpy as np
import copy

# Default colors configuration
DEFAULT_COLORS = {
    "orange": {
        "lower": np.array([0, 130, 130]),
        "upper": np.array([20, 255, 255]),
        "label": "Ball",
        "draw_color": (0, 165, 255),
        "min_area": 30
    },
    "yellow": {
        "lower": np.array([21, 50, 100]),
        "upper": np.array([40, 255, 255]),
        "label": "Yellow Goal",
        "draw_color": (0, 255, 255),
        "min_area": 150
    },
    "blue": {
        "lower": np.array([100, 130, 50]),
        "upper": np.array([140, 255, 255]),
        "label": "Blue Goal",
        "draw_color": (255, 0, 0),
        "min_area": 150
    }
}

def detect_objects(frame, colors=None):
    if colors is None:
        colors = DEFAULT_COLORS

    # Convert BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    detections = []
    
    # Morphological operations kernel
    kernel = np.ones((5, 5), np.uint8)

    # Function to find and draw bounding boxes
    def process_mask(mask, draw_color, label, min_area):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area: # Filter small noise
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(frame, (x, y), (x + w, y + h), draw_color, 2)
                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, draw_color, 2)
                detections.append({
                    "label": label,
                    "x": x, "y": y, "w": w, "h": h,
                    "center": (x + w // 2, y + h // 2),
                    "area": area
                })

    for color_name, config in colors.items():
        mask = cv2.inRange(hsv, config['lower'], config['upper'])
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        process_mask(mask, config['draw_color'], config['label'], config['min_area'])

    return frame, detections

def nothing(x):
    pass

def main():
    webcam = cv2.VideoCapture(0) # Use the first webcam
    
    if not webcam.isOpened():
        print("Error: Could not open webcam.")
        return

    # Calibration state
    calibrating = False
    calibration_keys = list(DEFAULT_COLORS.keys())
    calibration_idx = 0
    current_colors = copy.deepcopy(DEFAULT_COLORS)
    
    cv2.namedWindow('Calibration')
    cv2.createTrackbar('H Min', 'Calibration', 0, 179, nothing)
    cv2.createTrackbar('S Min', 'Calibration', 0, 255, nothing)
    cv2.createTrackbar('V Min', 'Calibration', 0, 255, nothing)
    cv2.createTrackbar('H Max', 'Calibration', 179, 179, nothing)
    cv2.createTrackbar('S Max', 'Calibration', 255, 255, nothing)
    cv2.createTrackbar('V Max', 'Calibration', 255, 255, nothing)

    def update_trackbars(color_name):
        c = current_colors[color_name]
        cv2.setTrackbarPos('H Min', 'Calibration', c['lower'][0])
        cv2.setTrackbarPos('S Min', 'Calibration', c['lower'][1])
        cv2.setTrackbarPos('V Min', 'Calibration', c['lower'][2])
        cv2.setTrackbarPos('H Max', 'Calibration', c['upper'][0])
        cv2.setTrackbarPos('S Max', 'Calibration', c['upper'][1])
        cv2.setTrackbarPos('V Max', 'Calibration', c['upper'][2])

    # Initialize trackbars with first color
    update_trackbars(calibration_keys[calibration_idx])

    while True:
        ret, frame = webcam.read()
        if not ret:
            print("Error: Failed to capture image.")
            break

        if calibrating:
            active_color = calibration_keys[calibration_idx]
            
            # Read trackbars
            h_min = cv2.getTrackbarPos('H Min', 'Calibration')
            s_min = cv2.getTrackbarPos('S Min', 'Calibration')
            v_min = cv2.getTrackbarPos('V Min', 'Calibration')
            h_max = cv2.getTrackbarPos('H Max', 'Calibration')
            s_max = cv2.getTrackbarPos('S Max', 'Calibration')
            v_max = cv2.getTrackbarPos('V Max', 'Calibration')

            current_colors[active_color]['lower'] = np.array([h_min, s_min, v_min])
            current_colors[active_color]['upper'] = np.array([h_max, s_max, v_max])

            # Show mask for calibration
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, current_colors[active_color]['lower'], current_colors[active_color]['upper'])
            cv2.imshow('Calibration Mask', mask)
        else:
            try:
                cv2.destroyWindow('Calibration Mask')
            except:
                pass

        processed_frame, detections = detect_objects(frame, current_colors)

        if calibrating:
            cv2.putText(processed_frame, f"CALIBRATING: {calibration_keys[calibration_idx]}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(processed_frame, "Keys: 'n' next color, 'c' toggle, 'p' print", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imshow('Object Detection', processed_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            calibrating = not calibrating
            if calibrating:
                print(f"Started calibration for {calibration_keys[calibration_idx]}")
                update_trackbars(calibration_keys[calibration_idx])
            else:
                print("Stopped calibration")
        elif key == ord('n') and calibrating:
            calibration_idx = (calibration_idx + 1) % len(calibration_keys)
            print(f"Switched to {calibration_keys[calibration_idx]}")
            update_trackbars(calibration_keys[calibration_idx])
        elif key == ord('p'):
             print(f"Current Settings for {calibration_keys[calibration_idx]}:")
             print(f"Lower: {current_colors[calibration_keys[calibration_idx]]['lower'].tolist()}")
             print(f"Upper: {current_colors[calibration_keys[calibration_idx]]['upper'].tolist()}")

    webcam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

