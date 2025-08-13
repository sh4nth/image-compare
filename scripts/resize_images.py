#!/usr/bin/env python3

import os
import sys
import argparse
import shutil
import subprocess
import tempfile
from PIL import Image, ImageSequence, ExifTags
from tqdm import tqdm

# Define the maximum size for the resized images
MAX_SIZE = (1080, 1080)

def human_readable_size(size, decimal_places=2):
    """Formats bytes into a human-readable string (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

def is_tool_installed(name):
    """Check whether `name` is on PATH and marked as executable."""
    return shutil.which(name) is not None

def resize_image(source_path, output_path, use_gifsicle=False):
    """
    Dispatches image processing to format-specific functions.
    Returns the number of bytes saved.
    """
    original_size = os.path.getsize(source_path)
    
    try:
        with Image.open(source_path) as img:
            is_too_large = img.width > MAX_SIZE[0] or img.height > MAX_SIZE[1]
            
            # For GIFs, we always process them to potentially optimize them.
            if img.format == 'GIF':
                _resize_gif_with_optimization(img, source_path, output_path, use_gifsicle)
            # For other images, we only process if they are too large.
            elif is_too_large:
                if img.format == 'JPEG':
                    _resize_jpeg_with_exif(img, output_path)
                else:
                    _resize_other_image(img, output_path)
            # Otherwise, just copy the file.
            else:
                shutil.copy2(source_path, output_path)

        resized_size = os.path.getsize(output_path)
        bytes_saved = original_size - resized_size
        return bytes_saved

    except (IOError, OSError, Image.UnidentifiedImageError, subprocess.CalledProcessError) as e:
        print(f"ERROR: Could not process file {source_path}. Reason: {e}", file=sys.stderr)
        return 0


def process_directory(input_dir, test_mode=False):
    """
    Recursively traverses the input directory, finds images, and resizes them.
    """
    # Create the output directory next to the input directory
    parent_dir = os.path.dirname(os.path.abspath(input_dir))
    output_dir = os.path.join(parent_dir, 'small-images')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # Check for gifsicle and inform the user
    use_gifsicle = is_tool_installed('gifsicle')
    if not use_gifsicle:
        print("WARNING: 'gifsicle' not found. GIFs will be resized but not optimally compressed.")
        print("         For smaller GIFs, please install gifsicle (e.g., 'sudo apt-get install gifsicle')")


    supported_extensions = ('.jpg', '.jpeg', '.png', '.gif')
    
    # Pre-scan to build the list of files to process
    files_to_process = []
    if test_mode:
        print("Test mode enabled: will process up to 2 files per extension.")
        test_counts = {ext: 0 for ext in supported_extensions}
        test_limit = 2
        for root, _, files in os.walk(input_dir):
            for filename in files:
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in supported_extensions:
                    if test_counts.get(file_ext, 0) < test_limit:
                        files_to_process.append(os.path.join(root, filename))
                        test_counts[file_ext] += 1
            # Optimization: if all limits are reached, stop walking
            if all(count >= test_limit for count in test_counts.values()):
                break
    else:
        for root, _, files in os.walk(input_dir):
            for filename in files:
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in supported_extensions:
                    files_to_process.append(os.path.join(root, filename))

    # Main processing loop is now unified
    total_bytes_saved = 0
    with tqdm(total=len(files_to_process), desc="Resizing images", unit="file") as pbar:
        for source_path in files_to_process:
            filename = os.path.basename(source_path)
            output_path = os.path.join(output_dir, filename)
            
            bytes_saved = resize_image(source_path, output_path, use_gifsicle)
            if bytes_saved > 0:
                total_bytes_saved += bytes_saved
            
            pbar.update(1)
            pbar.set_postfix_str(f"Saved: {human_readable_size(total_bytes_saved)}")

    print(f"\nTotal space saved: {human_readable_size(total_bytes_saved)}")


def main():
    """
    Main function to parse arguments and start the processing.
    """
    parser = argparse.ArgumentParser(
        description="Recursively find and resize images in a directory.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'input_dir',
        type=str,
        help="The directory to search for images."
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help="Run in test mode: resize only the first 2 files of each type."
    )
    
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory not found at '{args.input_dir}'", file=sys.stderr)
        sys.exit(1)
        
    process_directory(args.input_dir, args.test)
    print("\nProcessing complete.")


# --- Image Processing Helper Functions ---

def _resize_gif_with_optimization(img, source_path, output_path, use_gifsicle):
    """Helper to resize and optimize a GIF."""
    needs_resize = img.width > MAX_SIZE[0] or img.height > MAX_SIZE[1]
    
    # Fallback if gifsicle is not available
    if not use_gifsicle:
        frames = []
        for frame in ImageSequence.Iterator(img):
            frame_copy = frame.copy()
            if needs_resize:
                frame_copy.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
            frames.append(frame_copy)
        
        if frames:
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                loop=img.info.get('loop', 0),
                duration=img.info.get('duration', 100),
                format='GIF'
            )
        return

    # Gifsicle path
    temp_path = None
    input_for_gifsicle = source_path

    if needs_resize:
        # Resize with Pillow first into a temporary file
        frames = []
        for frame in ImageSequence.Iterator(img):
            frame_copy = frame.copy()
            frame_copy.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
            frames.append(frame_copy)
        
        if frames:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as temp_f:
                temp_path = temp_f.name
            
            frames[0].save(
                temp_path,
                save_all=True,
                append_images=frames[1:],
                loop=img.info.get('loop', 0),
                duration=img.info.get('duration', 100),
                format='GIF'
            )
            input_for_gifsicle = temp_path
    
    # Optimize with gifsicle
    subprocess.run(
        ['gifsicle', '-O3', '--lossy=80', input_for_gifsicle, '-o', output_path],
        check=True,
        capture_output=True
    )

    if temp_path and os.path.exists(temp_path):
        os.remove(temp_path)

def _resize_jpeg_with_exif(img, output_path):
    """Helper to resize a JPEG and preserve EXIF."""
    exif_data = img.info.get('exif')
    img_copy = img.copy()
    img_copy.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
    
    if exif_data:
        img_copy.save(output_path, 'JPEG', exif=exif_data)
    else:
        img_copy.save(output_path, 'JPEG')

def _resize_other_image(img, output_path):
    """Helper to resize a non-GIF, non-JPEG image."""
    img_copy = img.copy()
    img_copy.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
    img_copy.save(output_path, img.format)


if __name__ == '__main__':
    main()
