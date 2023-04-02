import json
import os
import time

from ...constants import PROTON_XDG_CACHE_HOME_STREAMING_ICONS
from ...logger import logger


class StreamingIcons:
    def __init__(self):
        self.__data = None
        self.__streaming_services = None

    def __getitem__(self, icon_name):
        if not isinstance(icon_name, str):
            raise TypeError("Expected type str (provided {})".format(type(icon_name)))

        if not os.path.isfile(os.path.join(PROTON_XDG_CACHE_HOME_STREAMING_ICONS, icon_name)):
            return None

        return os.path.join(PROTON_XDG_CACHE_HOME_STREAMING_ICONS, icon_name)

    def update_streaming_icons_data(self, streaming_services):
        try:
            self.__cache_streaming_icons(streaming_services)
        except Exception as e:
            logger.exception(e)
            return

        if not isinstance(self.__data, dict):
            self.__data = {}

        self.__data["StreamingIconsUpdateTimestamp"] = time.time()

    def __cache_streaming_icons(self, streaming_services):
        logger.info("Attempting to cache streaming icons")
        self.__streaming_services = streaming_services

        import concurrent.futures
        services_set = set()
        for _, content in self.__streaming_services.items():
            for icon_name in content["2"]:
                icon = icon_name.get("Icon", None)
                if icon:
                    services_set.add(icon)

        if not os.path.isdir(PROTON_XDG_CACHE_HOME_STREAMING_ICONS):
            os.makedirs(PROTON_XDG_CACHE_HOME_STREAMING_ICONS)

        logger.debug("Executing concurrent futures")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.__cache, services_set)

    def __cache(self, streaming_icon):
        import os
        from io import BytesIO

        import requests
        from PIL import Image

        icon_path = os.path.join(
            PROTON_XDG_CACHE_HOME_STREAMING_ICONS,
            streaming_icon
        )
        if os.path.isfile(icon_path):
            return

        try:
            r = requests.get(self.__streaming_services.base_url + streaming_icon, timeout=3)
        except requests.exceptions.BaseHTTPError as e:
            logger.exception(e)
            return

        i = Image.open(BytesIO(r.content))
        i.save(os.path.join(
            PROTON_XDG_CACHE_HOME_STREAMING_ICONS,
            streaming_icon
        ))

    def json_dumps(self):
        return json.dumps(self.__data)

    def json_loads(self, data):
        self.__data = json.loads(data)

    @property
    def streaming_icons_timestamp(self):
        try:
            return self.__data.get("StreamingIconsUpdateTimestamp", 0.0)
        except AttributeError:
            return 0.0
