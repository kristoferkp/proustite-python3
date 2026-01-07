import socket
import time
import struct
import sys

# Configuration
SERVER_IP = "proustite.local"  # REPLACE WITH RASPBERRY PI IP
SERVER_PORT = 5005
SEND_RATE = 20  # Hz

try:
    import pygame
except ImportError:
    print("Error: pygame is required. Install it with: pip install pygame")
    sys.exit(1)

def map_range(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def main():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No joystick found.")
        return

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Initialized Joystick: {joystick.get_name()}")
    print(f"Number of buttons: {joystick.get_numbuttons()}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"\n=== Proustite Robot Client ===")
    print(f"Sending commands to {SERVER_IP}:{SERVER_PORT}")
    print("\nControls:")
    print("  Left Stick Y:  Forward/Backward")
    print("  Left Stick X:  Strafe Left/Right")
    print("  Right Stick X: Rotate")
    print("  A Button:      Ball collector FORWARD")
    print("  B Button:      Ball collector STOP")
    print("  X Button:      Ball collector REVERSE")
    print("  Back/Select:   Reset heading")
    print("Press Ctrl+C to exit\n")

    # Ball collector state tracking
    collector_state = 'stop'
    last_collector_buttons = [False] * 3  # A, B, X

    try:
        clock = pygame.time.Clock()
        while True:
            pygame.event.pump()

            # Read axes
            # Left Stick X -> Vy (Strafe)
            axis_x = joystick.get_axis(0)
            # Left Stick Y -> Vx (Forward/Back) - Inverted usually
            axis_y = -joystick.get_axis(1) 
            # Right Stick X -> Omega (Rotation)
            axis_rot = joystick.get_axis(2)

            # Deadzone
            deadzone = 0.1
            if abs(axis_x) < deadzone: axis_x = 0
            if abs(axis_y) < deadzone: axis_y = 0
            if abs(axis_rot) < deadzone: axis_rot = 0

            # Scale to max velocity (m/s) and rotation (rad/s)
            MAX_VEL = 1.0 # m/s
            MAX_ROT = 3.0 # rad/s

            vx = axis_y * MAX_VEL
            vy = -axis_x * MAX_VEL # Invert X for correct strafe direction if needed
            omega = -axis_rot * MAX_ROT

            # Create and send velocity packet
            message = f"VEL,{vx:.3f},{vy:.3f},{omega:.3f}"
            sock.sendto(message.encode(), (SERVER_IP, SERVER_PORT))
            
            # Ball collector control buttons
            # Button mapping (Xbox controller):
            # 0 = A, 1 = B, 2 = X, 3 = Y
            # 6 = Back/Select
            button_a = joystick.get_button(0)  # Forward
            button_b = joystick.get_button(1)  # Stop
            button_x = joystick.get_button(2)  # Reverse
            
            # Detect button presses (rising edge)
            current_buttons = [button_a, button_b, button_x]
            
            if button_a and not last_collector_buttons[0]:
                # A pressed - Forward
                collector_state = 'forward'
                sock.sendto(b"COLLECTOR,forward", (SERVER_IP, SERVER_PORT))
                print("Ball collector: FORWARD")
            
            elif button_b and not last_collector_buttons[1]:
                # B pressed - Stop
                collector_state = 'stop'
                sock.sendto(b"COLLECTOR,stop", (SERVER_IP, SERVER_PORT))
                print("Ball collector: STOP")
            
            elif button_x and not last_collector_buttons[2]:
                # X pressed - Reverse
                collector_state = 'reverse'
                sock.sendto(b"COLLECTOR,reverse", (SERVER_IP, SERVER_PORT))
                print("Ball collector: REVERSE")
            
            last_collector_buttons = current_buttons
            
            # Reset heading button (Back/Select button)
            if joystick.get_numbuttons() > 6:
                if joystick.get_button(6):
                    sock.sendto(b"RESET_HEADING", (SERVER_IP, SERVER_PORT))
                    print("Reset heading to 0")
                    time.sleep(0.2)  # Debounce

            clock.tick(SEND_RATE)

    except KeyboardInterrupt:
        print("\nExiting...")
        # Send stop commands
        sock.sendto(b"STOP", (SERVER_IP, SERVER_PORT))
        sock.sendto(b"COLLECTOR,stop", (SERVER_IP, SERVER_PORT))
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
