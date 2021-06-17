"""
Class implementing a Tester interface.
"""

import configparser as ConfigParser
import os
import subprocess
import time

import aft.errors as errors
import aft.testcasefactory
from aft.logger import Logger as logger


class Tester:
    """
    Class representing a Tester interface.
    """

    def __init__(self, device):
        self._device = device
        self.test_cases = []
        self._results = []
        self._start_time = None
        self._end_time = None

        test_plan_name = device.test_plan
        test_plan_file = os.path.join("/etc/aft/test_plan/", device.test_plan + ".cfg")
        test_plan_config = ConfigParser.SafeConfigParser()
        test_plan_config.read(test_plan_file)

        if len(test_plan_config.sections()) == 0:
            raise errors.AFTConfigurationError("Test plan " + str(test_plan_name) +
                                               " (" + str(test_plan_file) + ") doesn't " +
                                               "have any test cases. Does the file exist?")

        for test_case_name in test_plan_config.sections():
            test_case_config = dict(test_plan_config.items(test_case_name))
            test_case_config["name"] = test_case_name
            test_case = aft.testcasefactory.build_test_case(test_case_config)
            self.test_cases.append(test_case)

        logger.info("Built test plan with " + str(len(self.test_cases)) + " test cases.")

    def execute(self):
        """
        Set values to default and execute the test plan.
        """

        # Set the Beaglebones gpio20 values to default
        logger.info("Setting Beaglebone gpio testing pin back to default")
        subprocess.call("echo 20 > /sys/class/gpio/export", shell=True)
        subprocess.call("echo in > /sys/class/gpio/gpio20/direction", shell=True)

        logger.info("Executing the test plan")
        self._start_time = time.time()
        logger.info("Test plan start time: " + str(self._start_time))

        for index, test_case in enumerate(self.test_cases, 1):
            logger.info("Executing test case " + str(index) + " of " + str(self.test_cases))
            test_case.execute(self._device)
            self._results.append(test_case.result)

        self._end_time = time.time()
        logger.info("Test plan end time: " + str(self._end_time))
        self._save_test_results()

    def _results_to_xunit(self):
        """
        Return test results formatted in xunit XML
        """
        xml = [('<?xml version="1.0" encoding="utf-8"?>\n'
                '<testsuite errors="0" failures="{0}" '
                .format(len([test_case for test_case in self.test_cases
                             if not test_case.result])) +
                'name="aft.{0}.{1}" skips="0" '
                .format(time.strftime("%Y%m%d%H%M%S",
                                      time.localtime(self._start_time)),
                        os.getpid()) +
                'tests="{0}" time="{1}">\n'
                .format(len(self._results),
                        self._end_time - self._start_time))]
        for test_case in self.test_cases:
            xml.append(test_case.xunit_section)
        xml.append('</testsuite>\n')
        return "".join(xml)

    def get_results_location(self):
        """
        Returns the file path of the results xml-file.
        """
        return os.path.join(os.getcwd(), "results.xml")

    def _save_test_results(self):
        """
        Store the test results.
        """
        logger.info("Storing the test results.")
        xunit_results = self._results_to_xunit()
        results_filename = self.get_results_location()
        with open(results_filename, "w") as results_file:
            results_file.write(xunit_results)
        logger.info("Results saved to " + str(results_filename) + ".")

    def get_results(self):
        return self._results

    def get_results_str(self):
        arr = []
        for test_case in self.test_cases:
            arr.append(test_case.xunit_section)
        return "".join(arr)
