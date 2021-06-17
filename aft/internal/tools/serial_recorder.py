"""
A script to record serial output from a tty-device.
"""

import time

import serial

import aft.internal.tools.ansi_parser as ansi_parser
from aft.internal.tools.thread_handler import ThreadHandler


def main(port, rate, output):
    """
    Initialization.
    """
    serial_stream = serial.Serial(port, rate, timeout=0.01, xonxoff=True)
    output_file = open(output, "w")

    print("Starting recording from " + str(port) + " to " + str(output) + ".")
    record(serial_stream, output_file)

    print("Parsing output")
    ansi_parser.parse_file(output)

    serial_stream.close()
    output_file.close()


def record(serial_stream, output):
    """
    Recording loop
    """
    read_buffer = ""

    while True:
        try:
            new_data = serial_stream.read(4096)

            if not sys.version_info[0] == 2:
                new_data.decode("ISO-8859-1")

            read_buffer += new_data
        except serial.SerialException as err:
            # This is a hacky way to fix random, frequent, read errors.
            # May catch more than intended.
            serial_stream.close()
            serial_stream.open()
            continue

        last_newline = read_buffer.rfind("\n")
        if last_newline == -1 and not ThreadHandler.get_flag(ThreadHandler.RECORDERS_STOP):
            continue

        text_batch = read_buffer[0:last_newline + 1]
        read_buffer = read_buffer[last_newline + 1:-1]

        time_now = time.time()
        timed_batch = text_batch.replace("\n", "\n[" + str(time_now) + "] ")
        output.write(timed_batch)
        output.flush()

        if ThreadHandler.get_flag(ThreadHandler.RECORDERS_STOP):
            # Write out the remaining buffer.
            if read_buffer:
                output.write(read_buffer)
            output.flush()
            return


if __name__ == '__main__':
    import sys

    args = sys.argv
    main(args[0], args[1], args[2])
