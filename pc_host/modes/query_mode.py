import json
from pathlib import Path

from pc_host.modes.common import reserve_device, remote_execute
from pc_host.modes.mode import Mode


class QueryMode(Mode):
    @classmethod
    def name(cls):
        return 'query'

    @classmethod
    def add_mode_arguments(cls, parser):
        parser.add_argument('results', help="Path to store the results of the query in")
        parser.add_argument('--ip', action="store_true", default=False, help="Query the IP of the machine")

    def __init__(self, args, config):
        self._args = args
        self._config = config

    def execute(self):
        queried_data = dict()

        with reserve_device(self._args, self._config) as beaglebone_dut:
            queried_data['IP'] = beaglebone_dut.wait_for_responsive_ip()

        Path(self._args.results).write_text(json.dumps(queried_data))

        return 0

    def _execute_get_ip(self, bb_dut):
        dut = bb_dut["device_type"].lower()
        command = f"aft {dut} _ --get-ip"
        output = remote_execute(bb_dut["bb_ip"], command=command.split(), timeout=1200, config=self._config)

        return output
