
import json
import os

from .... import exceptions
from ....constants import NETZONE_METADATA_FILEPATH
from ....enums import MetadataActionEnum, MetadataEnum, NetzoneMetadataEnum
from ....logger import logger
from ._base import NetzoneMetadataBackend


class DefaultNetzone(NetzoneMetadataBackend):
    metadata = "default"

    METADATA_DICT = {
        MetadataEnum.NETZONE: NETZONE_METADATA_FILEPATH
    }

    def __init__(self):
        self.__netzone = None

    @property
    def address(self):
        """Get address from metadata file."""
        if self.__netzone is None:
            try:
                self.__netzone = self.get_metadata(MetadataEnum.NETZONE)[NetzoneMetadataEnum.ADDRESS.value]
            except KeyError:
                self.__netzone = ""

        return self.__netzone

    @address.setter
    def address(self, address):
        """Save address to metadata file."""
        if not address:
            return

        truncated_address = self._truncate_address(address)

        metadata = self.get_metadata(MetadataEnum.NETZONE)
        metadata[NetzoneMetadataEnum.ADDRESS.value] = truncated_address

        self.__write_metadata(MetadataEnum.NETZONE, metadata)
        logger.info("Saved IP to metadata")
        self.__netzone = truncated_address

    def _truncate_address(self, address):
        if not isinstance(address, str):
            address = str(address)

        parts = address.split(".")
        if len(parts) < 3:
            return ""

        return "{}.{}.{}.0".format(parts[0], parts[1], parts[2])

    def get_metadata(self, metadata_type):
        """Get metadata.

        Args:
            metadata_type (MetadataEnum): type of metadata to save

        Returns:
            dict: connection metadata
        """
        try:
            return self.manage_metadata(
                MetadataActionEnum.GET, metadata_type
            )
        except FileNotFoundError:
            return {}

    def __write_metadata(self, metadata_type, metadata):
        """Save metadata to file.

        Args:
            metadata_type (MetadataEnum): type of metadata to save
            metadata (dict): metadata content
        """
        self.manage_metadata(
            MetadataActionEnum.WRITE,
            metadata_type,
            metadata
        )

    def remove_metadata(self, metadata_type):
        """Remove metadata file.

        Args:
            metadata_type (MetadataEnum): type of metadata to save
        """
        self.manage_metadata(
            MetadataActionEnum.REMOVE,
            metadata_type
        )

    def manage_metadata(self, action, metadata_type, metadata=None):
        """Metadata manager."""
        logger.debug(
            "Metadata manager \"action: {} - Metadata type: {}\"".format(
                action,
                metadata_type
            )
        )
        metadata_action_dict = {
            MetadataActionEnum.GET: self.__get_metadata_from_file,
            MetadataActionEnum.WRITE: self.__write_metadata_to_file,
            MetadataActionEnum.REMOVE: self.__remove_metadata_file
        }

        if action not in metadata_action_dict:
            raise exceptions.IllegalMetadataActionError(
                "Illegal {} metadata action".format(action)
            )

        self.__ensure_metadata_type_is_valid(metadata_type)

        metadata_from_file = metadata_action_dict[action](
            metadata_type, metadata
        )
        return metadata_from_file

    def __get_metadata_from_file(self, metadata_type, _):
        """Get state metadata.

        Returns:
            json/dict
        """
        logger.debug("Getting metadata from \"{}\"".format(metadata_type))
        with open(self.METADATA_DICT[metadata_type]) as f:
            metadata = json.load(f)
            logger.debug("Successfully fetched metadata from file")
            return metadata

    def __write_metadata_to_file(self, metadata_type, metadata):
        """Save metadata to file."""
        with open(self.METADATA_DICT[metadata_type], "w") as f:
            json.dump(metadata, f)
            logger.debug(
                "Successfully saved metadata to \"{}\"".format(metadata_type)
            )

    def __remove_metadata_file(self, metadata_type, _):
        """Remove metadata file."""
        filepath = self.METADATA_DICT[metadata_type]

        if os.path.isfile(filepath):
            os.remove(filepath)

    def __ensure_metadata_type_is_valid(self, metadata_type):
        """Check metedata type."""
        logger.debug("Checking if {} is valid".format(metadata_type))
        if metadata_type not in self.METADATA_DICT:
            raise exceptions.IllegalMetadataTypeError(
                "Metadata type not found"
            )
        logger.debug("\"{}\" is valid metadata type".format(metadata_type))

    def __check_metadata_exists(self, metadata_type):
        """Check if metadata file exists."""
        logger.debug("Checking if \"{}\" exists".format(metadata_type))
        self.__ensure_metadata_type_is_valid(metadata_type)

        metadata_exists = False
        if os.path.isfile(self.METADATA_DICT[metadata_type]):
            metadata_exists = True

        logger.debug(
            "Metadata \"{}\" \"{}\"".format(
                metadata_type,
                ("exists" if metadata_exists else "does not exist")
            )
        )
        return metadata_exists
