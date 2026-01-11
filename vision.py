import cv2
import numpy as np

def detect_objects(frame):
    # Convert BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Define color ranges in HSV
    # Orange balls
    orange_lower = np.array([0, 130, 130])
    orange_upper = np.array([20, 255, 255])
    
    # Yellow goals
    yellow_lower = np.array([21, 50, 100])
    yellow_upper = np.array([40, 255, 255])
    
    # Blue goals
    blue_lower = np.array([100, 130, 50])
    blue_upper = np.array([140, 255, 255])

    # Create masks
    orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)

    # Morphological operations to remove noise
    kernel = np.ones((5, 5), np.uint8)
    orange_mask = cv2.morphologyEx(orange_mask, cv2.MORPH_OPEN, kernel)
    yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN, kernel)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)

    detections = []

    # Function to find and draw bounding boxes
    def process_mask(mask, color_name, draw_color, label, min_area=150):
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

    # Draw boxes for each color
    process_mask(orange_mask, "orange", (0, 165, 255), "Ball", min_area=30)
    process_mask(yellow_mask, "yellow", (0, 255, 255), "Yellow Goal")
    process_mask(blue_mask, "blue", (255, 0, 0), "Blue Goal")

    return frame, detections

def main():
    webcam = cv2.VideoCapture(0) # Use the first webcam
    
    if not webcam.isOpened():
        print("Error: Could not open webcam.")
        return

    while True:
        ret, frame = webcam.read()
        if not ret:
            print("Error: Failed to capture image.")
            break

        processed_frame, detections = detect_objects(frame)

        cv2.imshow('Object Detection', processed_frame)

        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    webcam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

