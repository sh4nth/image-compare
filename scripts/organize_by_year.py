#!/usr/bin/env python3
"""
Organizes misplaced files from a specific year's directory into their correct
year-specific subdirectories.

This script takes a single year (YYYY) as an argument and scans the
corresponding directory (e.g., './2023/'). For each file within that directory,
it checks if the filename starts with a four-digit prefix.

- If the prefix matches the containing folder's year, the file is ignored.
- If the prefix is a different year (e.g., a file '2022-photo.jpg' is found
  inside the '2023' folder), the script will move it to the correct year's
  directory (e.g., to './2022/').

It assumes the target year directories already exist.

If a file with the same name already exists in the destination folder, the
script will add a sequential, two-digit suffix to the new file's name before
the extension (e.g., '2022-photo-01.jpg') to prevent overwriting.

The --dry-run flag can be used to print the intended file moves without
actually executing them.
"""
import os
import re
import shutil
import argparse

def organize_files_by_year(source_year, dry_run=False):
    """
    Scans a source year directory and moves files that are prefixed with a
    different year to their correct year-named folder.

    Args:
        source_year (str): The four-digit year of the directory to scan.
        dry_run (bool): If True, prints actions without moving files.
    """
    # Check if the source year directory exists.
    if not os.path.isdir(source_year):
        print(f"Error: Source directory '{source_year}' does not exist.")
        return

    # Regex to find files starting with any four-digit year.
    prefix_pattern = re.compile(r'^(\d{4})')

    # Get a list of all files in the source directory.
    try:
        files_in_source_dir = [f for f in os.listdir(source_year) if os.path.isfile(os.path.join(source_year, f))]
    except OSError as e:
        print(f"Error reading directory '{source_year}': {e}")
        return

    if not files_in_source_dir:
        print(f"No files found in directory '{source_year}'.")
        return

    print(f"Scanning {len(files_in_source_dir)} files in '{source_year}'...")

    for filename in files_in_source_dir:
        match = prefix_pattern.match(filename)

        # Skip files that don't have a 4-digit prefix.
        if not match:
            continue

        file_prefix_year = match.group(1)

        # Ignore files that are already in the correct year's directory.
        if file_prefix_year == source_year:
            continue

        # This file is misplaced and needs to be moved.
        destination_year = file_prefix_year
        source_path = os.path.join(source_year, filename)

        # Check if the destination directory exists before attempting a move.
        if not os.path.isdir(destination_year):
            print(f"Warning: Destination directory '{destination_year}' for file '{filename}' does not exist. Skipping.")
            continue

        destination_path = os.path.join(destination_year, filename)

        # Handle potential filename collisions in the destination.
        if os.path.exists(destination_path):
            base, extension = os.path.splitext(filename)
            counter = 1
            while True:
                new_filename = f"{base}-{counter:02d}{extension}"
                new_destination_path = os.path.join(destination_year, new_filename)
                if not os.path.exists(new_destination_path):
                    destination_path = new_destination_path
                    break
                counter += 1
        
        # Move the file or print the action for a dry run.
        if dry_run:
            print(f"[DRY RUN] Would move: '{source_path}' -> '{destination_path}'")
        else:
            try:
                shutil.move(source_path, destination_path)
                print(f"Moved: '{source_path}' -> '{destination_path}'")
            except shutil.Error as e:
                print(f"Error moving file '{filename}': {e}")

    print("\nOrganization complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'year',
        type=str,
        help='The four-digit year of the directory to scan for misplaced files (e.g., "2023").'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print the planned file moves without executing them.'
    )
    args = parser.parse_args()

    if not re.match(r'^\d{4}$', args.year):
        print("Error: Please provide a valid four-digit year.")
        parser.print_help()
        exit(1)

    organize_files_by_year(args.year, args.dry_run)