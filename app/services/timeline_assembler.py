# app/services/timeline_assembler.py

import os
import moviepy.editor as mpy

def assemble_timeline(scene_file_paths, output_path):
    """
    Concatenates processed scene videos into a final composite video.
    
    Parameters:
      - scene_file_paths: List of file paths to the processed scene videos, in the desired order.
      - output_path: The file path where the final composite video will be saved.
      
    Returns:
      None. Writes the final video to output_path.
    """
    # Ensure the output directory exists.
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Load each processed scene as a VideoFileClip.
    clips = [mpy.VideoFileClip(fp) for fp in scene_file_paths]
    
    # Concatenate the scene clips in order.
    final_clip = mpy.concatenate_videoclips(clips, method="compose")
    
    # Write the final composite timeline video.
    final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
