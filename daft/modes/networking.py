import ipaddress

from daft.modes.common import local_execute


def get_network_from_ip(ip):
    ip_interface = ipaddress.ip_interface(f'{ip}/255.255.255.0')
    network_ip = ip_interface.network.network_address

    return network_ip


def fix_dut_routing(dut_ip, bbb_ip):
    """
    Check if routing exists to the DUT, if not - add ones

    Args:
        dut_ip (str): IP of the DUT
        bbb_ip (str): IP of the Beaglebone black
    """
    dut_network = get_network_from_ip(dut_ip)

    routing_exists_command = f"ip route | grep {dut_network} | wc -l"
    routing_exists_stdout = local_execute(routing_exists_command, shell=True)
    no_routing_found = routing_exists_stdout == "0"

    if no_routing_found:
        add_ip_route_command = f"sudo ip route add {dut_network}/24 via {bbb_ip}".split()
        local_execute(add_ip_route_command)


def rewrite_ssh_keys(ip):
    local_execute(f'ssh-keygen -f "/home/hailo/.ssh/known_hosts" -R "{ip}"')
    local_execute(f'ssh-copy-id "{ip}"')
