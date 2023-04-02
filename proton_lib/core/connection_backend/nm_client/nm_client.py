

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from .... import exceptions
from ....constants import VIRTUAL_DEVICE_NAME
from ....enums import (ConnectionStartStatusEnum, KillSwitchActionEnum,
                       KillswitchStatusEnum, NetworkManagerConnectionTypeEnum,
                       ProtocolImplementationEnum, VPNConnectionStateEnum)
from ....logger import logger
from ...dbus.dbus_reconnect import DbusReconnect
from ...environment import ExecutionEnvironment
from ..connection_backend import ConnectionBackend
from .monitor_vpn_connection_start import MonitorVPNConnectionStart
from .nm_client_mixin import NMClientMixin
from .plugin import NMPlugin


class NetworkManagerClient(ConnectionBackend, NMClientMixin):
    client = "networkmanager"

    def __init__(self, daemon_reconnector=None):
        super().__init__()
        self.__virtual_device_name = VIRTUAL_DEVICE_NAME
        self.__vpn_configuration = None
        self.daemon_reconnector = DbusReconnect()

    @property
    def vpn_configuration(self):
        """Get certificate filepath property."""
        return self.__vpn_configuration

    @vpn_configuration.setter
    def vpn_configuration(self, new_value):
        """Set property of virtual device tunnel."""
        self.__vpn_configuration = new_value

    @property
    def virtual_device_name(self):
        return self.__virtual_device_name

    def setup(self, *args, **kwargs):
        """Setup VPN connection.

        This should be used only if there are required steps before
        starting the connection.
        """
        logger.info("Adding VPN connection")

        connection, protocol_implementation = NMPlugin.import_vpn_config(
            self.vpn_configuration
        )

        try:
            self.disconnect()
        except: # noqa
            pass

        credentials = kwargs.get("credentials")
        connection_data = {
            "user_data": {
                "username": credentials.get("ovpn_username"),
                "password": credentials.get("ovpn_password")
            },
            "domain": kwargs.get("domain"),
            "servername": kwargs.get("servername"),
            "virtual_device_name": self.virtual_device_name,
            "vpn_configuration": self.vpn_configuration,
        }

        if protocol_implementation == ProtocolImplementationEnum.OPENVPN:
            from .openvpn.configure_openvpn_connection import \
                ConfigureOpenVPNConnection
            ConfigureOpenVPNConnection.configure_connection(
                connection, connection_data
            )
        else:
            raise NotImplementedError("Other implementationsa are not ready")

        self._pre_setup_connection(kwargs.get("entry_ip"))
        self._add_connection_async(connection)

    def connect(self, attempt_reconnect=False):
        """Connect to VPN.

        Returns status of connection in dict form.
        """
        logger.info("Starting VPN connection")

        connection = self.get_non_active_protonvpn_connection()
        self.ensure_protovnpn_connection_exists(connection)
        self._start_connection_async(connection)

        DBusGMainLoop(set_as_default=True)
        dbus_loop = GLib.MainLoop()

        response = {}
        MonitorVPNConnectionStart(
            dbus_loop,
            response
        )
        dbus_loop.run()
        if response[ConnectionStartStatusEnum.STATE] != VPNConnectionStateEnum.IS_ACTIVE:
            logger.info("Unable to connect to VPN")
            env = ExecutionEnvironment()
            logger.info("Restoring kill switch to previous state")
            if env.settings.killswitch == KillswitchStatusEnum.HARD:
                env.killswitch.update_from_user_configuration_menu(KillswitchStatusEnum.HARD)
            else:
                env.killswitch.update_from_user_configuration_menu(KillswitchStatusEnum.DISABLED)
                env.ipv6leak.remove_leak_protection()

            try:
                self.disconnect()
            except: # noqa
                pass

            try:
                self.ensure_protovnpn_connection_exists(connection)
            except exceptions.ConnectionNotFound:
                pass

            logger.info("Ensure that account has expected values")
            env.accounting.ensure_accounting_has_expected_values()

        else:
            self.daemon_reconnector.start_daemon_reconnector()

        return response

    def disconnect(self):
        """Disconnect form VPN connection."""
        connection = self.get_active_protonvpn_connection()
        try:
            self.ensure_protovnpn_connection_exists(connection)
        except exceptions.ConnectionNotFound:
            connection = self.get_non_active_protonvpn_connection()
            self.ensure_protovnpn_connection_exists(connection)

        self._remove_connection_async(connection)
        self._post_disconnect()

    def get_non_active_protonvpn_connection(self):
        """Get non active VPN connection.

        A connection can be existent but not active, thus
        it should be gettable.
        """
        return self.__get_protonvpn_connection(
            NetworkManagerConnectionTypeEnum.ALL
        )

    def get_active_protonvpn_connection(self):
        "Get active VPN connection."
        return self.__get_protonvpn_connection(
            NetworkManagerConnectionTypeEnum.ACTIVE
        )

    def ensure_protovnpn_connection_exists(self, connection):
        if not connection:
            raise exceptions.ConnectionNotFound(
                "ProtonVPN connection was not found"
            )

    def __get_protonvpn_connection(
        self, network_manager_connection_type
    ):
        """Get ProtonVPN connection.

        Args:
            connection_type (NetworkManagerConnectionTypeEnum):
                can either be:
                ALL - for all connections
                ACTIVE - only active connections

        Returns:
            if:
            - NetworkManagerConnectionTypeEnum.ALL: NM.RemoteConnection
            - NetworkManagerConnectionTypeEnum.ACTIVE: NM.ActiveConnection
        """
        logger.info("Getting VPN from \"{}\" connections".format(
            network_manager_connection_type
        ))
        protonvpn_connection = False

        connection_types = {
            NetworkManagerConnectionTypeEnum.ALL: self.nm_client.get_connections, # noqa
            NetworkManagerConnectionTypeEnum.ACTIVE: self.nm_client.get_active_connections # noqa
        }

        connections_list = connection_types[network_manager_connection_type]()

        for conn in connections_list:
            if conn.get_connection_type() == "vpn":
                conn_for_vpn = conn
                # conn can be either NM.RemoteConnection
                # or NM.VPNConnection
                if (
                    network_manager_connection_type
                    == NetworkManagerConnectionTypeEnum.ACTIVE
                ):
                    conn_for_vpn = conn.get_connection()
                    conn = conn_for_vpn

                try:
                    vpn_settings = conn_for_vpn.get_setting_vpn()
                except AttributeError:
                    return False

                if (
                    vpn_settings.get_data_item("dev")
                    == self.virtual_device_name
                ):
                    protonvpn_connection = conn
                    break
        logger.info(
            "VPN connection: {}".format(
                None if not protonvpn_connection else protonvpn_connection
            )
        )
        return protonvpn_connection

    # TO-DO: Maybe move code below outside of this class
    def _pre_setup_connection(self, entry_ip):
        env = ExecutionEnvironment()
        settings = env.settings
        killswitch = env.killswitch
        ipv6_lp = env.ipv6leak

        logger.info("Running pre-setup connection.")
        if ipv6_lp.enable_ipv6_leak_protection:
            ipv6_lp.manage(KillSwitchActionEnum.ENABLE)
        if settings.killswitch != KillswitchStatusEnum.DISABLED:
            killswitch.manage(
                KillSwitchActionEnum.PRE_CONNECTION,
                server_ip=entry_ip
            )

    # TO-DO: Maybe move code below outside of this class
    def _post_disconnect(self):
        logger.info("Running post disconnect.")
        env = ExecutionEnvironment()
        settings = env.settings
        killswitch = env.killswitch
        ipv6_lp = env.ipv6leak

        self.daemon_reconnector.stop_daemon_reconnector()
        ipv6_lp.manage(KillSwitchActionEnum.DISABLE)
        if settings.killswitch == KillswitchStatusEnum.SOFT:
            killswitch.manage(KillSwitchActionEnum.DISABLE)
