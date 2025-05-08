#!/usr/bin/env python3
import argparse
import time
import multiprocessing
import subprocess
import statistics
from pathlib import Path
import json
from datetime import datetime
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Process, Manager

def get_absolute_path(path):
    """Convert relative path to absolute path."""
    return os.path.abspath(path)

def process_video(video_path, output_path):
    """
    Process a single video using Docker.
    
    Args:
        video_path: Path to the input video file
        output_path: Path where the processed video should be saved
        
    Returns:
        float: Processing time in seconds, or None if processing failed
    """
    try:
        # Convert paths to absolute paths as strings
        video_path = str(Path(video_path).resolve())
        output_path = str(Path(output_path).resolve())
        project_root = str(Path(__file__).resolve().parent.parent.parent)
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Get relative paths for Docker command
        rel_video_path = os.path.relpath(video_path, project_root)
        rel_output_path = os.path.relpath(output_path, project_root)

        # Prepare Docker command with proper path handling
        cmd = f"""docker run --rm \
                -v {project_root}:/app \
                -w /app video-process-backend-test \
                bash -c "pip install -e . && python3 -c \\"
import sys
sys.path.append('/app')
from app.video_processor import VideoProcessor
from app.config import Config

config = Config()
processor = VideoProcessor(config)
processor.process_video('{rel_video_path}', '{rel_output_path}')
\\""
"""
        start_time = time.time()
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        end_time = time.time()
        
        if result.stderr:
            print(f"Warning: {result.stderr}")
            
        return end_time - start_time
        
    except subprocess.CalledProcessError as e:
        print(f"Error processing video: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return None

def process_video_wrapper(args):
    """
    Wrapper function for process_video to be used with ProcessPoolExecutor.
    """
    video_path, output_path, results = args
    try:
        processing_time = process_video(video_path, output_path)
        if processing_time is not None:
            results.append(processing_time)
    except Exception as e:
        print(f"Error in process_video_wrapper: {e}")

def run_concurrent_test(video_path, output_dir, num_concurrent=3, num_runs=5):
    """
    Run concurrent video processing tests.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with Manager() as manager:
        results = manager.list()
        
        for run in range(num_runs):
            print(f"\nStarting run {run + 1}/{num_runs}")
            
            # Create tasks for concurrent processing
            tasks = []
            for i in range(num_concurrent):
                output_path = output_dir / f"output_{run}_{i}.mp4"
                tasks.append((video_path, output_path, results))

            # Run tasks concurrently
            with ProcessPoolExecutor(max_workers=num_concurrent) as executor:
                executor.map(process_video_wrapper, tasks)

    return list(results)  # Convert manager list to regular list

def calculate_throughput(processing_times):
    """
    Calculate throughput statistics from processing times.
    """
    if not processing_times:
        return {
            "avg_throughput": 0,
            "min_throughput": 0,
            "max_throughput": 0,
            "total_videos": 0,
            "successful_videos": 0
        }

    # Calculate throughput (videos per minute)
    throughputs = [60 / t for t in processing_times if t > 0]  # Avoid division by zero
    
    return {
        "avg_throughput": sum(throughputs) / len(throughputs) if throughputs else 0,
        "min_throughput": min(throughputs) if throughputs else 0,
        "max_throughput": max(throughputs) if throughputs else 0,
        "total_videos": len(processing_times),
        "successful_videos": len(throughputs)
    }

def main():
    parser = argparse.ArgumentParser(description='Video encoding performance test')
    parser.add_argument('--concurrency', type=int, default=5,
                        help='Number of concurrent processes')
    parser.add_argument('--runs', type=int, default=3,
                        help='Number of test runs')
    parser.add_argument('--video', type=str, default='tests/assets/screen-preview.mov',
                        help='Path to input video')
    parser.add_argument('--output-dir', type=str, default='tests/perf/output',
                        help='Directory for output videos')
    args = parser.parse_args()
    
    print(f"Starting performance test with {args.concurrency} concurrent processes, {args.runs} runs")
    print(f"Input video: {args.video}")
    
    processing_times = run_concurrent_test(args.video, args.output_dir, args.concurrency, args.runs)
    results = calculate_throughput(processing_times)
    
    # Calculate metrics
    avg_throughput = results["avg_throughput"]
    min_throughput = results["min_throughput"]
    max_throughput = results["max_throughput"]
    total_videos = results["total_videos"]
    successful_videos = results["successful_videos"]
    
    # Print results
    print("\nPerformance Results:")
    print(f"Average throughput: {avg_throughput:.2f} videos/minute")
    print(f"Min throughput: {min_throughput:.2f} videos/minute")
    print(f"Max throughput: {max_throughput:.2f} videos/minute")
    print(f"Total videos: {total_videos}")
    print(f"Successful videos: {successful_videos}")
    
    # Save results to JSON
    results["timestamp"] = datetime.now().isoformat()
    results["num_concurrent"] = args.concurrency
    results["num_runs"] = args.runs
    
    output_file = Path('report') / 'performance-results.json'
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")

if __name__ == '__main__':
    main() 