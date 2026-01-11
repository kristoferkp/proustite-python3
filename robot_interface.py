"""
Robot Interface - Layer 2 Controller
Handles communication with:
- Nucleo (movement control via serial)
- ESP32 (IMU data + drone motor via serial)
"""

import serial
import time
import threading
import re
from collections import deque
import math


class RobotInterface:
    """Interface to communicate with Nucleo and ESP32."""
    
    def __init__(self, nucleo_port="/dev/ttyACM0", esp32_port="/dev/ttyUSB0", 
                 nucleo_baud=115200, esp32_baud=115200):
        """
        Initialize connections to both microcontrollers.
        
        Args:
            nucleo_port: Serial port for Nucleo (movement)
            esp32_port: Serial port for ESP32 (IMU + drone motor)
            nucleo_baud: Baud rate for Nucleo
            esp32_baud: Baud rate for ESP32
        """
        self.nucleo_port = nucleo_port
        self.esp32_port = esp32_port
        
        # Serial connections
        self.nucleo_serial = None
        self.esp32_serial = None
        
        # IMU data storage
        self.imu_lock = threading.Lock()
        self.latest_imu = {
            'timestamp': 0,
            'accel_x': 0.0, 'accel_y': 0.0, 'accel_z': 0.0,
            'gyro_x': 0.0, 'gyro_y': 0.0, 'gyro_z': 0.0,
            'temp_c': 0.0
        }
        
        # Heading tracking (integrated from gyro_z)
        self.heading = 0.0  # Current heading in radians
        self.last_heading_update = time.time()
        
        # Drift compensation parameters
        self.drift_history = deque(maxlen=10)  # Store recent gyro_z readings
        
        # ESP32 reader thread
        self.esp32_running = False
        self.esp32_thread = None
        
        # Initialize connections
        self._connect_nucleo(nucleo_baud)
        self._connect_esp32(esp32_baud)
        
    def _connect_nucleo(self, baud):
        """Connect to Nucleo board."""
        try:
            self.nucleo_serial = serial.Serial(self.nucleo_port, baud, timeout=1)
            time.sleep(2)  # Wait for connection to stabilize
            print(f"✓ Connected to Nucleo on {self.nucleo_port}")
        except serial.SerialException as e:
            print(f"✗ Failed to connect to Nucleo: {e}")
            raise
    
    def _connect_esp32(self, baud):
        """Connect to ESP32 and start reading thread."""
        try:
            self.esp32_serial = serial.Serial(self.esp32_port, baud, timeout=1)
            time.sleep(2)  # Wait for connection to stabilize
            print(f"✓ Connected to ESP32 on {self.esp32_port}")
            
            # Start reading thread
            self.esp32_running = True
            self.esp32_thread = threading.Thread(target=self._esp32_reader_thread, daemon=True)
            self.esp32_thread.start()
            
        except serial.SerialException as e:
            print(f"✗ Failed to connect to ESP32: {e}")
            raise
    
    def _esp32_reader_thread(self):
        """Background thread to continuously read IMU data from ESP32."""
        buffer = ""
        current_reading = {}
        
        while self.esp32_running:
            try:
                if self.esp32_serial and self.esp32_serial.in_waiting > 0:
                    line = self.esp32_serial.readline().decode('utf-8', errors='ignore').strip()
                    
                    if not line:
                        continue
                    
                    # Parse IMU data format from sketch_oct31a.ino
                    # Expected format:
                    # time: 12345 ms
                    # accel_x: 0.123, accel_y: 0.456, accel_z: 9.810
                    # gyro_x: 0.001, gyro_y: 0.002, gyro_z: 0.003
                    # temp_c: 25.50
                    # ---
                    
                    if line.startswith("time:"):
                        # Start of new reading
                        match = re.search(r'time:\s*(\d+)\s*ms', line)
                        if match:
                            current_reading['timestamp'] = int(match.group(1))
                    
                    elif line.startswith("accel_x:"):
                        # Parse accelerometer data
                        match = re.search(r'accel_x:\s*([-\d.]+),\s*accel_y:\s*([-\d.]+),\s*accel_z:\s*([-\d.]+)', line)
                        if match:
                            current_reading['accel_x'] = float(match.group(1))
                            current_reading['accel_y'] = float(match.group(2))
                            current_reading['accel_z'] = float(match.group(3))
                    
                    elif line.startswith("gyro_x:"):
                        # Parse gyroscope data
                        match = re.search(r'gyro_x:\s*([-\d.]+),\s*gyro_y:\s*([-\d.]+),\s*gyro_z:\s*([-\d.]+)', line)
                        if match:
                            current_reading['gyro_x'] = float(match.group(1))
                            current_reading['gyro_y'] = float(match.group(2))
                            current_reading['gyro_z'] = float(match.group(3))
                    
                    elif line.startswith("temp_c:"):
                        # Parse temperature
                        match = re.search(r'temp_c:\s*([-\d.]+)', line)
                        if match:
                            current_reading['temp_c'] = float(match.group(1))
                    
                    elif line == "---":
                        # End of reading - update latest IMU data
                        if len(current_reading) >= 7:  # Ensure we have all fields
                            with self.imu_lock:
                                self.latest_imu = current_reading.copy()
                                # Update heading
                                self._update_heading()
                        current_reading = {}
                
            except Exception as e:
                print(f"Error reading ESP32: {e}")
                time.sleep(0.1)
            
            time.sleep(0.001)  # Small delay to prevent CPU thrashing
    
    def _update_heading(self):
        """Update heading based on gyro_z integration."""
        current_time = time.time()
        dt = current_time - self.last_heading_update
        
        # Integrate gyro_z to get heading
        gyro_z = self.latest_imu['gyro_z']
        self.heading += gyro_z * dt
        
        # Keep heading in range [-pi, pi]
        self.heading = math.atan2(math.sin(self.heading), math.cos(self.heading))
        
        # Store for drift detection
        self.drift_history.append(gyro_z)
        
        self.last_heading_update = current_time
    
    def get_imu_data(self):
        """
        Get latest IMU data.
        
        Returns:
            dict: Latest IMU readings with keys:
                  timestamp, accel_x, accel_y, accel_z,
                  gyro_x, gyro_y, gyro_z, temp_c
        """
        with self.imu_lock:
            return self.latest_imu.copy()
    
    def get_heading(self):
        """
        Get current heading in radians.
        
        Returns:
            float: Current heading in radians [-pi, pi]
        """
        with self.imu_lock:
            return self.heading
    
    def get_drift_rate(self):
        """
        Get current rotational drift rate (rad/s).
        
        Returns:
            float: Average gyro_z over recent readings
        """
        if len(self.drift_history) == 0:
            return 0.0
        return sum(self.drift_history) / len(self.drift_history)
    
    def reset_heading(self):
        """Reset heading to zero."""
        with self.imu_lock:
            self.heading = 0.0
            self.drift_history.clear()
    
    def send_velocity_command(self, vx, vy, omega):
        """
        Send velocity command to Nucleo.
        
        Args:
            vx (float): Forward velocity in m/s
            vy (float): Strafe velocity in m/s
            omega (float): Rotational velocity in rad/s
        """
        if self.nucleo_serial:
            command = f"VEL,{vx:.3f},{vy:.3f},{omega:.3f}\n"
            try:
                self.nucleo_serial.write(command.encode())
            except Exception as e:
                print(f"Error sending velocity command: {e}")
    
    def stop_movement(self):
        """Stop all movement by sending STOP command to Nucleo."""
        if self.nucleo_serial:
            try:
                self.nucleo_serial.write(b"STOP\n")
            except Exception as e:
                print(f"Error sending stop command: {e}")
    
    def set_ball_collector(self, mode):
        """
        Control the ball collector motor (drone motor on ESP32).
        
        Args:
            mode (str): 'forward', 'reverse', or 'stop'
        """
        if self.esp32_serial:
            command_map = {
                'forward': 'R',
                'reverse': 'F',
                'stop': 'S'
            }
            
            cmd = command_map.get(mode.lower())
            if cmd:
                try:
                    self.esp32_serial.write((cmd + '\n').encode())
                    self.esp32_serial.flush()
                except Exception as e:
                    print(f"Error sending ball collector command: {e}")
            else:
                print(f"Invalid ball collector mode: {mode}")
    
    def close(self):
        """Close all serial connections."""
        print("Closing RobotInterface...")
        
        # Stop balls collector first
        self.set_ball_collector('stop')
        time.sleep(0.2)
        
        # Stop ESP32 reading thread
        self.esp32_running = False
        if self.esp32_thread:
            self.esp32_thread.join(timeout=2)
        
        # Close serial ports
        if self.nucleo_serial:
            try:
                self.nucleo_serial.write(b"STOP\n")
                self.nucleo_serial.flush()
                self.nucleo_serial.close()
                print("✓ Closed Nucleo connection")
            except Exception as e:
                print(f"Error closing Nucleo: {e}")
        
        if self.esp32_serial:
            try:
                self.esp32_serial.write(b'S\n')  # Stop ball collector (redundant safety)
                self.esp32_serial.flush()
                self.esp32_serial.close()
                print("✓ Closed ESP32 connection")
            except Exception as e:
                print(f"Error closing ESP32: {e}")
