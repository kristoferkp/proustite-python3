"""
Layer 2 Controller - Drift Compensation and Motion Control
Provides closed-loop control using IMU feedback to compensate for drift
"""

import time
import math


class Layer2Controller:
    """
    Layer 2 controller that compensates for drift using IMU feedback.
    
    Architecture:
    - Receives desired velocity commands (from joystick/client)
    - Reads IMU data to detect actual rotation
    - Compensates for drift by adjusting omega command
    - Sends corrected commands to Nucleo via RobotInterface
    """
    
    def __init__(self, robot_interface, drift_gain=1.0):
        """
        Initialize Layer 2 controller.
        
        Args:
            robot_interface: RobotInterface instance
            drift_gain: Proportional gain for drift compensation (default: 1.0)
        """
        self.robot = robot_interface
        self.drift_gain = drift_gain
        
        # Desired velocities (set by user/joystick)
        self.desired_vx = 0.0
        self.desired_vy = 0.0
        self.desired_omega = 0.0
        
        # Target heading (when rotating)
        self.target_heading = None
        self.heading_tolerance = 0.05  # radians (~3 degrees)
        
        # Control mode
        self.drift_compensation_enabled = True
        
        # Ball collector state
        self.ball_collector_mode = 'stop'
        
        # Watchdog
        self.last_command_time = time.time()
        self.command_timeout = 1.0  # seconds
        
        print("Layer 2 Controller initialized")
        print(f"  Drift compensation gain: {drift_gain}")
    
    def set_velocity(self, vx, vy, omega):
        """
        Set desired velocity.
        
        Args:
            vx (float): Forward velocity in m/s
            vy (float): Strafe velocity in m/s
            omega (float): Rotational velocity in rad/s
        """
        self.desired_vx = vx
        self.desired_vy = vy
        self.desired_omega = omega
        self.last_command_time = time.time()
        
        # If user is commanding rotation, update target heading
        if abs(omega) > 0.01:
            # User is actively rotating, track current heading as target
            self.target_heading = None
        elif self.target_heading is None:
            # Just stopped rotating, lock current heading
            self.target_heading = self.robot.get_heading()
    
    def set_ball_collector(self, mode):
        """
        Set ball collector motor mode.
        
        Args:
            mode (str): 'forward', 'reverse', or 'stop'
        """
        if mode != self.ball_collector_mode:
            self.ball_collector_mode = mode
            self.robot.set_ball_collector(mode)
            print(f"Ball collector: {mode}")
    
    def enable_drift_compensation(self, enabled=True):
        """Enable or disable drift compensation."""
        self.drift_compensation_enabled = enabled
        if enabled:
            print("Drift compensation: ENABLED")
        else:
            print("Drift compensation: DISABLED")
    
    def reset_heading(self):
        """Reset heading to zero."""
        self.robot.reset_heading()
        self.target_heading = 0.0
        print("Heading reset to 0")
    
    def update(self):
        """
        Main control loop update - call this regularly (e.g., 20-50 Hz).
        Calculates compensated velocity commands and sends to robot.
        """
        # Check watchdog
        if time.time() - self.last_command_time > self.command_timeout:
            # No recent commands, stop robot
            self.robot.stop_movement()
            return
        
        # Get IMU data
        imu_data = self.robot.get_imu_data()
        current_heading = self.robot.get_heading()
        drift_rate = self.robot.get_drift_rate()
        
        # Start with desired velocities
        cmd_vx = self.desired_vx
        cmd_vy = self.desired_vy
        cmd_omega = self.desired_omega
        
        # Apply drift compensation if enabled
        if self.drift_compensation_enabled:
            # If not actively rotating, compensate for drift
            if abs(self.desired_omega) < 0.01:
                # No commanded rotation - maintain heading
                if self.target_heading is not None:
                    # Calculate heading error
                    heading_error = self._normalize_angle(self.target_heading - current_heading)
                    
                    # Proportional control to correct heading
                    # Add feedforward term to cancel measured drift
                    omega_correction = self.drift_gain * heading_error - drift_rate
                    
                    # Limit correction magnitude
                    max_correction = 1.0  # rad/s
                    omega_correction = max(-max_correction, min(max_correction, omega_correction))
                    
                    cmd_omega += omega_correction
        
        # Send compensated command to robot
        self.robot.send_velocity_command(cmd_vx, cmd_vy, cmd_omega)
    
    def _normalize_angle(self, angle):
        """Normalize angle to [-pi, pi] range."""
        return math.atan2(math.sin(angle), math.cos(angle))
    
    def stop(self):
        """Emergency stop - stop all movement and ball collector."""
        self.desired_vx = 0.0
        self.desired_vy = 0.0
        self.desired_omega = 0.0
        self.robot.stop_movement()
        self.robot.set_ball_collector('stop')
        print("EMERGENCY STOP")
    
    def get_status(self):
        """
        Get current controller status.
        
        Returns:
            dict: Status information
        """
        imu_data = self.robot.get_imu_data()
        current_heading = self.robot.get_heading()
        drift_rate = self.robot.get_drift_rate()
        
        return {
            'desired': {
                'vx': self.desired_vx,
                'vy': self.desired_vy,
                'omega': self.desired_omega
            },
            'heading': {
                'current': current_heading,
                'target': self.target_heading,
                'drift_rate': drift_rate
            },
            'imu': imu_data,
            'ball_collector': self.ball_collector_mode,
            'drift_compensation': self.drift_compensation_enabled
        }
    
    def print_status(self):
        """Print current status to console."""
        status = self.get_status()
        
        print("\n=== Layer 2 Controller Status ===")
        print(f"Desired: vx={status['desired']['vx']:.2f} m/s, "
              f"vy={status['desired']['vy']:.2f} m/s, "
              f"ω={status['desired']['omega']:.2f} rad/s")
        print(f"Heading: {math.degrees(status['heading']['current']):.1f}°")
        if status['heading']['target'] is not None:
            print(f"Target Heading: {math.degrees(status['heading']['target']):.1f}°")
        print(f"Drift Rate: {status['heading']['drift_rate']:.4f} rad/s")
        print(f"Ball Collector: {status['ball_collector'].upper()}")
        print(f"Drift Compensation: {'ON' if status['drift_compensation'] else 'OFF'}")
        print("=" * 35)


class DriftEstimator:
    """
    Optional advanced drift estimator using Kalman filter or complementary filter.
    Can be integrated for more sophisticated drift compensation.
    """
    
    def __init__(self, alpha=0.98):
        """
        Initialize drift estimator.
        
        Args:
            alpha: Complementary filter constant (0-1)
                   Higher values trust gyro more, lower values trust accel more
        """
        self.alpha = alpha
        self.estimated_drift = 0.0
        self.bias_estimate = 0.0
        
    def update(self, gyro_z, accel_x, accel_y, dt):
        """
        Update drift estimate using sensor fusion.
        
        Args:
            gyro_z: Gyroscope Z reading (rad/s)
            accel_x: Accelerometer X (m/s²)
            accel_y: Accelerometer Y (m/s²)
            dt: Time delta (seconds)
        
        Returns:
            float: Estimated drift rate (rad/s)
        """
        # Simple complementary filter
        # In steady state with no commanded rotation, any gyro reading is drift
        
        # Calculate acceleration magnitude
        accel_mag = math.sqrt(accel_x**2 + accel_y**2)
        
        # If acceleration is low (robot not moving much), update bias estimate
        if accel_mag < 0.5:  # Threshold for "steady state"
            # Low-pass filter on bias estimate
            self.bias_estimate = self.alpha * self.bias_estimate + (1 - self.alpha) * gyro_z
        
        self.estimated_drift = self.bias_estimate
        
        return self.estimated_drift
