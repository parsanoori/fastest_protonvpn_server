from . import exceptions
from .core.country import Country
from .core.environment import ExecutionEnvironment
from .core.utilities import Utilities
from .core.report import BugReport
from .enums import (ConnectionMetadataEnum, ConnectionTypeEnum, FeatureEnum,
                    MetadataEnum, ServerTierEnum, KillswitchStatusEnum)
from .logger import logger


class ProtonVPNClientAPI:
    def __init__(self):
        # The constructor should be where you initialize
        # the environment and it's parameter
        self._env = ExecutionEnvironment()
        self._country = Country()
        self._utils = Utilities
        self._bug_report = BugReport()

    def __set_netzone_address(self):
        new_ip = self._env.api_session.get_location_data().ip
        if new_ip:
            self._env.netzone.address = new_ip

    def login(self, username, password, human_verification=None):
        """Login user with provided username and password.
        If login is unsuccessful, an exception will be thrown.

        Args:
            username (string)
            password (string)
            human_verification (optional; list|tuple)
        """
        self._utils.ensure_internet_connection_is_available()
        self._env.api_session.authenticate(username, password, human_verification)
        self.__set_netzone_address()

    def logout(self):
        """Logout user and delete current user session."""
        self._env.api_session.logout()
        try:
            self.disconnect()
        except exceptions.ConnectionNotFound:
            pass

    def connect(self):
        """Connect to Proton VPN.

        Should be user either after setup_connection() or
        setup_reconnect().
        """
        connect_result = self._env.connection_backend.connect()
        self._env.connection_metadata.save_connect_time()
        return connect_result

    def disconnect(self):
        """Disconnect from Proton VPN"""
        self._env.connection_backend.disconnect()
        if self._env.settings.killswitch != KillswitchStatusEnum.HARD:
            self.__set_netzone_address()

    def setup_connection(
            self,
            connection_type,
            connection_type_extra_arg=None,
            protocol=None
    ):
        """Setup and configure VPN connection prior
        calling connect().

        Args:
            connection_type (ConnectionTypeEnum):
                selected connection type
            connection_type_extra_arg (string):
                (optional) should be used only when
                connecting directly to a specific server
                with ConnectionTypeEnum.SERVERNAME or when
                connecting to a specific country with
                ConnectionTypeEnum.COUNTRY.
            optional protocol (string):
                (optional) if None, then protocol will be fetched
                from user configurations.

        Returns:
            dict: dbus response
        """
        logger.info("Setting up connection")
        if not self._env.api_session.is_valid:
            raise exceptions.UserSessionNotFound(
                "User session was not found, please login first."
            )
        self._utils.ensure_internet_connection_is_available()

        (
            _connection_type,
            _connection_type_extra_arg,
            _protocol
        ) = self._utils.parse_user_input(
            {
                "connection_type": connection_type,
                "connection_type_extra_arg": connection_type_extra_arg,
                "protocol": protocol,
            }
        )

        if self._env.settings.killswitch != KillswitchStatusEnum.HARD:
            self.__set_netzone_address()

        connect_configurations = {
            ConnectionTypeEnum.FREE: self.config_for_fastest_free_server,
            ConnectionTypeEnum.SERVERNAME:
                self.config_for_server_with_servername,
            ConnectionTypeEnum.FASTEST: self.config_for_fastest_server,
            ConnectionTypeEnum.RANDOM: self.config_for_random_server,
            ConnectionTypeEnum.COUNTRY:
                self.config_for_fastest_server_in_country,
            ConnectionTypeEnum.SECURE_CORE:
                self.config_for_fastest_server_with_feature,
            ConnectionTypeEnum.PEER2PEER:
                self.config_for_fastest_server_with_feature,
            ConnectionTypeEnum.TOR: self.config_for_fastest_server_with_feature
        }

        server = connect_configurations[connection_type](
            _connection_type_extra_arg,
        )
        physical_server = server.get_random_physical_server()
        self._env.api_session.servers.match_server_domain(physical_server)

        openvpn_username = self._env.api_session.vpn_username
        if physical_server.label:
            openvpn_username = openvpn_username + "+b:" + physical_server.label
            logger.info("Appended server label.")

        data = {
            "domain": physical_server.domain,
            "entry_ip": physical_server.entry_ip,
            "servername": server.name,
            "credentials": {
                "ovpn_username": openvpn_username,
                "ovpn_password": self._env.api_session.vpn_password
            },
        }
        self._env.connection_metadata.save_servername(server.name)
        self._env.connection_metadata.save_protocol(_protocol)
        self._env.connection_metadata.save_display_server_ip(
            physical_server.exit_ip
        )
        self._env.connection_metadata.save_server_ip(physical_server.entry_ip)

        logger.info("Stored metadata to file")
        configuration = physical_server.get_configuration(_protocol)
        logger.info("Received configuration object")
        self._env.connection_backend.vpn_configuration = configuration

        logger.info("Setting up {}".format(server.name))
        self._env.connection_backend.setup(**data)
        return server

    def config_for_fastest_free_server(self, *_):
        """Select fastest server.

        Returns:
            LogicalServer
        """
        return self.config_for_fastest_free_servers(1)[0]

    def config_for_fastest_free_servers(self, n):
        """Select fastest server.

        Returns:
            LogicalServer
        """
        secure_core = bool(self._env.settings.secure_core.value)
        logger.info("Fastest with secure core \"{}\"".format(secure_core))
        try:
            return self._env.api_session.servers.filter(
                lambda server: server.tier == ServerTierEnum.FREE.value
            ).get_fastest_servers(n)
        except exceptions.EmptyServerListError:
            raise exceptions.FastestServerNotFound(
                "Fastest server could not be found."
            )

    def config_for_fastest_servers_in_country(self, country, n):
        """Select fastest server.

        Returns:
            LogicalServer
        """
        secure_core = bool(self._env.settings.secure_core.value)
        logger.info("Fastest with secure core \"{}\"".format(secure_core))
        try:
            return self._env.api_session.servers.filter(
                lambda server: server.entry_country == country and server.tier == ServerTierEnum.FREE.value
            ).get_fastest_servers(n)
        except exceptions.EmptyServerListError:
            raise exceptions.FastestServerNotFound(
                "Fastest server could not be found."
            )

    def config_for_fastest_server(self, *_):
        """Select fastest server.

        Returns:
            LogicalServer
        """
        secure_core = bool(self._env.settings.secure_core.value)
        logger.info("Fastest with secure core \"{}\"".format(secure_core))
        try:
            return self._env.api_session.servers.filter(
                lambda server:
                server.tier <= ExecutionEnvironment().api_session.vpn_tier
                and (
                        secure_core
                        and FeatureEnum.SECURE_CORE in server.features
                ) or (
                        not secure_core
                        and FeatureEnum.SECURE_CORE not in server.features
                        and FeatureEnum.TOR not in server.features
                )
            ).get_fastest_server()
        except exceptions.EmptyServerListError:
            raise exceptions.FastestServerNotFound(
                "Fastest server could not be found."
            )

    def config_for_fastest_server_in_country(self, country_code):
        """Select server by country code.

        Returns:
            LogicalServer
        """
        secure_core = bool(self._env.settings.secure_core.value)
        logger.info("Country with secure core \"{}\"".format(secure_core))
        try:
            return self._env.api_session.servers.filter(
                lambda server:
                server.tier <= ExecutionEnvironment().api_session.vpn_tier
                and server.exit_country.lower() == country_code.lower()
                and (
                        (
                                secure_core
                                and FeatureEnum.SECURE_CORE in server.features
                        ) or (
                                not secure_core
                                and FeatureEnum.SECURE_CORE not in server.features
                                and FeatureEnum.TOR not in server.features
                        )
                )
            ).get_fastest_server()
        except exceptions.EmptyServerListError:
            raise exceptions.FastestServerInCountryNotFound(
                "Fastest server could not be found."
            )

    def config_for_fastest_server_with_feature(self, features):
        """Select server by specified feature.

        By transforming features into a list and generating possible_features
        we can easily implement the possibility to specify multiple features
        to connect.

        Returns:
            LogicalServer
        """
        connection_type_translation = {
            ConnectionTypeEnum.SECURE_CORE: FeatureEnum.SECURE_CORE,
            ConnectionTypeEnum.PEER2PEER: FeatureEnum.P2P,
            ConnectionTypeEnum.TOR: FeatureEnum.TOR,
        }
        feature = [features]
        possible_features = [
            connection_type_translation[f]
            for f in feature
            if f in connection_type_translation
        ]
        try:
            return self._env.api_session.servers.filter(
                lambda server: (
                        server.tier <= ExecutionEnvironment().api_session.vpn_tier
                        and all(
                    chosen_feature
                    in server.features
                    for chosen_feature
                    in possible_features
                )
                )
            ).get_fastest_server()
        except exceptions.EmptyServerListError:
            raise exceptions.FeatureServerNotFound(
                "Server with specified feature could not be found.\n"
                "Either the server went into maintenance or "
                "you don't have access to the server with your plan."
            )

    def config_for_server_with_servername(self, servername):
        """Select server by servername.

        Returns:
            LogicalServer
        """
        try:
            return self._env.api_session.servers.filter(
                lambda server:
                server.tier <= ExecutionEnvironment().api_session.vpn_tier
                and server.name.lower() == servername.lower()  # noqa
            ).get_fastest_server()
        except exceptions.EmptyServerListError:
            raise exceptions.ServernameServerNotFound(
                "The specified servername could not be found.\n"
                "Either the server went into maintenance or "
                "you don't have access to the server with your plan."
            )

    def config_for_random_server(self, *_):
        """Select server for random connection.

        Returns:
            LogicalServer
        """
        try:
            return self._env.api_session.servers.get_random_server()
        except exceptions.EmptyServerListError:
            raise exceptions.RandomServerNotFound(
                "Random server could not be found."
            )

    def setup_reconnect(self):
        """Setup and configure VPN connection to
        a previously connected server.

        Should be called before calling connect().
        """
        logger.info("Gathering data for recconnect to previous server")
        last_connection_metadata = self._env.connection_metadata \
            .get_connection_metadata(
            MetadataEnum.LAST_CONNECTION
        )

        try:
            previous_server = last_connection_metadata[
                ConnectionMetadataEnum.SERVER.value
            ]
        except KeyError:
            logger.error(
                "File exists but servername field is missing, exitting"
            )
            raise Exception(
                "No previous connection data was found, "
                "please first connect to a server."
            )

        try:
            protocol = last_connection_metadata[
                ConnectionMetadataEnum.PROTOCOL.value
            ]
        except KeyError:
            protocol = None

        logger.info(
            "Gathered all data from previous connection \"{}\". "
            "Proceeding to setup connection.".format(
                previous_server
            )
        )

        return self.setup_connection(
            connection_type=ConnectionTypeEnum.SERVERNAME,
            connection_type_extra_arg=previous_server,
            protocol=protocol
        )

    def check_session_exists(self):
        """Checks if session exists.

        Returns:
            bool
        """
        return self._env.api_session.is_valid

    def get_settings(self):
        """Get user settings object."""
        return self._env.settings

    def get_session(self):
        """Get user session object."""
        return self._env.api_session

    def get_country(self):
        """Get country object."""
        return self._country

    def get_connection_metadata(self):
        """Get metadata of an active Proton VPN connection.

        Returns:
            dict
        """
        return self._env.connection_metadata.get_connection_metadata(
            MetadataEnum.CONNECTION
        )

    def get_non_active_protonvpn_connection(self):
        """Get non active Proton VPN connection object.

        Args:
            nm_connection_type (NetworkManagerConnectionTypeEnum)
        Returns:
            VPN connection
        """
        return self._env.connection_backend \
            .get_non_active_protonvpn_connection()

    def get_active_protonvpn_connection(self):
        """Get active Proton VPN connection object.

        Args:
            nm_connection_type (NetworkManagerConnectionTypeEnum)
        Returns:
            VPN connection
        """
        return self._env.connection_backend \
            .get_active_protonvpn_connection()

    def ensure_connectivity(self):
        """Check for connectivity.

        1) It checks if there is internet connection
        2) It checks if API can be reached
        """
        self._utils.ensure_internet_connection_is_available()

    def get_bug_report(self):
        """Get bug report object."""
        return self._bug_report


protonvpn = ProtonVPNClientAPI()  # noqa
