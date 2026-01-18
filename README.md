# Proustite Software

Hello! This is a repository of the many iterations of code for my DeltaX 2026 football robot.

This code runs on the Raspberry Pi. The Raspberry Pi is connected to a Logitech C930e webcam, a Nucleo G431KB and an ESP32/Arduino using USB.

The Nucleo and ESP32/Arduino connect using serial over USB, baud rate 115200.

# Autonomous mode
Start the program using ```python3 main.py --team [target colour]```

Consult ```main.py```for more options.

The program took a long time to start up, so maybe make the start command a key press and not the starting of the python code as the init of the serial devices took like 5 seconds.

Also it didn't help that the ESP32 had a broken connector and half the time didn't start up.

The ```layer2_controller.py``` uses the IMU data from the ESP32/Arduino to compensate for drift in the robots motion. The motors are worn and some wheels spun longer than others.

The game logic and the robot state machine is inside ```game_logic.py```. 

I had trouble updating the code while at the competition site as there was a lot of radio interference and my phone hotspot wasn't powerful enough.

**If you can, please try to take a portable WAP with you, or try to connect to the Pi over a wired connection.**

## Vision
The vision system was supposed to use a Raspberry Pi AI kit for the inference of a custom trained YOLOv11n model. T

he model was completed in time and compiled to the Hailo format, it is the ```yolov11n.hef``` file, but I didn't have time to implement it as I had connection issues.

The ```detection_simple.py``` has an example on how to use OpenCV with the Hailo-8L. For the venv to run the Hailo, follow the [Hailo-RPI5-examples tutorial](https://github.com/hailo-ai/hailo-rpi5-examples).

The ```vision.py```right now uses colour masks to identify objects. 

Other robots are prohibited from using similar Yellow, Blue, Orange and Green colours, but some didn't want to abide by the rules. (Yes, some shade was thrown)

The goal detection is quite bad. I tried to fix it, but I didn't have a solid connection to the robot, so I couldn't even save the file using ssh.

# Manual mode
The ```client.py``` runs on a laptop with a controller like the Xbox Series controller connected.
The IP address of the server must be changed (not needed if your Raspberry Pi advertises itself under ```proustite.local```).

The ```server.py```runs on the Raspberry Pi.

Please note the port must match between the computers and the port must be open on both of the computers.