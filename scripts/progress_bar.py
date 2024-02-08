import os

class ProgressBar:
    """
    Creates a CLI progress bar that can update itself, provided nothing gets
    in the way.

    Parameters:
    - total_tests: the length of the progress bar.
    """

    def __init__(self, total_tests):
        self.total_tests = total_tests
        self.passed = 0
        self.failed = 0

        _, max_line_length = os.popen("stty size", "r").read().split()
        self.max_line_length = min(
            int(max_line_length) - len("Running Tests []"),
            80 - len("Running Tests []")
        )

        # Initialize the lines for the progress bar and stats
        print("Running Tests [" + " " * self.max_line_length + "]")
        print("Pass: 0 | Fail: 0 | Remaining: {}".format(total_tests))
        print("See logs for more details (use -v for verbose output).")

        # Initialize the progress bar
        self.update()

    def update(self):
        remaining_tests = self.total_tests - (self.passed + self.failed)
        progress_bar = ""

        if self.total_tests == 0:
            prop_passed = 0
            prop_failed = 0
        else:
            prop_passed = round(
                self.passed / self.total_tests * self.max_line_length)
            prop_failed = round(
                self.failed / self.total_tests * self.max_line_length
            )

        # Ensure at least one # for passed and failed, if they exist
        prop_passed = max(prop_passed, 1) if self.passed > 0 else 0
        prop_failed = max(prop_failed, 1) if self.failed > 0 else 0

        remaining = self.max_line_length - prop_passed - prop_failed

        progress_bar += '\033[92m#\033[0m' * prop_passed    # Green
        progress_bar += '\033[91m#\033[0m' * prop_failed    # Red
        progress_bar += ' ' * remaining                     # Empty space

        # Move the cursor up 3 lines, to the beginning of the progress bar
        print("\033[3A\r", end='')

        print("Running Tests [{}]".format(progress_bar))
        # Space is left there intentionally to flush out the command line
        print("Pass: {:2} | Fail: {:2} | Remaining: {:2} ".format(
            self.passed, self.failed, remaining_tests))
        print("See logs for more details (use -v for verbose output).")

    def update_with_value(self, passed: bool):
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        self.update()
