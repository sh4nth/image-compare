#!/usr/bin/env python3
"""
This script processes JPEG images in a specified directory to generate a shell
script for renaming them based on their creation timestamp.

It performs the following steps:

1.  **Scans for Images:** It recursively searches the provided directory for all
    JPEG files (.jpg, .jpeg).

2.  **Finds Timestamps:** For each image, it tries to find the creation date and
    time from two sources, in order of preference:
    a.  It uses the `exiftool` utility to read the `DateTimeOriginal` tag from
        the image's EXIF metadata.
    b.  If EXIF data is unavailable, it looks for a corresponding Google Photos
        JSON file (e.g., `image.jpg.supplemental-metadata.json`) and reads the
        `photoTakenTime` timestamp from there.

3.  **Formats New Filenames:** The timestamp is formatted into a `YYYYMMDD-HHMMSS`
    string, which becomes the new base filename.

4.  **Handles Duplicates:** If multiple images have the exact same timestamp, it
    appends a sequential suffix (e.g., `-01`, `-02`) to the new filename to
    avoid conflicts.

5.  **Generates a Shell Script:** It does not rename the files directly. Instead, it
    appends `mv` commands to a shell script named `ALL_YEARS.sh` in the current
    directory. This script, when run, will:
    a.  Rename the image to its new timestamp-based name.
    b.  Rename the associated JSON file if one was used.
    c.  Move the renamed files into a parallel directory structure under a `done/`
        directory, preserving the original folder hierarchy.

6.  **Logs Failures:** If a timestamp cannot be found for an image, it adds a
    commented-out line in the `ALL_YEARS.sh` script indicating the failure.

This script requires `exiftool` to be installed and in the system's PATH.
"""
import os
import subprocess
import sys
import re
import json
from datetime import datetime
from collections import defaultdict

def get_exif_datetime(filepath):
    """Runs exiftool on a file and returns the DateTimeOriginal tag."""
    try:
        result = subprocess.run(
            ['exiftool', '-T', '-DateTimeOriginal', filepath],
            capture_output=True, text=True, check=False
        )
        if result.returncode != 0 or not result.stdout.strip() or result.stdout.strip() == '-':
            return None
        return result.stdout.strip()
    except (FileNotFoundError):
        print("Error: exiftool not found. Please install it to read EXIF data.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running exiftool on {filepath}: {e}", file=sys.stderr)
        return None

def find_json_file(image_path):
    """Finds the JSON file associated with an image, trying different truncations."""
    num = None
    metadata_name = f"{image_path}.supplemental-metadata"
    match = re.match(r'(.*)(\([0-9]+\))(\.[a-zA-Z]*)', image_path)
    if match:
        filename, num, ext = match.groups()
        metadata_name = f'{filename}{ext}.supplemental-metadata'
    for i in range(len(metadata_name), 10, -1):
        substring = metadata_name[:i]
        potential_json_path = f"{substring}{num}.json" if num else f"{substring}.json"
        if os.path.exists(potential_json_path):
            return potential_json_path
    return None

def get_json_datetime(json_filepath):
    """Extracts and formats the timestamp from a JSON file."""
    try:
        with open(json_filepath, 'r') as f:
            data = json.load(f)
            timestamp_str = data.get('photoTakenTime', {}).get('timestamp')
            if timestamp_str:
                dt_object = datetime.fromtimestamp(int(timestamp_str))
                return dt_object.strftime('%Y%m%d-%H%M%S')
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Could not process JSON file {json_filepath}: {e}", file=sys.stderr)
    return None

def format_exif_datetime(dt_string):
    """Formats 'YYYY:MM:DD HH:MM:SS' to 'YYYYMMDD-HHMMSS'."""
    if not dt_string:
        return None
    return dt_string.replace(':', '').replace(' ', '-', 1)



def process(directory):
  with open('ALL_YEARS.sh', 'a') as f_out:
    timestamp_counts = defaultdict(int)
    
    # First pass: Collect all potential new basenames and their counts
    all_files = []
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(('.jpg', '.jpeg')):
                all_files.append(os.path.join(root, filename))

    # Generate all potential new names
    potential_renames = {}
    total = len(all_files)
    block = total // 10 if total > 10 else total
    print(f'{len(all_files)} to process in {directory}')
    for filepath in sorted(all_files):
        timestamp = None
        exif_dt = get_exif_datetime(filepath)
        if exif_dt:
            timestamp = format_exif_datetime(exif_dt)
        
        json_path = find_json_file(filepath)
        if not timestamp:
            if json_path:
                timestamp = get_json_datetime(json_path)

        if timestamp:
            potential_renames[filepath] = (timestamp, json_path)
            timestamp_counts[timestamp] += 1
        else:
            potential_renames[filepath] = (None, None)


    # Second pass: Generate the actual commands with suffixes for duplicates
    processed_timestamps = defaultdict(int)
    done = 0
    for filepath in sorted(all_files):
        timestamp, json_path = potential_renames.get(filepath, (None, None))
        done += 1
        if done % block == 0:
            print(f'  {done:04}/{len(all_files):04} done', flush=True)
        if timestamp:
            base_new_name = timestamp
            current_count = processed_timestamps[base_new_name]
            processed_timestamps[base_new_name] += 1

            suffix = ""
            # Add suffix only if there are duplicates
            if timestamp_counts[base_new_name] > 1:
                suffix = f"-{current_count:02d}"

            extension = os.path.splitext(filepath)[1]
            new_filename = f"{base_new_name}{suffix}{extension}"
            new_filepath = os.path.join('done', os.path.dirname(filepath), new_filename)

            f_out.write(f'mv "{filepath}" "{new_filepath}"\n')

            if json_path:
                new_json_filename = f"{base_new_name}{suffix}.json"
                new_json_filepath = os.path.join('done', os.path.dirname(filepath), new_json_filename)
                f_out.write(f'mv "{json_path}" "{new_json_filepath}"\n')
            else:
                f_out.write(f'# No json file for {filepath}\n')
        else:
            f_out.write(f'# No timestamp information available for {filepath}\n')

    print(f'Done')


def main():
    """Main function to find images, get timestamps, and generate rename commands."""
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(f"Usage: {sys.argv[0]} <directory>\n")
        print(__doc__)
        sys.exit(0)

    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: Directory not found at '{directory}'", file=sys.stderr)
        sys.exit(1)
    process(directory)

if __name__ == "__main__":
    main()