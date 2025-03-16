# test_corner_pin_only.py

from app.services.video_manipulation import *

if __name__ == "__main__":
    # Paths to your assets.
    background_path = "assets/background.mov" 
    user_video_path = "assets/screen-preview.mov" 
    reflections_path = "assets/reflections.mov"         # The user-supplied screen video.
    corner_pin_data_path = "assets/cp/anim_mock_free_cp.json"   # The exported corner pin data (JSON file).
    output_path = "uploads/corner_pin_output.mp4"
    mask_path = "assets/mask.mov"
    
    composite_all_layers(background_path,
                         user_video_path,
                         reflections_path,
                         corner_pin_data_path,
                         mask_path,
                         output_path)
    print("Final composite video created at:", output_path)