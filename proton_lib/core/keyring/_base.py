from abc import ABCMeta, abstractmethod
from ...logger import logger
from ..utils import SubclassesMixin


class KeyringBackend(SubclassesMixin, metaclass=ABCMeta):
    def __init__(self):
        pass

    @classmethod
    def get_default(cls):
        subclasses = cls._get_subclasses_with('priority')
        subclasses.sort(key=lambda x: x.priority, reverse=True)
        for subclass in subclasses:
            try:
                logger.info("Using \"{}\" keyring".format(subclass))
                return subclass()
            except: # noqa
                pass

        raise RuntimeError("Couldn't initialize any keyring")

    def _ensure_key_is_valid(self, key):
        if type(key) != str:
            raise TypeError(f"Invalid key for keyring: {key!r}")
        if not key.isalnum():
            raise ValueError("Keyring key should be alphanumeric")

    def _ensure_value_is_valid(self, value):
        if not isinstance(value, dict):
            msg = "Provided value {} is not a valid type (expect {})".format(
                value, dict
            )

            logger.error(msg)
            raise TypeError(msg)

    @abstractmethod
    def __getitem__(self, key):
        """Get an item from the keyring"""
        pass

    @abstractmethod
    def __delitem__(self, key):
        """Remove an item from the keyring"""
        pass

    @abstractmethod
    def __setitem__(self, key, value):
        """Add or replace an item in the keyring"""
        pass

    @abstractmethod
    def _ensure_backend_is_working(self):
        """Ensure that a backend is working properly."""
        pass
