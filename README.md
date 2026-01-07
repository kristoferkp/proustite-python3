# Proustite Python Control

This directory contains Python scripts for remote controlling the Proustite robot with **Layer 2 drift compensation**.

## 🆕 Layer 2 Controller

The new Layer 2 controller provides:
- **IMU-based drift compensation** - Automatically corrects rotational drift using ESP32 gyroscope data
- **Ball collector control** - Integrated control of the drone motor (forward/reverse/stop)
- **Closed-loop heading control** - Maintains robot orientation even without user input
- **Dual hardware integration** - Simultaneously manages Nucleo (movement) and ESP32 (IMU + collector)

See [LAYER2_README.md](LAYER2_README.md) for detailed documentation.

## Prerequisites

### On Laptop (Client)
- Python 3
- `pygame` library for Xbox controller input

```bash
pip install pygame
```

### On Raspberry Pi (Server)
- Python 3
- `pyserial` library for communicating with Nucleo and ESP32

```bash
pip install pyserial
```

## Hardware Architecture

```
Laptop (Client)          Raspberry Pi (Server)          Hardware
┌─────────────┐         ┌──────────────────┐          ┌─────────────┐
│ Xbox        │   UDP   │ Layer2Controller │  Serial  │ Nucleo      │
│ Controller  ├────────►│ - Drift comp     ├─────────►│ - Movement  │
│             │         │ - Ball collector │          │ - 3 Motors  │
│ client.py   │         │                  │  Serial  │             │
└─────────────┘         │ server.py        ├─────────►│ ESP32       │
                        └──────────────────┘          │ - MPU6050   │
                                                       │ - ESC       │
                                                       └─────────────┘
```

## Quick Start

### 1. Hardware Setup
- Connect Nucleo to Raspberry Pi via USB (typically `/dev/ttyACM0`)
- Connect ESP32 to Raspberry Pi via USB (typically `/dev/ttyUSB0`)
- Connect Xbox controller to laptop
- Ensure Raspberry Pi and laptop are on same network

### 2. Configure Serial Ports

Edit `server.py` and update:
```python
NUCLEO_PORT = "/dev/ttyACM0"  # Check with: ls /dev/tty*
ESP32_PORT = "/dev/ttyUSB0"   # Check with: ls /dev/tty*
```

Grant serial port permissions (first time only):
```bash
sudo usermod -a -G dialout $USER
# Log out and back in for permissions to take effect
```

### 3. Configure Network

Edit `client.py` and update:
```python
SERVER_IP = "proustite.local"  # or Raspberry Pi's IP address
```

Find Pi's IP: `hostname -I` on Raspberry Pi

### 4. Run Server (on Raspberry Pi)

```bash
cd proustite-python
python3 server.py
```

Expected output:
```
=== Proustite Robot Server - Layer 2 Controller ===
✓ Connected to Nucleo on /dev/ttyACM0
✓ Connected to ESP32 on /dev/ttyUSB0
✓ Listening on UDP 0.0.0.0:5005
✓ Control loop running at 50 Hz

=== Server Ready ===
Waiting for commands...
```

### 5. Run Client (on Laptop)

```bash
cd proustite-python
python3 client.py
```

## Controls (Xbox Controller)

### Movement
- **Left Stick Y:** Forward / Backward (vx)
- **Left Stick X:** Strafe Left / Right (vy)
- **Right Stick X:** Rotate Left / Right (omega)

### Ball Collector
- **A Button:** Ball collector FORWARD
- **B Button:** Ball collector STOP
- **X Button:** Ball collector REVERSE

### Special Functions
- **Back/Select Button:** Reset heading to 0°

## Features

### Drift Compensation

The Layer 2 controller continuously monitors the robot's heading using the MPU6050 IMU on the ESP32. When you stop rotating the robot:

1. Current heading is "locked" as the target
2. Controller monitors for any drift (unwanted rotation)
3. Automatically applies correction to maintain heading
4. User doesn't feel any resistance - correction is transparent

**Result:** Robot maintains its orientation without constant joystick input!

### Ball Collector Control

The drone motor (BLHeli_S ESC) on the ESP32 is controlled via button presses:
- **Forward:** Collect balls into robot
- **Reverse:** Eject balls from robot  
- **Stop:** Turn off motor

Commands are sent directly to ESP32 via the serial interface.

## File Structure

```
proustite-python/
├── client.py              # Laptop client (joystick control)
├── server.py              # Raspberry Pi server (main entry point)
├── robot_interface.py     # Hardware communication layer
├── layer2_controller.py   # Drift compensation controller
├── test_layer2.py         # Test suite
├── README.md              # This file
└── LAYER2_README.md       # Detailed Layer 2 documentation
```

## Troubleshooting

### "Failed to connect to Nucleo/ESP32"
- Check USB connections
- Verify serial port names: `ls /dev/tty*`
- Check permissions: `sudo usermod -a -G dialout $USER`

### "No joystick found"
- Connect Xbox controller to laptop
- Install pygame: `pip install pygame`

### Drift compensation not working
- Send STATUS command to view IMU data
- Check that gyro_z values are updating
- Try increasing drift_gain in server.py

### Robot not moving
- Check Nucleo firmware is uploaded
- Verify VEL commands reach Nucleo

## Documentation

See [LAYER2_README.md](LAYER2_README.md) for complete documentation.
