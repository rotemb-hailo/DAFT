"""
Tools for remote controlling a device over ssh.
"""

import os
import subprocess as subprocess32

import aft.internal.tools.misc as tools
from aft.internal.logger import Logger as logger


def _get_proxy_settings():
    """
    Fetches proxy settings from the environment.
    """
    proxy_env_variables = ["http_proxy", "https_proxy", "ftp_proxy", "no_proxy"]
    proxy_env_command = ""
    for var in proxy_env_variables:
        val = os.getenv(var)
        if val is not None and val != "":
            proxy_env_command += "export " + var + '="' + val + '"; '
    return proxy_env_command


def test_ssh_connectivity(remote_ip, timeout=10):
    """
    Test whether remote_ip is accessible over ssh.
    """
    try:
        remote_execute(remote_ip, ["echo", "$?"], connect_timeout=timeout)
        return True
    except subprocess32.CalledProcessError as err:
        logger.warning("Could not establish ssh-connection to " + remote_ip +
                       ". SSH return code: " + str(err.returncode) + ".")
        return False


def push(remote_ip, source, destination, timeout=60, ignore_return_codes=None, user="root"):
    """
    Transmit a file from local 'source' to remote 'destination' over SCP
    """
    scp_args = ["scp", source, user + "@" + str(remote_ip) + ":" + destination]
    return tools.local_execute(scp_args, timeout, ignore_return_codes)


def pull(remote_ip, source, destination, timeout=60, ignore_return_codes=None, user="root"):
    """
    Transmit a file from remote 'source' to local 'destination' over SCP

    Args:
        remote_ip (str): Remote device IP
        source (str): path to file on the remote filesystem
        destination (str): path to the file on local filesystem
        timeout (integer): Timeout in seconds for the operation
        ignore_return_codes (list(integer)):
            List of scp return codes that will be ignored
        user (str): User that will be used with scp

    Returns:
        Scp output on success

    Raises:
        subprocess32.TimeoutExpired:
            If timeout expired
        subprocess32.CalledProcessError:
            If process returns non-zero, non-ignored return code
    """
    scp_args = [
        "scp",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "StrictHostKeyChecking=no",
        user + "@" + str(remote_ip) + ":" + source,
        destination]
    return tools.local_execute(scp_args, timeout, ignore_return_codes)


def remote_execute(remote_ip, command, timeout=60, ignore_return_codes=None,
                   user="root", connect_timeout=15):
    """
    Execute a Bash command over ssh on a remote device with IP 'remote_ip'.
    Returns combines stdout and stderr if there are no errors. On error raises
    subprocess32 errors.
    """
    ssh_args = ["ssh",
                "-i", "".join([os.path.expanduser("~"), "/.ssh/id_rsa_testing_harness"]),
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                "-o", "LogLevel=ERROR",
                "-o", "ConnectTimeout=" + str(connect_timeout),
                user + "@" + str(remote_ip),
                _get_proxy_settings(), ]

    logger.info("Executing " + " ".join(command), filename="ssh.log")

    try:
        return tools.local_execute(ssh_args + command, timeout, ignore_return_codes)
    except subprocess32.CalledProcessError as err:
        logger.error("Command raised exception: " + str(err), filename="ssh.log")
        logger.error("Output: " + str(err.output), filename="ssh.log")
        raise err