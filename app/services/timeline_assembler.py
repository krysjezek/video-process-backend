# app/services/timeline_assembler.py

import os
import gc
import psutil
import moviepy.editor as mpy
from typing import List
from app.config.logging import get_logger

logger = get_logger(component="timeline_assembler")

def log_memory_usage():
    """Log current memory usage."""
    process = psutil.Process()
    mem_info = process.memory_info()
    logger.info(
        "memory_usage",
        rss_mb=mem_info.rss / 1024 / 1024,
        vms_mb=mem_info.vms / 1024 / 1024
    )

def assemble_timeline(scene_file_paths: List[str], output_path: str) -> None:
    """
    Join scene clips in the user-defined order and write the final MP4.
    
    Args:
        scene_file_paths: List of paths to processed scene videos
        output_path: Path where the final composite video should be written
        
    Raises:
        FileNotFoundError: If any input file doesn't exist
        OSError: If output directory can't be created or other I/O errors occur
    """
    logger.info("starting_timeline_assembly", scene_count=len(scene_file_paths))
    log_memory_usage()
    
    # First verify all input files exist
    missing_files = [fp for fp in scene_file_paths if not os.path.exists(fp)]
    if missing_files:
        logger.error("missing_input_files", files=missing_files)
        raise FileNotFoundError(f"The following input files do not exist: {', '.join(missing_files)}")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir:  # Only create if there's a directory component
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            logger.error("failed_to_create_output_directory", error=str(e))
            raise OSError(f"Failed to create output directory {output_dir}: {str(e)}")
    
    clips = []
    base_size = None
    
    try:
        # Load each processed scene as a VideoFileClip
        for fp in scene_file_paths:
            try:
                clip = mpy.VideoFileClip(fp)
                
                # Check resolution consistency
                if base_size is None:
                    base_size = clip.size
                elif clip.size != base_size:
                    raise ValueError(
                        f"Video resolution mismatch: {fp} has size {clip.size}, "
                        f"expected {base_size}"
                    )
                
                clips.append(clip)
                log_memory_usage()
                
            except (IOError, OSError) as e:
                logger.error("failed_to_load_clip", file=fp, error=str(e))
                # Clean up any clips we've opened so far
                for c in clips:
                    c.close()
                raise OSError(f"Failed to load video file {fp}: {str(e)}")
        
        # Concatenate the scene clips in order
        final_clip = mpy.concatenate_videoclips(clips, method="compose")
        
        try:
            # Write the final composite timeline video
            final_clip.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                threads=4,  # Use multiple threads for faster encoding
                preset="medium"  # Balance between speed and compression
            )
            
            logger.info("timeline_assembly_completed")
            log_memory_usage()
            
        except (IOError, OSError) as e:
            logger.error("failed_to_write_output", file=output_path, error=str(e))
            raise OSError(f"Failed to write output file {output_path}: {str(e)}")
            
    finally:
        # Clean up resources
        for clip in clips:
            try:
                clip.close()
            except:  # noqa: E722
                pass  # Ignore errors during cleanup
        if 'final_clip' in locals():
            try:
                final_clip.close()
            except:  # noqa: E722
                pass
        gc.collect()  # Force garbage collection
        log_memory_usage()
