import time
import cv2
import math
from robot_interface import RobotInterface
from vision import detect_objects

class GameLogic:
    def __init__(self, robot: RobotInterface, target_goal_color="blue"):
        self.robot = robot
        self.target_goal_color = target_goal_color # The goal we want to score in (opponent's goal)
        self.own_goal_color = "yellow" if target_goal_color == "blue" else "blue"
        
        # State Management
        self.state = "IDLE"
        self.state_start_time = 0
        
        # Game Progress
        self.balls_collected = 0
        self.max_balls = 3
        self.game_start_time = 0
        self.game_duration = 150 # seconds
        
        # Movement Parameters
        self.search_rotation_speed = 2
        self.approach_speed = 0.75
        self.approach_kP = 0.003 # Proportional gain for turning
        self.deposit_time = 3 # How long to run the depositor
        self.deposit_backup_speed = -0.6
        
        # Image Parameters (Assumes 640x480 typically, but will adjust)
        self.frame_width = 640
        self.frame_center_x = 320
        
        # Ball collection detection
        self.ball_was_centered = False
        self.center_tolerance = 80 # pixels from center to consider "centered"
        self.bottom_threshold = 0.85 # Ball must be in bottom 15% of frame (y > 85% of height)
        
        # Goal approach detection
        self.goal_was_centered = False
        self.goal_center_tolerance = 100 # pixels from center for goal centering
        
        self.last_collector_mode = None

    def set_ball_collector(self, mode):
        if mode != self.last_collector_mode:
            self.robot.set_ball_collector(mode)
            self.last_collector_mode = mode
        
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
        self.set_ball_collector("stop")

    def update(self, frame):
        """
        Main game loop update.
        Args:
            frame: opencv image frame from camera
        """
        if frame is None:
            return
            
        self.frame_width = frame.shape[1]
        self.frame_height = frame.shape[0]
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
            self.set_ball_collector("forward") # Keep intake on just in case
            
            if len(balls) > 0:
                # Found a ball, target the largest/closest one
                closest_ball = max(balls, key=lambda b: b['area'])
                self.target_ball = closest_ball
                self.ball_was_centered = False # Reset the flag
                self.set_state("APPROACH_BALL")
            else:
                # "Try around more" - alternating search pattern
                search_time = current_time - self.state_start_time
                # Cycle: Spin for 4s, Drive for 1.5s
                cycle_time = search_time % 5.5
                
                if cycle_time < 4.0:
                    self.robot.send_velocity_command(0, 0, self.search_rotation_speed)
                else:
                    # Drive forward with slight turn to explore new areas
                    self.robot.send_velocity_command(self.approach_speed, 0, 0.5)

        elif self.state == "APPROACH_BALL":
            if len(balls) == 0:
                # Check if ball disappeared from center - indicates collection
                if self.ball_was_centered:
                    print("Ball disappeared from bottom center - collected!")
                    self.balls_collected += 1
                    self.ball_was_centered = False
                    if self.balls_collected >= self.max_balls:
                        self.set_state("SEARCH_GOAL")
                    else:
                        self.set_state("SEARCH_BALL")
                else:
                    # Lost the ball without centering
                    self.set_state("SEARCH_BALL")
                return processed_frame

            # Update target (simple: pick largest again or track?)
            # Picking largest is safest for now
            closest_ball = max(balls, key=lambda b: b['area'])
            
            # Check if ball is in bottom region (entire width)
            ball_x = closest_ball['center'][0]
            ball_y = closest_ball['center'][1]
            if ball_y > self.frame_height * self.bottom_threshold:
                self.ball_was_centered = True
            
            # Control Logic
            # Steering: PD control on x-offset
            error_x = self.frame_center_x - ball_x
            omega = error_x * self.approach_kP
            
            # Speed: Constant forward
            # If ball is very close (large area), we might be collecting it
            if closest_ball['area'] > 32000: # Threshold for "close enough to suck"
                self.robot.send_velocity_command(self.approach_speed/2, 0, 0)
                self.set_state("COLLECTING")
            else:
                self.robot.send_velocity_command(self.approach_speed, 0, omega)
                self.set_ball_collector("forward")

        elif self.state == "COLLECTING":
            # Drive forward blindly for a bit to ensure intake
            self.robot.send_velocity_command(self.approach_speed, 0, 0)
            self.set_ball_collector("forward")
            
            # Wait for 4 seconds to ensure collection
            if (current_time - self.state_start_time) > 4.0:
                print("Collection timeout - assumed collected")
                self.balls_collected += 1
                self.ball_was_centered = False
                if self.balls_collected >= self.max_balls:
                    self.set_state("SEARCH_GOAL")
                else:
                    self.set_state("SEARCH_BALL")

        elif self.state == "SEARCH_GOAL":
            self.set_ball_collector("forward")
            
            if len(target_goal) > 0:
                self.goal_was_centered = False
                self.set_state("APPROACH_GOAL")
            else:
                self.robot.send_velocity_command(0, 0, self.search_rotation_speed)

        elif self.state == "APPROACH_GOAL":
            self.set_ball_collector("forward") # Keep holding balls
            
            if len(target_goal) == 0:
                self.set_state("SEARCH_GOAL")
                return processed_frame
                
            goal = max(target_goal, key=lambda g: g['area'])
            
            # Check if goal is centered
            goal_x = goal['center'][0]
            if abs(goal_x - self.frame_center_x) < self.goal_center_tolerance:
                self.goal_was_centered = True
            
            error_x = self.frame_center_x - goal_x
            omega = error_x * self.approach_kP
            
            # Deposit only if goal is centered AND almost fills the frame
            # Assuming 640x480 frame, full frame area ~= 307200, so 150000+ is almost full
            if self.goal_was_centered and goal['area'] > 100000:
                self.set_state("DEPOSITING")
            else:
                 self.robot.send_velocity_command(self.approach_speed, 0, omega)

        elif self.state == "DEPOSITING":
            # Reverse ball collector and drive backwards to push balls to the front roller
            self.set_ball_collector("reverse")
            self.robot.send_velocity_command(self.deposit_backup_speed, 0, 0)
            
            if (current_time - self.state_start_time) > self.deposit_time:
                self.balls_collected = 0
                self.set_state("LEAVE_GOAL")

        elif self.state == "LEAVE_GOAL":
            # Turn around to avoid seeing the deposited balls immediately
            self.set_ball_collector("forward")
            self.robot.send_velocity_command(0, 0, self.search_rotation_speed)

            # Turn for enough time to face away (~180 degrees)
            # Speed 2.0 rad/s -> ~3.14 rad needed -> ~1.6s
            if (current_time - self.state_start_time) > 1.6:
                self.set_state("SEARCH_BALL")

        return processed_frame

    def cleanup(self):
        self.robot.stop_movement()
        self.set_ball_collector("stop")
