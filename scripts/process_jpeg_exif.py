#!/usr/bin/env python3
"""
This script is a command-line tool designed to manage the `DateTimeOriginal`
EXIF timestamp of JPEG images within a specified directory.

It performs the following main functions:

1.  **File Scanning:** It recursively searches the provided directory for all
    JPEG files (with .jpg or .jpeg extensions).

2.  **Filename Parsing:** For each file, it attempts to parse a date and time
    from its filename, looking for the specific format YYYYMMDD-HHMMSS.

3.  **EXIF Data Handling:** It uses the external command-line utility `exiftool`
    to interact with the image's metadata. It first reads the existing
    `DateTimeOriginal` tag.
    - If an EXIF timestamp exists, it compares it with the filename's
      timestamp. If they differ by more than one second, it prints a
      "Timestamp mismatch" warning.
    - If no EXIF timestamp exists, it sets the `DateTimeOriginal` tag in the
      file using the timestamp parsed from the filename, modifying the file
      directly.
"""
import os
import re
import subprocess
import argparse
from datetime import datetime, timedelta
from tqdm import tqdm

def find_jpeg_files(directory):
    """Recursively finds all JPEG files in a directory."""
    jpeg_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg')):
                jpeg_files.append(os.path.join(root, file))
    return jpeg_files

def parse_datetime_from_filename(filename):
    """Parses YYYYMMDD-HHMMSS from the filename."""
    match = re.search(r'(\d{8})-(\d{6})', os.path.basename(filename))
    if match:
        try:
            return datetime.strptime(f"{match.group(1)}{match.group(2)}", '%Y%m%d%H%M%S')
        except ValueError:
            return None
    return None

def get_exif_datetime(filepath):
    """Gets the DateTimeOriginal from a file using exiftool."""
    try:
        cmd = ['exiftool', '-s', '-s', '-s', '-DateTimeOriginal', filepath]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            return datetime.strptime(result.stdout.strip(), '%Y:%m:%d %H:%M:%S')
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None
    return None

def set_exif_datetime(filepath, dt_object):
    """Sets the DateTimeOriginal in a file using exiftool."""
    dt_str = dt_object.strftime('%Y:%m:%d %H:%M:%S')
    try:
        cmd = ['exiftool', f'-DateTimeOriginal="{dt_str}"', '-overwrite_original', filepath]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def process_images(directory):
    """Processes all JPEG images in a directory."""
    print(f"Scanning for JPEG files in '{directory}'...")
    jpeg_files = find_jpeg_files(directory)
    if not jpeg_files:
        print("No JPEG files found.")
        return

    total_files = len(jpeg_files)
    print(f"Found {total_files} JPEG files. Starting processing...")

    with tqdm(total=total_files, unit='file') as pbar:
        for filepath in jpeg_files:
            filename_dt = parse_datetime_from_filename(filepath)
            if not filename_dt:
                tqdm.write(f"Could not parse datetime from filename: {os.path.basename(filepath)}")
                pbar.update(1)
                continue

            exif_dt = get_exif_datetime(filepath)

            if exif_dt:
                # Check for difference
                if abs((filename_dt - exif_dt).total_seconds()) > 1:
                    tqdm.write(f"Timestamp mismatch for {os.path.basename(filepath)}: "
                               f"Filename: {filename_dt}, EXIF: {exif_dt}")
            else:
                # Set the datetime
                tqdm.write(f"Setting EXIF datetime for {os.path.basename(filepath)} to {filename_dt}")
                if not set_exif_datetime(filepath, filename_dt):
                    tqdm.write(f"Failed to set EXIF for {os.path.basename(filepath)}")
            
            pbar.update(1)

    print("\nProcessing complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'directory', 
        metavar='DIRECTORY',
        type=str, 
        help='The directory to process recursively.'
    )
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found at '{args.directory}'")
        exit(1)
        
    try:
        subprocess.run(['exiftool', '-ver'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: 'exiftool' is not installed or not in your PATH.")
        print("Please install it to use this script (e.g., 'sudo apt-get install libimage-exiftool-perl')")
        exit(1)

    process_images(args.directory)