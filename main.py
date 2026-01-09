import cv2
import time
import argparse
import sys
from game_logic import GameLogic
from robot_interface import RobotInterface

def main():
    parser = argparse.ArgumentParser(description='Proustite Robot Soccer Main Controller')
    parser.add_argument('--team', type=str, default='blue', choices=['blue', 'yellow'], help='Target goal color (blue or yellow)')
    parser.add_argument('--nucleo', type=str, default='/dev/ttyACM0', help='Serial port for Nucleo')
    parser.add_argument('--esp32', type=str, default='/dev/ttyUSB0', help='Serial port for ESP32')
    
    args = parser.parse_args()
    
    # 1. Initialize Robot Interface
    print(f"Initializing Robot Interface on {args.nucleo} and {args.esp32}...")
    try:
        robot = RobotInterface(nucleo_port=args.nucleo, esp32_port=args.esp32)
    except Exception as e:
        print(f"Failed to initialize robot: {e}")
        # For testing without hardware, we might want to mock this, 
        # but for now we exit as hardware is required for operation.
        sys.exit(1)

    # 2. Initialize Camera
    print("Initializing Camera...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera")
        robot.close()
        sys.exit(1)

    # 3. Initialize Game Logic
    # If we are Blue team, we score in Yellow goal, and vice versa.
    game = GameLogic(robot, target_goal_color=args.team)
    
    print("Starting Game Loop. Press 'q' to quit.")
    print("Waiting 2 seconds before starting...")
    time.sleep(2)
    
    game.start_game()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break
                
            # Update Game Logic
            processed_frame = game.update(frame)
            
            # Show Feed
            if processed_frame is not None:
                cv2.imshow('Proustite Vision', processed_frame)
                
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            # minimal sleep to prevent CPU hogging if vision is fast
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        game.cleanup()
        cap.release()
        cv2.destroyAllWindows()
        robot.close()

if __name__ == "__main__":
    main()
