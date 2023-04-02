from abc import abstractmethod, ABCMeta
from ..utils import SubclassesMixin
from ...logger import logger


class SettingsBackend(SubclassesMixin, metaclass=ABCMeta):

    @classmethod
    def get_backend(cls, settings_backend="default"):
        subclasses_dict = cls._get_subclasses_dict("settings_backend")
        if settings_backend not in subclasses_dict:
            raise NotImplementedError("Backend not implemented")
        logger.info("Settings backend: {}".format(
            subclasses_dict[settings_backend]
        ))

        return subclasses_dict[settings_backend]()

    @property
    @abstractmethod
    def netshield():
        """Get user netshield setting."""
        pass

    @netshield.setter
    @abstractmethod
    def netshield():
        """Set netshield to specified option."""
        pass

    @property
    @abstractmethod
    def killswitch():
        """Get user Kill Switch setting."""
        pass

    @killswitch.setter
    @abstractmethod
    def killswitch():
        """Set Kill Switch to specified option."""
        pass

    @property
    @abstractmethod
    def secure_core():
        """Get Secure Core setting.

        This is mostly for GUI as it might not be very
        relevant for CLIs.
        """
        pass

    @secure_core.setter
    @abstractmethod
    def secure_core():
        """Get Secure Core setting.

        This is mostly for GUI as it might not be very
        relevant for CLIs."""
        pass

    @property
    @abstractmethod
    def protocol():
        """Get default protocol."""
        pass

    @protocol.setter
    @abstractmethod
    def protocol():
        """Set default protocol setting."""
        pass

    @property
    @abstractmethod
    def dns():
        """Get user DNS setting."""
        pass

    @dns.setter
    @abstractmethod
    def dns():
        """Set DNS setting."""
        pass

    @property
    @abstractmethod
    def dns_custom_ips():
        """Get user DNS setting."""
        pass

    @dns_custom_ips.setter
    @abstractmethod
    def dns_custom_ips():
        """Set custom DNS lis."""
        pass

    @property
    @abstractmethod
    def vpn_accelerator():
        """Get user VPN Accelerator setting."""
        pass

    @vpn_accelerator.setter
    @abstractmethod
    def vpn_accelerator():
        """Set VPN Accelerator lis."""
        pass

    @property
    @abstractmethod
    def event_notification():
        """Get event notification setting."""
        pass

    @event_notification.setter
    @abstractmethod
    def event_notification():
        """Set event notification."""
        pass

    @property
    @abstractmethod
    def new_brand():
        """Get new brand setting."""
        pass

    @new_brand.setter
    @abstractmethod
    def new_brand():
        """Set new brand notification."""
        pass

    @property
    @abstractmethod
    def moderate_nat():
        """Get moderate NAT setting."""
        pass

    @moderate_nat.setter
    @abstractmethod
    def moderate_nat():
        """Set moderate NAT."""
        pass

    @property
    @abstractmethod
    def non_standard_ports():
        """Get moderate NAT setting."""
        pass

    @non_standard_ports.setter
    @abstractmethod
    def non_standard_ports():
        """Set moderate NAT."""
        pass

    @abstractmethod
    def reset_to_default_configs():
        """Reset user configuration to default values."""
        pass

    @abstractmethod
    def get_user_settings():
        """Get user settings."""
        pass
