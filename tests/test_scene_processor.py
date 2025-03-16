# tests/test_scene_processor.py

import os
from app.services.scene_processor import process_scene_with_effect_chain

def main():
    # Define a sample mockup configuration for the basic mockup.
    # In a real system, this could be loaded from a JSON configuration file.
    mockup_config = {
        "assets": {
            "background": "assets/mockup1/background.mov",
            "reflections": "assets/mockup1/reflections.mov",
            "mask": "assets/mockup1/mask.mov",
            "corner_pin_data": "assets/mockup1/corner_pin_data.json"
        },
        "effects_chain": [
            {"effect": "corner_pin", "params": {"use_mask": True}},
            {"effect": "reflections", "params": {"opacity": 0.5}}
        ]
    }

    # Path to the user-supplied video
    user_video_path = "assets/screen-preview.mov"
    
    # Define the scene timing.
    # For example, we use the first 90 frames (at 24 fps, that's 90/24 seconds).
    scene_timing = {"in_frame": 0, "out_frame": 90}
    
    # Define the output path for the processed scene.
    output_path = "uploads/processed_scenes/scene_test.mp4"
    
    # Ensure that the output directory exists.
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print("Starting scene processing...")
    process_scene_with_effect_chain(mockup_config, user_video_path, scene_timing, output_path)
    print("Processed scene video saved at:", output_path)

if __name__ == "__main__":
    main()
