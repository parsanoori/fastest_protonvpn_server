from abc import ABCMeta, abstractmethod
from ..utils import SubclassesMixin
from ...logger import logger


class Accounting(SubclassesMixin, metaclass=ABCMeta):

    @classmethod
    def get_backend(cls, backend="default"):
        subclasses_dict = cls._get_subclasses_dict("accounting")
        if backend not in subclasses_dict:
            raise NotImplementedError("Backend not implemented")
        logger.info(
            "Accounting backend: {}".format(subclasses_dict[backend])
        )

        return subclasses_dict[backend]()
