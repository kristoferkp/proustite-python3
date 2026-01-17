import os
from pathlib import Path
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import hailo
from hailo_platform import VDevice
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.hailo_app_python.apps.detection_simple.detection_pipeline_simple import GStreamerDetectionApp
from hailo_apps.hailo_app_python.core.common.core import get_default_parser
from hailo_apps.hailo_app_python.core.common.installation_utils import detect_hailo_arch
import cv2
import numpy as np
from hailo_apps.hailo_app_python.core.common.buffer_utils import get_caps_from_pad, get_numpy_from_buffer

import sys

# User-defined class to be used in the callback function: Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()

# User-defined callback function: This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    user_data.increment()  # Using the user_data to count the number of frames
    string_to_print = f"Frame count: {user_data.get_count()}\n"
    buffer = info.get_buffer()  # Get the GstBuffer from the probe info
    if buffer is None:  # Check if the buffer is valid
        return Gst.PadProbeReturn.OK
    
    format, width, height = get_caps_from_pad(pad) 
    frame = None
    if format is not None and width is not None and height is not None:
        frame = get_numpy_from_buffer(buffer, format, width, height)
        # Convert the frame to BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    for detection in hailo.get_roi_from_buffer(buffer).get_objects_typed(hailo.HAILO_DETECTION):  # Get the detections from the buffer & Parse the detections
        label = detection.get_label()
        confidence = detection.get_confidence()
        string_to_print += (f"Detection: {label} Confidence: {confidence:.2f}\n")
        
        if frame is not None:
            bbox = detection.get_bbox()
            # BBox coordinates are normalized (0-1)
            x_min = int(bbox.xmin() * width)
            y_min = int(bbox.ymin() * height)
            x_max = int(bbox.xmax() * width)
            y_max = int(bbox.ymax() * height)
            
            # Draw rectangle
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {confidence:.2f}", (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    if frame is not None:
        user_data.set_frame(frame)

    print(string_to_print)
    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    env_file     = project_root / "hailo-rpi5-examples" / ".env"
    env_path_str = str(env_file)
    os.environ["HAILO_ENV_FILE"] = env_path_str

    # Create the parser and add an argument for the video input
    parser = get_default_parser()
    parser.add_argument("--source", "-s", dest="input", type=str, help="Path to input video file for testing (alias for --input)")
    
    # Set default paths for HEF and labels JSON if not provided
    arch = detect_hailo_arch()
    hef_path = Path(__file__).parent / "yolov11n.hef"
    labels_json = project_root / "hailo-rpi5-examples" / "resources" / "json" / "yolov11n.json"
    
    if "--hef-path" not in sys.argv:
        parser.set_defaults(hef_path=str(hef_path))
    
    # Manually inject labels-json default into sys.argv if not present, because GStreamerDetectionApp adds it with default=None
    if "--labels-json" not in sys.argv:
         sys.argv.extend(["--labels-json", str(labels_json)])

    user_data = user_app_callback_class()  # Create an instance of the user app callback class
    app = GStreamerDetectionApp(app_callback, user_data, parser)
    app.options_menu.use_frame = True # Enable the display process in GStreamerApp
    app.run()
    
    # Release the VDevice to free resources
    VDevice().release()
