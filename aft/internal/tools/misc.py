"""
Convenience functions for (unix) command execution
"""

import os
import subprocess as subprocess32
import time


def local_execute(command, timeout=60, ignore_return_codes=None, shell=False):
    """
    Execute a command on local machine. Returns combined stdout and stderr if
    return code is 0 or included in the list 'ignore_return_codes'. Otherwise
    raises a subprocess32 error.
    """
    process = subprocess32.Popen(command, universal_newlines=True, stdout=subprocess32.PIPE, stderr=subprocess32.STDOUT,
                                 shell=shell)

    # Loop until process returns or timeout expires.
    start = time.time()
    output = ""
    return_code = None
    while time.time() < start + timeout and return_code is None:
        return_code = process.poll()
        if return_code is None:
            try:
                output += process.communicate(timeout=1)[0]
            except subprocess32.TimeoutExpired:
                pass

    if return_code is None:
        # Time ran out but the process didn't end.
        raise subprocess32.TimeoutExpired(cmd=command, output=output,
                                          timeout=timeout)

    if ignore_return_codes is None:
        ignore_return_codes = []
    if return_code in ignore_return_codes or return_code == 0:
        return output
    else:
        raise subprocess32.CalledProcessError(returncode=return_code,
                                              cmd=command, output=output)


def subprocess_killer(process):
    """
    A function to kill subprocesses, intended to be used as 'atexit' handle.
    """
    process.terminate()


def inject_ssh_keys_to_image(image_file):
    """
    Find images partition that has /home/root and inject ssh keys to it
    """
    possible_roots = []
    block_size = 512
    output = local_execute(("fdisk -l " + image_file).split())

    for line in output.split("\n"):
        if "Sector size" in line:
            block_size = int(line.split()[-2])
        if "Linux" in line:
            _start_block = int(line.split()[1])
            possible_roots.append(_start_block)

    os.makedirs("daft_tmp_dir")
    auth_keys_path = "daft_tmp_dir/home/root/.ssh/authorized_keys"

    for start_block in possible_roots:
        offset = str(block_size * start_block)
        local_execute(("mount -o loop,offset=" + offset + " " + image_file + " daft_tmp_dir").split())
        if os.path.exists("daft_tmp_dir/home/root"):
            local_execute(("touch " + auth_keys_path).split())
            with open(auth_keys_path, "a") as authorized_keys:
                with open("/root/.ssh/id_rsa_testing_harness.pub", "r")as key:
                    authorized_keys.write("\n" + key.read())
                    authorized_keys.flush()
        local_execute("umount daft_tmp_dir".split())
    os.rmdir("daft_tmp_dir")
