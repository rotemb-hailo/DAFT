"""
Basic Test Case class.
"""
import re
import subprocess as subprocess32

import aft.errors as errors
from aft.logger import Logger as logger
from aft.testcase import TestCase


class BasicTestCase(TestCase):
    """
    Simple Test Case executor.
    """

    def __init__(self, config):
        super(BasicTestCase, self).__init__(config)
        self.output = None
        self.parameters = config["parameters"]
        self.pass_regex = config["pass_regex"]

    def run(self, device):
        self.run_remote_command(device)

    def run_local_command(self, timeout=1800):
        """
        Executes a command locally, on the test harness.
        """
        command = "timeout " + str(timeout) + " " + self.parameters
        process = subprocess32.Popen(command.split(),
                                     universal_newlines=True,
                                     stderr=subprocess32.STDOUT,
                                     stdout=subprocess32.PIPE)
        self.output = process.communicate()[0]
        logger.debug("Output return code in basictestcase.run_local_command():" + str(process.returncode))
        logger.debug("And output: " + self.output)

        if process.returncode == 124 or process.returncode == 128 + 9:
            raise errors.AFTTimeoutError("Test cases failed to complete in " + str(timeout) + " seconds")
        return True

    def run_remote_command(self, device):
        """
        Executes a command remotely, on the device.
        """
        self.output = device.execute(self.parameters.split(), timeout=120)
        logger.info("Command: " + str(self.parameters) + "\nresult: " + str(self.output) + ".")
        return self._check_for_success()

    def _check_for_success(self):
        """
        Test for success.
        """
        logger.info("self.output " + self.output)
        if self.output == None or self.output.returncode != 0:
            logger.info("Test Failed: returncode " + str(self.output.returncode))
            if self.output != None:
                logger.info("stdout:\n" + str(self.output.stdoutdata))
                logger.info("stderr:\n" + str(self.output.stderrdata))
        elif self.pass_regex == "":
            logger.info("Test passed: returncode 0, no pass_regex")
            return True
        else:
            for line in self.output.stdoutdata.splitlines():
                if re.match(self.pass_regex, line) != None:
                    logger.info("Test passed: returncode 0 " +
                                "Matching pass_regex " + str(self.pass_regex))
                    return True
                else:
                    logger.info("Test failed: returncode 0\n" +
                                "But could not find matching pass_regex " +
                                str(self["pass_regex"]))
        return False
