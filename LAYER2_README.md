# Layer 2 Controller - Implementation Guide

## Overview

The Layer 2 controller provides closed-loop motion control with IMU-based drift compensation for the Proustite robot. It integrates data from both the ESP32 (IMU + ball collector motor) and Nucleo (omni-wheel drive) to maintain accurate positioning and heading.

## Architecture

```
┌──────────────┐       UDP Commands        ┌────────────────────┐
│   Client     │ ───────────────────────► │  Raspberry Pi      │
│  (Laptop)    │                           │  - server.py       │
│  - Joystick  │                           │  - Layer2Controller│
│  - client.py │                           │  - RobotInterface  │
└──────────────┘                           └─────────┬──────────┘
                                                     │
                        ┌────────────────────────────┴────────────────────┐
                        │                                                  │
                   Serial (USB)                                      Serial (USB)
                        │                                                  │
                ┌───────▼──────────┐                             ┌────────▼────────┐
                │  Nucleo Board    │                             │   ESP32 Board   │
                │  - OmniWheel     │                             │   - MPU6050 IMU │
                │    Drive         │                             │   - BLHeli ESC  │
                │  - 3 Motors      │                             │     (collector) │
                │  - PID Control   │                             └─────────────────┘
                └──────────────────┘
```

## Components

### 1. RobotInterface (`robot_interface.py`)

**Purpose:** Low-level interface to communicate with hardware.

**Features:**
- **Dual Serial Communication:**
  - Nucleo: Movement commands (VEL, STOP)
  - ESP32: IMU data reading + ball collector control
  
- **IMU Data Processing:**
  - Continuous background thread reads IMU data at ~100Hz
  - Parses accelerometer, gyroscope, and temperature
  - Integrates gyro_z to track heading
  - Maintains drift history for compensation
  
- **Ball Collector Control:**
  - Forward, Reverse, Stop commands to ESC
  - Non-blocking command interface

**Key Methods:**
```python
# Movement control
send_velocity_command(vx, vy, omega)
stop_movement()

# IMU data
get_imu_data()          # Latest IMU readings
get_heading()           # Integrated heading (rad)
get_drift_rate()        # Current drift rate (rad/s)
reset_heading()         # Reset heading to 0

# Ball collector
set_ball_collector(mode)  # 'forward', 'reverse', 'stop'
```

### 2. Layer2Controller (`layer2_controller.py`)

**Purpose:** High-level control logic with drift compensation.

**Features:**
- **Drift Compensation:**
  - Proportional feedback on heading error
  - Feedforward cancellation of measured drift
  - Only active when not manually rotating
  
- **Heading Lock:**
  - When user stops rotating, locks current heading
  - Automatically corrects any drift from target heading
  - Transparent to user - robot maintains orientation
  
- **Ball Collector Management:**
  - State tracking and command forwarding
  - Integrated with main control loop
  
- **Safety:**
  - Watchdog timer (1s timeout)
  - Emergency stop capability

**Control Algorithm:**
```
IF user_omega == 0:
    heading_error = target_heading - current_heading
    omega_correction = Kp * heading_error - drift_rate
    omega_command = desired_omega + omega_correction
ELSE:
    omega_command = desired_omega
    target_heading = None  # Free rotation

send_to_robot(vx, vy, omega_command)
```

**Key Methods:**
```python
set_velocity(vx, vy, omega)      # Set desired velocity
set_ball_collector(mode)         # Control ball collector
enable_drift_compensation(bool)  # Enable/disable compensation
reset_heading()                  # Reset heading to 0
update()                         # Main control loop (call at 20-50Hz)
get_status()                     # Get full status dict
```

### 3. Server (`server.py`)

**Purpose:** Runs on Raspberry Pi, bridges UDP commands to robot hardware.

**Features:**
- Initializes RobotInterface and Layer2Controller
- Receives UDP commands from client
- Runs control loop at 50Hz in background thread
- Command parsing and routing

**Supported Commands:**
```
VEL,vx,vy,omega       - Set velocity (m/s, m/s, rad/s)
STOP                  - Emergency stop
COLLECTOR,mode        - Ball collector (forward/reverse/stop)
RESET_HEADING         - Reset heading to 0
STATUS                - Print status to console
```

### 4. Client (`client.py`)

**Purpose:** Runs on laptop, translates joystick input to robot commands.

**Features:**
- Xbox controller support via pygame
- Ball collector button controls (A/B/X)
- Heading reset button (Back/Select)
- 20Hz command rate

**Controls:**
- **Left Stick Y:** Forward/Backward (vx)
- **Left Stick X:** Strafe Left/Right (vy)
- **Right Stick X:** Rotate (omega)
- **A Button:** Ball collector FORWARD
- **B Button:** Ball collector STOP
- **X Button:** Ball collector REVERSE
- **Back/Select:** Reset heading to 0

## Setup Instructions

### Hardware Connections

1. **Raspberry Pi:**
   - Nucleo: USB connection (typically `/dev/ttyACM0`)
   - ESP32: USB connection (typically `/dev/ttyUSB0`)

2. **Laptop:**
   - Xbox controller via USB or Bluetooth
   - Network connection to Raspberry Pi (same WiFi/LAN)

### Software Setup

#### On Raspberry Pi:

```bash
# Install dependencies
pip install pyserial

# Configure serial ports in server.py
NUCLEO_PORT = "/dev/ttyACM0"  # Check with: ls /dev/tty*
ESP32_PORT = "/dev/ttyUSB0"   # Check with: ls /dev/tty*

# Give user permission to access serial ports
sudo usermod -a -G dialout $USER
# Log out and back in for permissions to take effect

# Run server
python3 server.py
```

#### On Laptop:

```bash
# Install dependencies
pip install pygame

# Configure server IP in client.py
SERVER_IP = "proustite.local"  # or use Pi's IP address

# Run client
python3 client.py
```

## Tuning Parameters

### Drift Compensation Gain

Located in `server.py`:
```python
controller = Layer2Controller(robot, drift_gain=2.0)
```

- **Lower values (0.5-1.0):** Slower, smoother corrections
- **Higher values (2.0-5.0):** Faster, more aggressive corrections
- **Too high:** May cause oscillation or instability
- **Too low:** Won't fully correct drift

Recommended starting value: **2.0**

### Control Loop Rate

Located in `server.py`:
```python
CONTROL_RATE = 50  # Hz
```

- Recommended: 20-50 Hz
- Higher rates: More responsive, higher CPU usage
- Lower rates: Less responsive, may miss drift correction

### Max Velocity and Rotation

Located in `client.py`:
```python
MAX_VEL = 1.0  # m/s
MAX_ROT = 3.0  # rad/s
```

Adjust based on robot capabilities and desired responsiveness.

## Drift Compensation Details

### How It Works

1. **Heading Tracking:**
   - ESP32 continuously streams IMU data (100Hz)
   - Gyro Z-axis is integrated to track heading angle
   - Drift history maintained for feedforward compensation

2. **Target Heading:**
   - When user stops rotating (omega ≈ 0), current heading is "locked"
   - Controller maintains this target heading automatically

3. **Correction:**
   - **Feedback:** Proportional to heading error
   - **Feedforward:** Cancels measured drift rate
   - Combined correction added to omega command

4. **Manual Override:**
   - When user rotates joystick, drift compensation pauses
   - Allows free rotation without fighting controller
   - Target heading resets when rotation stops

### Mathematical Model

```
heading(t+dt) = heading(t) + gyro_z(t) * dt

heading_error = target_heading - current_heading

omega_correction = Kp * heading_error - drift_rate

omega_command = omega_desired + omega_correction
```

## Troubleshooting

### Serial Port Issues

```bash
# List all serial devices
ls /dev/tty*

# Check which device is which (look for VID/PID)
dmesg | grep tty

# Test serial connection
screen /dev/ttyACM0 115200
```

### IMU Not Reading

1. Check ESP32 serial output directly:
   ```bash
   screen /dev/ttyUSB0 115200
   ```
   You should see IMU data streaming.

2. Verify MPU6050 wiring (SDA=2, SCL=15 on ESP32)

3. Check ESP32 firmware is uploaded and running

### Drift Compensation Not Working

1. Print status to verify IMU data is updating:
   ```
   # Send from client or manually via UDP:
   echo "STATUS" | nc -u proustite.local 5005
   ```

2. Check drift_gain value (try increasing to 3-5)

3. Verify gyro_z readings are non-zero when stationary
   - If always zero, IMU may not be calibrated
   - Re-upload ESP32 firmware to recalibrate

### Robot Not Moving

1. Check Nucleo connection and firmware
2. Verify VEL commands are being sent:
   - Add debug print in server.py
3. Check motor PID tuning on Nucleo
4. Verify watchdog isn't triggering (should see commands within 1s)

## Advanced Features

### Custom Drift Estimator

The `DriftEstimator` class in `layer2_controller.py` provides a complementary filter for more sophisticated drift estimation. To use:

```python
from layer2_controller import DriftEstimator

estimator = DriftEstimator(alpha=0.98)

# In control loop:
imu = robot.get_imu_data()
drift = estimator.update(
    imu['gyro_z'], 
    imu['accel_x'], 
    imu['accel_y'], 
    dt
)
```

### Status Monitoring

Get real-time status:
```python
status = controller.get_status()
print(f"Heading: {math.degrees(status['heading']['current']):.1f}°")
print(f"Drift rate: {status['heading']['drift_rate']:.4f} rad/s")
```

## Future Enhancements

1. **Position Tracking:**
   - Double-integrate accelerometer for position estimation
   - Requires accounting for gravity and sensor noise
   - Consider sensor fusion with encoder odometry

2. **Adaptive Drift Compensation:**
   - Learn drift characteristics over time
   - Adjust gains based on surface conditions

3. **GUI Dashboard:**
   - Real-time visualization of heading, drift, velocities
   - Plots and logging for analysis

4. **Auto-Calibration:**
   - Automatic heading calibration on startup
   - Drift bias estimation during idle periods

## License

MIT License - See main repository for details.
