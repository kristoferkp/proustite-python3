# Robot Soccer Competition - Design Rules

## Field Specifications

### Dimensions
- **Playing area**: 3000 mm (length) × 2000 mm (width)
  - Bounded by white inner line + black outer line (50 mm total width)
  - Both lines belong to the playing area
- **Surrounding zone**: 4000 mm (length) × 3000 mm (width)
- **Walls**: Minimum 450 mm height, white color up to 450 mm

### Field Layout
- Divided into two halves by center line
- Goals positioned at center of short edges (700 mm gap, 200 mm height, 250 mm depth)
- Blue goal on one end, yellow goal on other end

### Field Markings
- Center line: divides field into two halves
- Goal areas: 100 mm line positioned in front of each goal
- Lines are 50 mm wide

## Game Structure

### Match Format
- Best-of-3 rounds (or best-of-2 in exceptional cases)
- Tiebreaker: Penalty round(s) (maximum 3 attempts each)
- Final tiebreaker: Empty field round (11 balls in 150 seconds)

### Round Duration
- **Regular round**: 150 seconds
- **Penalty round**: 60 seconds
- **Empty field round**: 150 seconds per robot

### Starting Position
- Both robots start in their respective right corners (when viewing from goal line)
- Starting position: intersection of outer black line (end) and side line
- Robots must be at rest before match start signal
- After start signal given by referee, teams must stop robot when signal ends
- Both teams have a side, yellow and blue, and must score into the opponents goal.

## Scoring Rules

### Goal Definition
- Ball must be 100% beyond black line in front of goal (top-down view)
- Goals scored by ball that was not "out of play" (out of bounds)

### Invalid Goals
1. Robot grabbed ball from out of bounds (100% outside black line) and scored
2. Robot grabbed ball from goal and scored in same goal

### Point Counting
- One point per ball completely in goal or passed through goal line
- Counted at end of round

## Game End Conditions

### Victory Conditions (in order)
1. Most round wins (best-of-3)
2. If tied in round wins: Penalty round winner (max 3 attempts)
3. If still tied: Most goals in regulation rounds
4. If still tied: Empty field round winner
5. Both teams can lose if neither scores in first two rounds

# Robot design
- The robot has a dribbler/ball collector in front. The collector has space for 5-6 balls.
- The robot has 3 omni wheels, with 120 degrees between them.
- The wheels are positioned 115mm from the center.
- The ball collector has a webcam attached.
- The ball collector also has a drone motor attached with a TPU roller to stop balls from escaping.
- The drone motor is controlled from the ESP32 and its attached ESC.
- The webcam is a Logitech C930e which has a 90 degree dFoV. The webcam sensor is 205mm off the ground, 165mm from the center of the robot, with a adjustable pitch.
- There are 3 controllers. A Nucleo G431KB to control the motors and their drivers, a ESP32 to connect to the MPU-6050 and BLHeli-S ESC, and the main computer is a Raspberry Pi 5 with the AI Kit installed (Hailo-8L).

# Game plan
- The robot needs to detect orange golf balls and collect as many as possible, while avoiding collecting balls from the goal or out of bounds.
- To collect the balls, the robot needs to start the drone motor and drive into the ball to suck the ball into the collector. 
- For the balls to stay in the collector, the drone motor needs to stay in the ball sucking mode.
- The robot then needs to drive to the opponents goal and start depositing the balls.
- To deposit the balls, the drone motor needs to reverse its direction and drive a bit backwards so the balls contact the TPU roller attached to the motor.
- When the robot has deposited the balls, it needs to go and find more balls and start the cycle over.
- We should also try and not hit the opponent.