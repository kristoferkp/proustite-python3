import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Scale factor to fit on screen (pixels per mm)
# Adjust this to make the window larger or smaller
SCALE = 0.25  # 0.25 pixels per mm gives 750x1000 pixel window

# Real-world dimensions in mm
TOTAL_WIDTH_MM = 3000
TOTAL_HEIGHT_MM = 4000
FIELD_WIDTH_MM = 2000
FIELD_HEIGHT_MM = 3000
BLACK_BORDER_MM = 50
WHITE_BORDER_MM = 50
GOAL_WIDTH_MM = 250
GOAL_HEIGHT_MM = 700
DEAD_ZONE_MM = 50  # Minimum distance from borders
START_ZONE_SIZE_MM = 350  # Robot starting zones in corners
ROBOT_DIAMETER_MM = 350

# Robot movement settings
ROBOT_SPEED_MS = 0.5  # meters per second
ROTATION_SPEED_RAD_S = 1.5  # radians per second
FPS = 60  # frames per second

# Convert movement speed to pixels per frame
MOVEMENT_SPEED = (ROBOT_SPEED_MS * 1000 * SCALE) / FPS  # m/s -> mm/s -> px/s -> px/frame
ROTATION_SPEED = ROTATION_SPEED_RAD_S / FPS  # rad/s -> rad/frame

# Calculate border around field
OUTER_BORDER_MM = (TOTAL_WIDTH_MM - FIELD_WIDTH_MM) / 2  # 500mm on each side

# Calculate pixel dimensions
TOTAL_WIDTH_PX = int(TOTAL_WIDTH_MM * SCALE)
TOTAL_HEIGHT_PX = int(TOTAL_HEIGHT_MM * SCALE)
FIELD_WIDTH_PX = int(FIELD_WIDTH_MM * SCALE)
FIELD_HEIGHT_PX = int(FIELD_HEIGHT_MM * SCALE)
BLACK_BORDER_PX = int(BLACK_BORDER_MM * SCALE)
WHITE_BORDER_PX = int(WHITE_BORDER_MM * SCALE)
OUTER_BORDER_PX = int(OUTER_BORDER_MM * SCALE)
GOAL_WIDTH_PX = int(GOAL_WIDTH_MM * SCALE)
GOAL_HEIGHT_PX = int(GOAL_HEIGHT_MM * SCALE)
DEAD_ZONE_PX = int(DEAD_ZONE_MM * SCALE)
START_ZONE_SIZE_PX = int(START_ZONE_SIZE_MM * SCALE)
ROBOT_RADIUS_PX = int((ROBOT_DIAMETER_MM / 2) * SCALE)

# Colors
GREEN = (0, 128, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)
RED = (255, 0, 0)

# Create the display window
screen = pygame.display.set_mode((TOTAL_WIDTH_PX, TOTAL_HEIGHT_PX))
pygame.display.set_caption(f"Field Visualization - {TOTAL_WIDTH_MM}mm x {TOTAL_HEIGHT_MM}mm")

# Field position
field_x = OUTER_BORDER_PX
field_y = OUTER_BORDER_PX

# Main loop
running = True
clock = pygame.time.Clock()

# Goal color configuration (True = yellow on top, False = yellow on bottom)
yellow_on_top = True

# Robot state (position in playable area and heading in radians)
import math
playable_x = field_x + BLACK_BORDER_PX + WHITE_BORDER_PX
playable_y = field_y + BLACK_BORDER_PX + WHITE_BORDER_PX
playable_width = FIELD_WIDTH_PX - 2 * (BLACK_BORDER_PX + WHITE_BORDER_PX)
playable_height = FIELD_HEIGHT_PX - 2 * (BLACK_BORDER_PX + WHITE_BORDER_PX)

# Robot starts in bottom-right corner, facing north
robot_x = playable_width - START_ZONE_SIZE_PX / 2
robot_y = playable_height - START_ZONE_SIZE_PX / 2
robot_heading = -math.pi / 2  # -90 degrees = north (up)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                yellow_on_top = not yellow_on_top
    
    # Handle continuous keyboard input for robot movement
    keys = pygame.key.get_pressed()
    
    # Rotation: Q/E keys
    if keys[pygame.K_q]:
        robot_heading -= ROTATION_SPEED
    if keys[pygame.K_e]:
        robot_heading += ROTATION_SPEED
    
    # Omni-directional movement: WASD keys
    if keys[pygame.K_w]:
        # Move forward in heading direction
        new_x = robot_x + math.cos(robot_heading) * MOVEMENT_SPEED
        new_y = robot_y + math.sin(robot_heading) * MOVEMENT_SPEED
        # Keep robot within playable area
        if ROBOT_RADIUS_PX <= new_x <= playable_width - ROBOT_RADIUS_PX:
            robot_x = new_x
        if ROBOT_RADIUS_PX <= new_y <= playable_height - ROBOT_RADIUS_PX:
            robot_y = new_y
    
    if keys[pygame.K_s]:
        # Move backward
        new_x = robot_x - math.cos(robot_heading) * MOVEMENT_SPEED
        new_y = robot_y - math.sin(robot_heading) * MOVEMENT_SPEED
        # Keep robot within playable area
        if ROBOT_RADIUS_PX <= new_x <= playable_width - ROBOT_RADIUS_PX:
            robot_x = new_x
        if ROBOT_RADIUS_PX <= new_y <= playable_height - ROBOT_RADIUS_PX:
            robot_y = new_y
    
    if keys[pygame.K_a]:
        # Strafe left
        strafe_angle = robot_heading - math.pi / 2
        new_x = robot_x + math.cos(strafe_angle) * MOVEMENT_SPEED
        new_y = robot_y + math.sin(strafe_angle) * MOVEMENT_SPEED
        if ROBOT_RADIUS_PX <= new_x <= playable_width - ROBOT_RADIUS_PX:
            robot_x = new_x
        if ROBOT_RADIUS_PX <= new_y <= playable_height - ROBOT_RADIUS_PX:
            robot_y = new_y
    
    if keys[pygame.K_d]:
        # Strafe right
        strafe_angle = robot_heading + math.pi / 2
        new_x = robot_x + math.cos(strafe_angle) * MOVEMENT_SPEED
        new_y = robot_y + math.sin(strafe_angle) * MOVEMENT_SPEED
        if ROBOT_RADIUS_PX <= new_x <= playable_width - ROBOT_RADIUS_PX:
            robot_x = new_x
        if ROBOT_RADIUS_PX <= new_y <= playable_height - ROBOT_RADIUS_PX:
            robot_y = new_y
    
    # Arrow keys for rotation
    if keys[pygame.K_LEFT]:
        robot_heading -= ROTATION_SPEED
    if keys[pygame.K_RIGHT]:
        robot_heading += ROTATION_SPEED
    
    # Draw the field layers
    # 1. Fill entire background with green (outer border)
    screen.fill(GREEN)
    
    # 2. Draw green field (centered with border around it)
    pygame.draw.rect(screen, GREEN, 
                     (field_x, field_y, FIELD_WIDTH_PX, FIELD_HEIGHT_PX))
    
    # 3. Draw black border (inset from green field edge)
    pygame.draw.rect(screen, BLACK, 
                     (field_x, field_y, FIELD_WIDTH_PX, FIELD_HEIGHT_PX), 
                     BLACK_BORDER_PX)
    
    # 4. Draw white border (inside the black border)
    white_rect = pygame.Rect(
        field_x + BLACK_BORDER_PX,
        field_y + BLACK_BORDER_PX,
        FIELD_WIDTH_PX - 2 * BLACK_BORDER_PX,
        FIELD_HEIGHT_PX - 2 * BLACK_BORDER_PX
    )
    pygame.draw.rect(screen, WHITE, white_rect, WHITE_BORDER_PX)
    
    # 5. Draw horizontal center line (50mm thick)
    line_thickness_px = int(50 * SCALE)
    center_y = field_y + FIELD_HEIGHT_PX // 2
    line_rect = pygame.Rect(
        field_x + BLACK_BORDER_PX + WHITE_BORDER_PX,
        center_y - line_thickness_px // 2,
        FIELD_WIDTH_PX - 2 * (BLACK_BORDER_PX + WHITE_BORDER_PX),
        line_thickness_px
    )
    pygame.draw.rect(screen, WHITE, line_rect)
    
    # 6. Draw goals outside playable field, touching the black border
    # Calculate horizontal center position for goals
    goal_x = field_x + (FIELD_WIDTH_PX - GOAL_HEIGHT_PX) // 2  # GOAL_HEIGHT is now width
    
    # Top goal (touching the top edge of the black border)
    top_goal_y = field_y - GOAL_WIDTH_PX
    top_goal_color = YELLOW if yellow_on_top else BLUE
    pygame.draw.rect(screen, top_goal_color,
                     (goal_x, top_goal_y, GOAL_HEIGHT_PX, GOAL_WIDTH_PX))
    
    # Bottom goal (touching the bottom edge of the black border)
    bottom_goal_y = field_y + FIELD_HEIGHT_PX
    bottom_goal_color = BLUE if yellow_on_top else YELLOW
    pygame.draw.rect(screen, bottom_goal_color,
                     (goal_x, bottom_goal_y, GOAL_HEIGHT_PX, GOAL_WIDTH_PX))
    
    # 7. Draw robot
    robot_screen_x = playable_x + robot_x
    robot_screen_y = playable_y + robot_y
    pygame.draw.circle(screen, RED, (int(robot_screen_x), int(robot_screen_y)), ROBOT_RADIUS_PX)
    
    # Draw heading vector
    heading_length = ROBOT_RADIUS_PX * 1.5
    heading_end_x = robot_screen_x + math.cos(robot_heading) * heading_length
    heading_end_y = robot_screen_y + math.sin(robot_heading) * heading_length
    pygame.draw.line(screen, WHITE, 
                    (int(robot_screen_x), int(robot_screen_y)),
                    (int(heading_end_x), int(heading_end_y)), 3)
    
    # Update the display
    pygame.display.flip()
    clock.tick(60)

# Quit
pygame.quit()
sys.exit()
