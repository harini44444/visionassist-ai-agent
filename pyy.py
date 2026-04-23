

import cv2
from ultralytics import YOLO
import pyttsx3
import gradio as gr
import time
import numpy as np
import os

# Initialize TTS engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

# Load YOLOv8 model
model = YOLO("/content/yolov8n.pt")  # path to your YOLOv8 model

# Cooldown dictionary to prevent repeated speech
last_spoken = {}
SPEAK_COOLDOWN = 3  # seconds

# Placeholder calibration parameters (These would ideally be determined through a calibration process)
KNOWN_DISTANCE = 100  # Distance from camera to object during calibration (in cm)
KNOWN_WIDTH = 50  # Real-world width of the object used for calibration (e.g., average person shoulder width in cm)
FOCAL_LENGTH = 700  # Placeholder for focal length (This needs to be calibrated)
AUDIO_GAP = 2 # seconds gap between speaking each object


# Function to calculate distance to camera
def distance_to_camera(known_width, focal_length, pixel_width):
    """
    Calculates the distance of an object from the camera using triangle similarity.
    """
    # Add a small value to pixel_width to avoid division by zero,
    # although the check `if pixel_width > 0` should prevent this.
    # This is an extra precaution.
    return (known_width * focal_length) / (pixel_width + 1e-6)


# Function to process frame, detect objects, and generate speech audio
def detect_objects(frame):
    global last_spoken

    # Convert frame from RGB (Gradio) to BGR (OpenCV)
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    # YOLOv8 inference
    results = model(frame_bgr)[0]

    objects_detected_info = [] # Store tuples of (label, distance)
    current_time = time.time()

    # Loop through detections
    for det in results.boxes:
        label = model.names[int(det.cls[0])]

        # Calculate bounding box width in pixels
        x1, y1, x2, y2 = map(int, det.xyxy[0])
        pixel_width = x2 - x1

        distance = None # Initialize distance to None
        # Estimate distance
        if pixel_width > 0: # Avoid division by zero
            # NOTE: For accurate distance estimation of various objects,
            # you would need known widths for each object class or a
            # more sophisticated depth estimation method.
            # Using a placeholder KNOWN_WIDTH here for demonstration.
            distance = distance_to_camera(KNOWN_WIDTH, FOCAL_LENGTH, pixel_width)


        # Check cooldown and add detection info
        if label not in last_spoken or current_time - last_spoken[label] > SPEAK_COOLDOWN:
            # Store label and distance for speaking later
            objects_detected_info.append((label, distance))
            last_spoken[label] = current_time # Update last spoken time for this label


        # Draw bounding box
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
        # Add distance to the text displayed on the frame
        display_text = f"{label}: {distance:.2f} cm" if distance is not None else label
        cv2.putText(frame_bgr, display_text, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    # Generate speech audio based on collected information with gaps
    speech_text = ""
    audio_output = None

    if objects_detected_info:
        for i, (label, distance) in enumerate(objects_detected_info):
            speech_phrase = ""
            if distance is not None:
                speech_phrase = f"{label} at {distance:.2f} centimeters"
            else:
                speech_phrase = f"{label}"

            if speech_phrase:
                # Save the speech to a temporary file
                temp_audio_file = f"temp_speech_{i}.mp3" # Use unique filename for each object
                engine.save_to_file(speech_phrase, temp_audio_file)
                engine.runAndWait()
                # Read the audio file
                if os.path.exists(temp_audio_file):
                    # In a real-world scenario, you might want to play these audio files sequentially
                    # within the Gradio interface or a separate thread.
                    # For this example, we'll just save the last one or concatenate.
                    # Returning the last one for simplicity, or you could return a list of paths.
                    audio_output = temp_audio_file
                    # Add a delay after speaking each object
                    time.sleep(AUDIO_GAP)


    # Convert frame back to RGB for Gradio
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    # Return both the processed image and the audio file path
    # Note: Returning only the last audio file path in this simplified example.
    # A more robust solution would handle multiple audio outputs or concatenation.
    return frame_rgb, audio_output


# Gradio Interface
iface = gr.Interface(
    fn=detect_objects,
    inputs=gr.Image(streaming=True),
    outputs=["image", gr.Audio(label="Detected Objects Audio", autoplay=True)],
    live=True,
    title="YOLOv8 Object Detection for Blind Assistance",
    description="Uses webcam feed to detect objects and speaks them aloud."
)

iface.launch()