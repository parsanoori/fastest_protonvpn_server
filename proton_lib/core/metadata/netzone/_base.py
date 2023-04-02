from abc import ABCMeta, abstractmethod
from ...utils import SubclassesMixin
from ....logger import logger


class NetzoneMetadataBackend(SubclassesMixin, metaclass=ABCMeta):

    @classmethod
    def get_backend(cls, backend="default"):
        subclasses_dict = cls._get_subclasses_dict("metadata")
        if backend not in subclasses_dict:
            raise NotImplementedError(
                "Metadata backend not implemented"
            )
        logger.info("Metadata backend: {}".format(
            subclasses_dict[backend]
        ))

        return subclasses_dict[backend]()

    @property
    @abstractmethod
    def address():
        """Get address."""
        pass

    @address.setter
    @abstractmethod
    def address():
        """Store address."""
        pass
