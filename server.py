import socket
import time
import sys
import threading
from robot_interface import RobotInterface
from layer2_controller import Layer2Controller

# Configuration
UDP_IP = "0.0.0.0"
UDP_PORT = 5005

# Serial port configuration
NUCLEO_PORT = "/dev/ttyACM0"  # Adjust if needed
ESP32_PORT = "/dev/ttyUSB0"   # Adjust if needed (may be /dev/ttyUSB1, etc.)
BAUD_RATE = 115200

# Control loop rate
CONTROL_RATE = 50  # Hz (20ms update period)

def main():
    print("=== Proustite Robot Server - Layer 2 Controller ===")
    
    # Initialize Robot Interface
    try:
        robot = RobotInterface(
            nucleo_port=NUCLEO_PORT,
            esp32_port=ESP32_PORT,
            nucleo_baud=BAUD_RATE,
            esp32_baud=BAUD_RATE
        )
    except Exception as e:
        print(f"Failed to initialize robot interface: {e}")
        print("\nTroubleshooting:")
        print("1. Check that both Nucleo and ESP32 are connected")
        print("2. Verify serial port names (ls /dev/tty* to list)")
        print("3. Ensure you have permissions (sudo usermod -a -G dialout $USER)")
        sys.exit(1)
    
    # Initialize Layer 2 Controller
    controller = Layer2Controller(robot, drift_gain=2.0)
    
    # Initialize UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(0.1)  # Non-blocking with timeout
    print(f"✓ Listening on UDP {UDP_IP}:{UDP_PORT}")
    
    # Control loop thread
    running = True
    
    def control_loop():
        """Background thread that runs the Layer 2 controller at fixed rate."""
        dt = 1.0 / CONTROL_RATE
        while running:
            start_time = time.time()
            
            # Update controller (calculates and sends compensated commands)
            controller.update()
            
            # Maintain fixed rate
            elapsed = time.time() - start_time
            if elapsed < dt:
                time.sleep(dt - elapsed)
    
    # Start control loop thread
    control_thread = threading.Thread(target=control_loop, daemon=True)
    control_thread.start()
    print(f"✓ Control loop running at {CONTROL_RATE} Hz")
    
    print("\n=== Server Ready ===")
    print("Waiting for commands...")
    print("  VEL,vx,vy,omega    - Set velocity")
    print("  STOP               - Emergency stop")
    print("  COLLECTOR,mode     - Ball collector (forward/reverse/stop)")
    print("  RESET_HEADING      - Reset heading to 0")
    print("  STATUS             - Print status")
    print("Press Ctrl+C to exit\n")

    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                command = data.decode().strip()
                
                # Parse command
                if command.startswith("VEL,"):
                    # Parse: VEL,vx,vy,omega
                    parts = command.split(',')
                    if len(parts) == 4:
                        try:
                            vx = float(parts[1])
                            vy = float(parts[2])
                            omega = float(parts[3])
                            controller.set_velocity(vx, vy, omega)
                        except ValueError:
                            print(f"Invalid velocity values: {command}")
                    else:
                        print(f"Invalid VEL command format: {command}")
                
                elif command == "STOP":
                    controller.stop()
                
                elif command.startswith("COLLECTOR,"):
                    # Parse: COLLECTOR,forward/reverse/stop
                    parts = command.split(',')
                    if len(parts) == 2:
                        mode = parts[1].lower()
                        if mode in ['forward', 'reverse', 'stop']:
                            controller.set_ball_collector(mode)
                        else:
                            print(f"Invalid collector mode: {mode}")
                    else:
                        print(f"Invalid COLLECTOR command format: {command}")
                
                elif command == "RESET_HEADING":
                    controller.reset_heading()
                
                elif command == "STATUS":
                    controller.print_status()
                
                else:
                    print(f"Unknown command: {command}")
            
            except socket.timeout:
                # No data received, continue
                pass

    except KeyboardInterrupt:
        print("\n\nShutting down...")
        running = False
        controller.stop()
    finally:
        # Clean up
        robot.close()
        sock.close()
        print("Server stopped")

if __name__ == "__main__":
    main()
