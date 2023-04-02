import hashlib
import os
import sys

import protonvpn_nm_lib

from ...constants import (LOCAL_SERVICE_FILEPATH,
                          SERVICE_TEMPLATE, XDG_CONFIG_SYSTEMD_USER)
from ...enums import DaemonReconnectorEnum
from ...logger import logger
from ..subprocess_wrapper import subprocess


class DbusReconnect:
    DAEMON_COMMANDS = [
        DaemonReconnectorEnum.START,
        DaemonReconnectorEnum.STOP,
        DaemonReconnectorEnum.DAEMON_RELOAD
    ]

    def __init__(self):
        pass
        if not os.path.isdir(XDG_CONFIG_SYSTEMD_USER):
            os.makedirs(XDG_CONFIG_SYSTEMD_USER)

        if (
            not os.path.isfile(LOCAL_SERVICE_FILEPATH)
            or (
                os.path.isfile(LOCAL_SERVICE_FILEPATH)
                and self.get_hash_from_template() != self.get_service_file_hash(LOCAL_SERVICE_FILEPATH) # noqa
            )
        ):
            self.setup_service()

    def setup_service(self):
        """Setup .service file."""
        logger.info("Setting up .service file")
        filled_template = self.__get_filled_service_template()
        with open(LOCAL_SERVICE_FILEPATH, "w") as f:
            f.write(filled_template)

        self.call_daemon_reconnector(DaemonReconnectorEnum.DAEMON_RELOAD)

    def __get_filled_service_template(self):
        root_dir = os.path.dirname(protonvpn_nm_lib.__file__)
        daemon_folder = os.path.join(root_dir, "daemon")
        python_service_path = os.path.join(
            daemon_folder, "dbus_daemon_reconnector.py"
        )
        python_interpreter_path = sys.executable
        exec_start = python_interpreter_path + " " + python_service_path
        filled_template = SERVICE_TEMPLATE.replace("EXEC_START", exec_start)

        return filled_template

    def start_daemon_reconnector(self):
        """Start daemon reconnector."""
        logger.info("Starting daemon reconnector")
        daemon_status = False
        try:
            daemon_status = self.check_daemon_reconnector_status()
        except Exception as e:
            logger.exception("[!] Exception: {}".format(e))

        logger.info("Daemon status: {}".format(daemon_status))

        if daemon_status:
            return

        self.daemon_reconnector_manager(DaemonReconnectorEnum.START, daemon_status)

    def stop_daemon_reconnector(self):
        """Stop daemon reconnector."""
        logger.info("Stopping daemon reconnector")
        daemon_status = False
        try:
            daemon_status = self.check_daemon_reconnector_status()
        except Exception as e:
            logger.exception("[!] Exception: {}".format(e))

        if not daemon_status:
            return

        logger.info("Daemon status: {}".format(daemon_status))
        self.daemon_reconnector_manager(DaemonReconnectorEnum.STOP, daemon_status)

    def daemon_reconnector_manager(self, callback_type, daemon_status):
        """Start/stop daemon reconnector.

        Args:
            callback_type (DaemonReconnectorEnum): enum
            daemon_status (int): 1 or 0
        """
        logger.info(
            "Managing daemon: cb_type-> \"{}\"; ".format(callback_type)
            + "daemon_status -> \"{}\"".format(daemon_status)
        )
        if callback_type == DaemonReconnectorEnum.START and not daemon_status:
            logger.info("Calling daemon reconnector for start")
            self.call_daemon_reconnector(callback_type)
        elif callback_type == DaemonReconnectorEnum.STOP and daemon_status:
            logger.info("Calling daemon reconnector for stop")
            self.call_daemon_reconnector(callback_type)
            try:
                daemon_status = self.check_daemon_reconnector_status()
            except Exception as e:
                logger.exception("[!] Exception: {}".format(e))
            else:
                logger.info(
                    "Daemon status after stopping: {}".format(daemon_status)
                )
        else:
            logger.info("Something went wrong with the daemon reconnector")

    def check_daemon_reconnector_status(self):
        """Checks the status of the daemon reconnector and starts the process
        only if it's not already running.

        Returns:
            int: indicates the status of the daemon process
        """
        logger.info("Checking daemon reconnector status")
        check_daemon = subprocess.run(
            ["systemctl", "status", "--user", "protonvpn_reconnect"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        decoded_stdout = check_daemon.stdout.decode()
        if (
            check_daemon.returncode == 3
        ):
            # Not running
            return 0
        elif (
            check_daemon.returncode == 0
        ):
            # Already running
            return 1
        else:
            # Service threw an exception
            raise Exception(
                "[!] An error occurred while checking for Proton VPN "
                + "reconnector service: "
                + "(Return code: {}; Exception: {} {})".format(
                    check_daemon.returncode, decoded_stdout,
                    check_daemon.stderr.decode().strip("\n")
                )
            )

    def call_daemon_reconnector(
        self, command
    ):
        """Makes calls to daemon reconnector to either
        start or stop the process.

        Args:
            command (string): to either start or stop the process
        """
        logger.info("Calling daemon reconnector")
        if command not in self.DAEMON_COMMANDS:
            raise Exception("Invalid daemon command \"{}\"".format(command))

        call_daemon = subprocess.run(
            ["systemctl", command.value, "--user", "protonvpn_reconnect"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if command == DaemonReconnectorEnum.DAEMON_RELOAD:
            call_daemon = subprocess.run(
                [
                    "systemctl",
                    "--user",
                    DaemonReconnectorEnum.DAEMON_RELOAD.value
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        decoded_stdout = call_daemon.stdout.decode()
        decoded_stderr = call_daemon.stderr.decode().strip("\n")

        if not call_daemon.returncode == 0:
            msg = "[!] An error occurred while {}ing Proton VPN "\
                "reconnector service: {} {}".format(
                    command,
                    decoded_stdout,
                    decoded_stderr
                )
            logger.error(msg)

    def get_hash_from_template(self):
        filled_template = self.__get_filled_service_template()
        template_hash = hashlib.sha256(
            filled_template.encode('ascii')
        ).hexdigest()
        logger.info("Template hash \"{}\"".format(template_hash))
        return template_hash

    def get_service_file_hash(self, file):
        # A arbitrary (but fixed) buffer
        # size (change accordingly)
        # 65536 = 65536 bytes = 64 kilobytes
        BUF_SIZE = 65536
        sha256 = hashlib.sha256()
        with open(file, "rb") as f:
            while True:
                # reading data = BUF_SIZE from
                # the file and saving it in a
                # variable
                data = f.read(BUF_SIZE)
                # True if eof = 1
                if not data:
                    break
                # Passing that data to that sh256 hash
                # function (updating the function with
                # that data)
                sha256.update(data)

        # sha256.hexdigest() hashes all the input
        # data passed to the sha256() via sha256.update()
        # Acts as a finalize method, after which
        # all the input data gets hashed hexdigest()
        # hashes the data, and returns the output
        # in hexadecimal format
        generated_hash = sha256.hexdigest()
        logger.info("Generated hash at runtime \"{}\"".format(generated_hash))
        return generated_hash
