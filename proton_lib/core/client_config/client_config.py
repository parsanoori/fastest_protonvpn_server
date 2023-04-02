import json
import time


class ClientConfig:
    def __init__(self):
        self.__data = None
        self.__feature_flags = None

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, newdata):
        self.__data = newdata
        self.__feature_flags = ClientFeatureConfig(newdata.get("FeatureFlags", None))

    @property
    def default_udp_ports(self):
        return self.__data["OpenVPNConfig"]["DefaultPorts"]["UDP"]

    @property
    def default_tcp_ports(self):
        return self.__data["OpenVPNConfig"]["DefaultPorts"]["TCP"]

    @property
    def hole_ips(self):
        return self.__data["HolesIPs"]

    @property
    def refresh_interval(self):
        return self.__data["ServerRefreshInterval"]

    @property
    def features(self):
        return self.__feature_flags

    def json_dumps(self):
        return json.dumps(self.data)

    def json_loads(self, data):
        self.data = json.loads(data)

    def update_client_config_data(self, data):
        assert "Code" in data
        assert "OpenVPNConfig" in data

        if data["Code"] != 1000:
            raise ValueError("Invalid data with code != 1000")

        data["ClientConfigUpdateTimestamp"] = time.time()
        self.data = data

    @property
    def client_config_timestamp(self):
        try:
            return self.data.get("ClientConfigUpdateTimestamp", 0.)
        except AttributeError:
            return 0.0


class ClientFeatureConfig:
    def __init__(self, data):
        self.__netshield = data.get("NetShield")
        self.__guest_holes = data.get("GuestHoles")
        self.__server_refresh = data.get("ServerRefresh")
        self.__streaming_logos = data.get("StreamingServicesLogos")
        self.__port_forwarding = data.get("PortForwarding")
        self.__moderate_nat = data.get("ModerateNAT")
        self.__safe_mode = data.get("SafeMode")
        self.__poll_notification_api = data.get("PollNotificationAPI")
        self.__vpn_accelerator = data.get("VpnAccelerator")

    @property
    def netshield(self):
        return True if self.__netshield else False

    @property
    def guest_holes(self):
        return True if self.__guest_holes else False

    @property
    def server_refresh(self):
        return True if self.__server_refresh else False

    @property
    def streaming_logos(self):
        return True if self.__streaming_logos else False

    @property
    def port_forwarding(self):
        return True if self.__port_forwarding else False

    @property
    def moderate_nat(self):
        return True if self.__moderate_nat else False

    @property
    def safe_mode(self):
        return True if self.__safe_mode else False

    @property
    def poll_notification_api(self):
        return True if self.__poll_notification_api else False

    @property
    def vpn_accelerator(self):
        return True if self.__vpn_accelerator else False
