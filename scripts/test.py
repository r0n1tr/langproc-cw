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
import queue
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from progress_bar import ProgressBar


# "File" will suggest the absolute path to the file, including the extension.
SCRIPT_LOCATION = Path(__file__).resolve().parent
PROJECT_LOCATION = SCRIPT_LOCATION.joinpath("..").resolve()
OUTPUT_FOLDER = PROJECT_LOCATION.joinpath("bin/output").resolve()
J_UNIT_OUTPUT_FILE = PROJECT_LOCATION.joinpath(
    "bin/junit_results.xml").resolve()
COMPILER_TEST_FOLDER = PROJECT_LOCATION.joinpath("compiler_tests").resolve()


def fail_testcase(
    init_message: tuple[str, str],
    message: str,
    log_queue: queue.Queue
):
    """
    Updates the log queue with the JUnit and the stdout fail message.
    """
    init_print_message, init_xml_message = init_message
    print_message = message
    xml_message = (
        f'<error type="error" message="{message}">{message}</error>\n'
        '</testcase>\n'
    )
    log_queue.put(
        (
            init_print_message + print_message,
            init_xml_message + xml_message,
            False,
        )
    )


def run_test(driver: Path, log_queue: queue.Queue) -> bool:
    """
    Run an instance of a test case.

    Returns:
    True if passed, False otherwise. This is to increment the pass counter.
    """

    # Replaces example_driver.c -> example.c
    new_name = driver.stem.replace('_driver', '') + '.c'
    to_assemble = os.path.relpath(driver.parent.joinpath(new_name), PROJECT_LOCATION)
    init_message = (str(to_assemble) + "\n",
                    f'<testcase name="{to_assemble}">\n')

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
        fail_testcase(
            init_message,
            result.stdout,
            log_queue
        )
        return False

    init_print_message, init_xml_message = init_message
    log_queue.put(
        (
            init_print_message + "\t> Pass\n",
            init_xml_message + "</testcase>\n",
            True,
        )
    )
    return True


def empty_log_queue(
    log_queue: queue.Queue,
    verbose: bool = False,
    progress_bar: ProgressBar = None
):
    while not log_queue.empty():
        print_msg, xml_message, test_passed = log_queue.get()

        with open(J_UNIT_OUTPUT_FILE, "a") as xml_file:
            xml_file.write(xml_message)

        if verbose:
            print(print_msg)
            continue

        if not progress_bar:
            continue

        if test_passed:
            progress_bar.test_passed()
        else:
            progress_bar.test_failed()


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

    try:
        shutil.rmtree(OUTPUT_FOLDER)
    except Exception as e:
        print(f"Error: {e}")

    Path(OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

    subprocess.run(["make", "-C", PROJECT_LOCATION, "bin/c_compiler"])

    with open(J_UNIT_OUTPUT_FILE, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<testsuite name="Integration test">\n')

    drivers = list(Path(args.dir).rglob("*_driver.c"))
    drivers = sorted(drivers, key=lambda p: (p.parent.name, p.name))
    log_queue = queue.Queue()
    results = []

    progress_bar = None
    if sys.stdout.isatty():
        progress_bar = ProgressBar(len(drivers))
    else:
        # Force verbose mode when not a terminal
        args.verbose = True

    if args.multithreading:
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(run_test, driver, log_queue)
                       for driver in drivers]

            for future in as_completed(futures):
                results.append(future.result())
                empty_log_queue(log_queue, args.verbose, progress_bar)

    else:
        for driver in drivers:
            result = run_test(driver, log_queue)
            results.append(result)
            empty_log_queue(log_queue, args.verbose, progress_bar)

    passing = sum(results)
    total = len(drivers)

    with open(J_UNIT_OUTPUT_FILE, "a") as f:
        f.write('</testsuite>\n')

    print("\n>> Test Summary: {} Passed, {} Failed".format(
        passing, total-passing))


if __name__ == "__main__":
    try:
        main()
    finally:
        if sys.stdout.isatty():
            # This solves dodgy terminal behaviour on multithreading
            os.system("stty echo")
