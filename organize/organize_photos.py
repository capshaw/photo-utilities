"""
Photo Organization Script

This script takes a source directory full of photos (e.g. a folder directly from a camera) and copies those to another
destination folder in an organized fashion. In its current iteration that structure is destination/year/year-month-day.
In future iterations this may be configurable.

Earlier versions of this script used EXIF data to determine the date. The current version uses file create date as a
proxy. This has flaws and should eventually be modified to use EXIF when possible and fallback to file create date as a
backup. (For context this transition occurred when moving from Python2 to Python3.)

I created this after I realized I was paying for Lightroom just to organize my photos for me. This does that one thing
and that one thing only.
"""
import argparse
import pathlib
import os

from typing import NamedTuple
from datetime import datetime
from shutil import copyfile

class IntermediateFileState(NamedTuple):
    folders_to_create: dict[int, set[str]]
    files_to_copy: dict[str, str]

class PhotoOrganizerTool:

    def __init__(self):
        self.args = PhotoOrganizerTool.setup_command_line_parser()

    def run(self) -> None:
        self._log(f'Running PhotoOrganizerTool with arguments {self.args}')
        intermediate_file_state = self._process_and_prepare_files()
        self._create_folders(intermediate_file_state.folders_to_create)
        self._copy_files_to_destination(intermediate_file_state.files_to_copy)
        self._log('Script completed successfully')

    def _process_and_prepare_files(self) -> IntermediateFileState:
        """
        Iterate through all files in the directory represented in args.path_from. If these files are in the allowlist
        of filetypes to copy, add them to an intermediate representation to copy later. Similarly tracks
        """
        files_to_copy = {}
        folders_to_create = {}

        self._log('Processing files to determine what to copy')
        for filename in os.listdir(self.args.path_from):

            input_file_path = os.path.join(self.args.path_from, filename)
            if not self._is_file_whitelisted(filename):
                self._log(f'Skipping non-allowlisted file {input_file_path}')
                continue

            self._log(f'Processing {filename}')
            file_created_datetime = datetime.fromtimestamp(pathlib.Path(input_file_path).stat().st_mtime)
            file_created_year = file_created_datetime.year
            file_created_date_string = datetime.strftime(file_created_datetime, '%Y-%m-%d')

            # Store a record of the file structure we will later need to create
            if file_created_year not in folders_to_create:
                folders_to_create[file_created_year] = set()
            folders_to_create[file_created_year].add(file_created_date_string)

            # Create a mapping of input file to output file for later processing
            files_to_copy[input_file_path] = os.path.join(
                self.args.path_to,
                str(file_created_year),
                file_created_date_string,
                filename
            )

        return IntermediateFileState(folders_to_create=folders_to_create, files_to_copy=files_to_copy)

    def _create_folders(self, folders_to_create: dict[int, set[str]]) -> None:
        """
        Create new folders to store our data in our destination.

        TODO: could be more generic to support different pathing options
        """
        self._log('Creating new folders')
        for year_to_add in folders_to_create.keys():
            for date_to_add in folders_to_create[year_to_add]:
                path_to_create = os.path.join(self.args.path_to, str(year_to_add), date_to_add)
                if not os.path.exists(path_to_create):
                    self._log(f'Creating path {path_to_create}')
                    if not self.args.dryrun_enabled:
                        os.makedirs(path_to_create)
                else:
                    self._log(f'Skipping path {path_to_create} that already exists')

    def _copy_files_to_destination(self, files_to_copy: dict[str, str]) -> None:
        """
        Given a map of source path to destination path, copy files from the source to the destination.
        """
        self._log('Copying files to destination')
        for source_path in files_to_copy.keys():
            destination_path = files_to_copy[source_path]
            if not os.path.isfile(destination_path):
                self._log(f'Copying file from {source_path} to {destination_path}')
                if not self.args.dryrun_enabled:
                    copyfile(source_path, destination_path)
            else:
                self._log(f'Skipping {destination_path}. File already exists.')

    def _is_file_whitelisted(self, filename: str):
        """
        Returns True if the specified filename has a suffix in the tool's allowlist, False otherwise.
        """
        return pathlib.Path(filename).suffix[1:].lower() in self.args.allowlist_filetypes

    def _log(self, output: str) -> None:
        """
        If verbose mode is enabled, log useful details for debugging and tracking of the script's progress.
        """
        if self.args.verbose_enabled:
            now = datetime.now()
            print(f'[{now}] {output}')

    @staticmethod
    def setup_command_line_parser():
        """
        Use Python's argparse to handle all command-line configuration and parsing.
        """
        parser = argparse.ArgumentParser(
            description='A simple utility to process and organize photos into date-based folders.',
        )
        parser.add_argument(
            '-f',
            '--from',
            type=str,
            required=True,
            dest='path_from',
            help='the input file path to organize',
        )
        parser.add_argument(
            '-t',
            '--to',
            type=str,
            required=True,
            dest='path_to',
            help='the output file path where organized photos will be sent',
        )
        parser.add_argument(
            '--filetypes',
            type=str,
            nargs='+',
            default=['jpg', 'dng', 'arw'],
            required=False,
            dest='allowlist_filetypes',
            help='an allowlist of filetypes to process',
        )
        parser.add_argument(
            '--verbose',
            required=False,
            action='store_true',
            dest='verbose_enabled',
            help='enables verbose mode with more helpful diagnostic comments',
        )
        parser.add_argument(
            '--dryrun',
            required=False,
            action='store_true',
            dest='dryrun_enabled',
            help='enables dryrun mode, preventing actual file modification',
        )
        return parser.parse_args()

if __name__ == '__main__':
    PhotoOrganizerTool().run()