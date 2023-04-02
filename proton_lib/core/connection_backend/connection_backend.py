from abc import ABCMeta, abstractmethod
from ..utils import SubclassesMixin
from ...logger import logger


class ConnectionBackend(SubclassesMixin, metaclass=ABCMeta):

    @classmethod
    def get_backend(cls, backend_client="networkmanager"):
        subclasses_dict = cls._get_subclasses_dict("client")
        if backend_client not in subclasses_dict:
            raise NotImplementedError("Backend not implemented")

        logger.info("Connection backend: {}".format(
            subclasses_dict[backend_client]
        ))
        return subclasses_dict[backend_client]()

    @property
    @abstractmethod
    def vpn_configuration():
        """Get certificate filepath property."""
        pass

    @vpn_configuration.setter
    @abstractmethod
    def vpn_configuration():
        """Set property of virtual device tunnel."""
        pass

    @property
    @abstractmethod
    def virtual_device_name():
        """Get property of virtual device tunnel."""
        pass

    @abstractmethod
    def get_non_active_protonvpn_connection():
        """Get non active VPN connection.

        A connection can be existent but not active, thus
        it should be gettable.
        """
        pass

    def get_active_protonvpn_connection():
        "Get active VPN connection."

    @abstractmethod
    def setup():
        """Setup VPN connection.

        This should be used only if there are required steps before
        starting the connection.
        """
        pass

    @abstractmethod
    def connect():
        """Setup VPN connection."""
        pass

    @abstractmethod
    def disconnect():
        """Setup VPN connection."""
        pass
