from moviepy.editor import VideoFileClip, VideoClip
import os

def match_clips_size(bcg, over):
    if over.size != bcg.size:
        return over.resize(bcg.size)
        
def calculate_duration(clip1, clip2):
    return min(clip1.duration, clip2.duration)
