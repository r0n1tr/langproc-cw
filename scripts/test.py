#!/usr/bin/env python3

"""
A wrapper script to run all the compiler tests. This script will call the
Makefile, run the tests and store the outputs in bin/output.

This script will also generate a JUnit XML file, which can be used to integrate
with CI/CD pipelines.

Usage: test.py [-h] [-m] [-v] [--version] [dir]

Example usage: scripts/test.py compiler_tests/_example

This will print out a progress bar and only run the example tests.
The output would be placed into bin/output/_example/example/.

For more information, run scripts/test.py -h
"""


__version__ = "0.2.0"
__author__ = "William Huynh (@saturn691)"


import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from progress_bar import ProgressBar
from junit_xml_file import JUnitXMLFile
import xml.sax.saxutils

# "File" will suggest the absolute path to the file, including the extension.
SCRIPT_LOCATION = Path(__file__).resolve().parent
PROJECT_LOCATION = SCRIPT_LOCATION.joinpath("..").resolve()
OUTPUT_FOLDER = PROJECT_LOCATION.joinpath("bin/output").resolve()
J_UNIT_OUTPUT_FILE = PROJECT_LOCATION.joinpath(
    "bin/junit_results.xml").resolve()
COMPILER_TEST_FOLDER = PROJECT_LOCATION.joinpath("compiler_tests").resolve()


@dataclass
class Result:
    """Class for keeping track of each test case result"""
    test_case_name: str
    passed: bool
    error_log: Optional[str]

    def to_xml(self) -> str:
        if self.passed:
            return (
                f'<testcase name="{self.test_case_name}">\n'
                f'</testcase>\n'
            )

        attribute = xml.sax.saxutils.quoteattr(self.error_log)
        xml_tag_body = xml.sax.saxutils.escape(self.error_log)
        return (
            f'<testcase name="{self.test_case_name}">\n'
            f'<error type="error" message={attribute}>\n{xml_tag_body}</error>\n'
            f'</testcase>\n'
        )

    def to_log(self) -> str:
        if self.passed:
            return f'{self.test_case_name}\n\t> Pass\n'
        return f'{self.test_case_name}\n{self.error_log}\n'


def run_test(driver: Path) -> Result:
    """
    Run an instance of a test case.

    Returns:
    A Result object with the status (pass/fail) of the test.
    """

    # Replaces example_driver.c -> example.c
    new_name = driver.stem.replace('_driver', '') + '.c'
    to_assemble = os.path.relpath(driver.parent.joinpath(new_name), PROJECT_LOCATION)

    result = subprocess.run(
        [
            SCRIPT_LOCATION.joinpath("test_single.sh"),
            os.path.relpath(driver, PROJECT_LOCATION)
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_LOCATION,
    )
    if result.returncode != 0:
        return Result(to_assemble, False, result.stdout)

    return Result(to_assemble, True, None)


def process_result(
    result: Result,
    xml_file: JUnitXMLFile,
    verbose: bool = False,
    progress_bar: ProgressBar = None,
):
    xml_file.write(result.to_xml())

    if verbose:
        print(result.to_log())
        return

    if not progress_bar:
        return

    progress_bar.update_with_value(result.passed)


def run_tests(args, xml_file):
    drivers = list(Path(args.dir).rglob("*_driver.c"))
    drivers = sorted(drivers, key=lambda p: (p.parent.name, p.name))
    results = []

    progress_bar = None
    if sys.stdout.isatty():
        progress_bar = ProgressBar(len(drivers))
    else:
        # Force verbose mode when not a terminal
        args.verbose = True

    if args.multithreading:
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_test, driver)
                       for driver in drivers]

            for future in as_completed(futures):
                result = future.result()
                results.append(result.passed)
                process_result(result, xml_file, args.verbose, progress_bar)

    else:
        for driver in drivers:
            result = run_test(driver)
            results.append(result.passed)
            process_result(result, xml_file, args.verbose, progress_bar)

    passing = sum(results)
    total = len(drivers)

    print("\n>> Test Summary: {} Passed, {} Failed, {} Total".format(
        passing, total-passing, total))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "dir",
        nargs="?",
        default=COMPILER_TEST_FOLDER,
        type=Path,
        help="(Optional) paths to the compiler test folders. Use this to select "
        "certain tests. Leave blank to run all tests."
    )

    parser.add_argument(
        "-m", "--multithreading",
        action="store_true",
        default=False,
        help="Use multiple threads to run tests. This will make it faster, "
        "but order is not guaranteed. Should only be used for speed."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output into the terminal. Note that all logs will "
        "be stored automatically into log files regardless of this option."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"BetterTesting {__version__}"
    )
    args = parser.parse_args()

    if os.path.isdir(OUTPUT_FOLDER):
        try:
            shutil.rmtree(OUTPUT_FOLDER)
        except Exception as e:
            print(f"Error removing output folder: {e}")
            exit(1)

    Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

    print("Running make bin/c_compiler...")
    make_result = subprocess.run(["make", "-C", PROJECT_LOCATION, "bin/c_compiler"])
    if make_result.returncode != 0:
        print("Failed to make bin/c_compiler")
        exit(1)

    with JUnitXMLFile(J_UNIT_OUTPUT_FILE) as xml_file:
        run_tests(args, xml_file)


if __name__ == "__main__":
    try:
        main()
    finally:
        if sys.stdout.isatty():
            # This solves dodgy terminal behaviour on multithreading
            os.system("stty echo")
