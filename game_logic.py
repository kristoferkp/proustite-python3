import time
import cv2
import math
from robot_interface import RobotInterface
from vision import detect_objects

class GameLogic:
    def __init__(self, robot: RobotInterface, target_goal_color="blue", opponent_goal_color="yellow"):
        self.robot = robot
        self.target_goal_color = target_goal_color # The goal we want to score in (opponent's goal)
        self.own_goal_color = "yellow" if target_goal_color == "blue" else "blue"
        
        # State Management
        self.state = "IDLE"
        self.state_start_time = 0
        
        # Game Progress
        self.balls_collected = 0
        self.max_balls = 5
        self.game_start_time = 0
        self.game_duration = 150 # seconds
        
        # Movement Parameters
        self.search_rotation_speed = 0.8
        self.approach_speed = 0.3
        self.approach_kP = 0.003 # Proportional gain for turning
        self.deposit_time = 3.0 # How long to run the depositor
        self.deposit_backup_speed = -0.1
        
        # Image Parameters (Assumes 640x480 typically, but will adjust)
        self.frame_width = 640
        self.frame_center_x = 320
        
    def set_state(self, new_state):
        self.state = new_state
        self.state_start_time = time.time()
        print(f"State changed to: {self.state}")
        
    def start_game(self):
        self.game_start_time = time.time()
        self.balls_collected = 0
        self.set_state("SEARCH_BALL")
        
    def stop_game(self):
        self.set_state("IDLE")
        self.robot.stop_movement()
        self.robot.set_ball_collector("stop")

    def update(self, frame):
        """
        Main game loop update.
        Args:
            frame: opencv image frame from camera
        """
        if frame is None:
            return
            
        self.frame_width = frame.shape[1]
        self.frame_center_x = self.frame_width // 2
        
        # 1. Vision Processing
        processed_frame, detections = detect_objects(frame)
        
        # Filter detections
        balls = [d for d in detections if d['label'] == 'Ball']
        goals = [d for d in detections if 'Goal' in d['label']]
        target_goal = [d for d in goals if self.target_goal_color.lower() in d['label'].lower()]

        current_time = time.time()
        
        # Check game time
        if self.state != "IDLE" and (current_time - self.game_start_time) > self.game_duration:
            print("Game Over")
            self.stop_game()

        # 2. State Machine
        if self.state == "IDLE":
            self.robot.stop_movement()
            
        elif self.state == "SEARCH_BALL":
            # Spin to find a ball
            self.robot.set_ball_collector("forward") # Keep intake on just in case
            
            if len(balls) > 0:
                # Found a ball, target the largest/closest one
                closest_ball = max(balls, key=lambda b: b['area'])
                self.target_ball = closest_ball
                self.set_state("APPROACH_BALL")
            else:
                self.robot.send_velocity_command(0, 0, self.search_rotation_speed)

        elif self.state == "APPROACH_BALL":
            if len(balls) == 0:
                # Lost the ball
                self.set_state("SEARCH_BALL")
                return processed_frame

            # Update target (simple: pick largest again or track?)
            # Picking largest is safest for now
            closest_ball = max(balls, key=lambda b: b['area'])
            
            # Control Logic
            # Steering: PD control on x-offset
            error_x = self.frame_center_x - closest_ball['center'][0]
            omega = error_x * self.approach_kP
            
            # Speed: Constant forward
            # If ball is very close (large area), we might be collecting it
            if closest_ball['area'] > 20000: # Threshold for "close enough to suck"
                self.set_state("COLLECTING")
            else:
                self.robot.send_velocity_command(self.approach_speed, 0, omega)
                self.robot.set_ball_collector("forward")

        elif self.state == "COLLECTING":
            # Drive forward blindly for a bit to ensure intake
            self.robot.send_velocity_command(self.approach_speed, 0, 0)
            self.robot.set_ball_collector("forward")
            
            if (current_time - self.state_start_time) > 1.5:
                # Assume collected
                self.balls_collected += 1
                if self.balls_collected >= self.max_balls:
                    self.set_state("SEARCH_GOAL")
                else:
                    self.set_state("SEARCH_BALL")

        elif self.state == "SEARCH_GOAL":
            self.robot.set_ball_collector("stop") # specific to not waste power? or keep holding?
            # "For the balls to stay in the collector, the drone motor needs to stay in the ball sucking mode."
            # So keep it ON ('forward')
            self.robot.set_ball_collector("forward")
            
            if len(target_goal) > 0:
                self.set_state("APPROACH_GOAL")
            else:
                self.robot.send_velocity_command(0, 0, self.search_rotation_speed)

        elif self.state == "APPROACH_GOAL":
            self.robot.set_ball_collector("forward") # Keep holding balls
            
            if len(target_goal) == 0:
                self.set_state("SEARCH_GOAL")
                return processed_frame
                
            goal = max(target_goal, key=lambda g: g['area'])
            
            error_x = self.frame_center_x - goal['center'][0]
            omega = error_x * self.approach_kP
            
            # Stop if close enough
            if goal['area'] > 40000: # Tune this threshold
                self.set_state("DEPOSITING")
            else:
                 self.robot.send_velocity_command(self.approach_speed, 0, omega)

        elif self.state == "DEPOSITING":
            # "To deposit the balls, the drone motor needs to reverse its direction and drive a bit backwards"
            self.robot.set_ball_collector("reverse")
            self.robot.send_velocity_command(self.deposit_backup_speed, 0, 0)
            
            if (current_time - self.state_start_time) > self.deposit_time:
                self.balls_collected = 0
                self.set_state("BACK_OFF")
                
        elif self.state == "BACK_OFF":
             # Move away from goal to start searching again
             self.robot.send_velocity_command(-0.2, 0, 0)
             if (current_time - self.state_start_time) > 1.0:
                 self.set_state("SEARCH_BALL")

        return processed_frame

    def cleanup(self):
        self.robot.stop_movement()
        self.robot.set_ball_collector("stop")
