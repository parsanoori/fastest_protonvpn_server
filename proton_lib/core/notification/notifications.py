import json
import time
import os

from abc import abstractmethod

from ...constants import PROTON_XDG_CACHE_HOME_NOTIFICATION_ICONS
from ...logger import logger
from ...enums import NotificationEnum
from ..utils import SubclassesMixin


class NotificationData:

    def __init__(self):
        self.__data = None

    def json_dumps(self):
        return json.dumps(self.__data)

    def json_loads(self, data):
        self.__data = json.loads(data)

    def update_notifications_data(self, data):
        assert "Code" in data
        assert "Notifications" in data

        if data["Code"] != 1000:
            raise ValueError("Invalid data with code != 1000")

        data["NotificationsUpdateTimestamp"] = time.time()
        self.__data = data

    def get_notification(self, notification_type):
        try:
            _data = self.__data.get("Notifications", None)[0]
        except (IndexError, AttributeError) as e:
            logger.exception(e)
            _data = {}

        return BaseNotificationType.factory(
            _data,
            notification_type
        )

    def get_all_notifications(self):
        notifications = self.__data.get("Notifications", None)
        if len(notifications) < 1:
            logger.info("Nofitications are empty: {}".format(notifications))
            _data = {}
        else:
            _data = notifications[0]

        return BaseNotificationType.factory(_data)

    @property
    def notifications_timestamp(self):
        try:
            return self.__data.get("NotificationsUpdateTimestamp", 0.0)
        except AttributeError:
            return 0.0


class BaseNotificationType(SubclassesMixin):

    def __init__(self, data):
        self.__data = data

    @classmethod
    def factory(cls, data, attribute=None):
        if not data or len(data) == 0:
            return cls._get_subclasses_dict("notification_type")[
                NotificationEnum.EMPTY.value
            ](data)

        if not attribute:
            return [_intance(data) for _intance in cls._get_all_subclasses()]
        else:
            subclasses_dict = cls._get_subclasses_dict("notification_type")
            return subclasses_dict[attribute](data)

    @property
    def start_time(self):
        return self.__data.get("StartTime", 0)

    @property
    def end_time(self):
        return self.__data.get("EndTime", 0)

    @property
    @abstractmethod
    def can_be_displayed():
        raise NotImplementedError("Should be implemented")

    @property
    def type_of_notification(self):
        return self.__data.get("Type", None)

    @property
    def url(self):
        return self.offer.get("URL", None)

    @property
    def icon(self):
        return self.offer.get("Icon", None)

    @property
    def label(self):
        return self.offer.get("Label", None)

    @property
    def incentive(self):
        return self.panel.get("Incentive", None)

    @property
    def incentive_price(self):
        return self.panel.get("IncentivePrice", None)

    @property
    def pill(self):
        return self.panel.get("Pill", None)

    @property
    def picture_url(self):
        return self.panel.get("PictureURL", None)

    @property
    def title(self):
        return self.panel.get("Title", None)

    @property
    def features(self):
        return self.panel.get("Features", [])

    @property
    def features_footer(self):
        return self.panel.get("FeaturesFooter", None)

    @property
    def button_text(self):
        return self.button.get("Text", None)

    @property
    def button_url(self):
        return self.button.get("URL", None)

    @property
    def page_footer(self):
        return self.panel.get("PageFooter", None)

    @property
    def offer(self):
        return self.__data.get("Offer", {})

    @property
    def panel(self):
        return self.offer.get("Panel", {})

    @property
    def button(self):
        return self.panel.get("Button", {})


class EmptyNotificationObject(BaseNotificationType):
    notification_type = NotificationEnum.EMPTY.value

    """This class is used only when there is no data available,
    so that instead of creating multiple crashes and multiple error handling
    paths due to lack of data, it just returns an object with empty data, thus
    lowering the risk of incurring into exceptions and thus managing them.
    """
    def __init__(self, data):
        self.icon_paths = set()
        super().__init__(data)

    @property
    def can_be_displayed(self):
        return False


class GenericNotification(BaseNotificationType):
    notification_type = NotificationEnum.GENERIC.value

    def __init__(self, data):
        self.icon_paths = set()
        super().__init__(data)
        if self.can_be_displayed:
            self.__cache_icons()

    @property
    def incentive(self):
        _incentive = self.panel.get("Incentive", None)
        if not _incentive:
            return None

        return _incentive.replace(" ", "\u00a0")

    @property
    def incentive_price(self):
        _incentive_price = self.panel.get("IncentivePrice", None)
        if not _incentive_price:
            return None

        return _incentive_price.replace("/", "/\u2060")

    @property
    def incentive_template_index_start(self):
        return int(self.incentive.find("%IncentivePrice%"))

    @property
    def features(self):
        features = self.panel.get("Features", None)
        if not features:
            return []

        _f = []
        for feature_dict in features:
            feature_dict.get("IconURL", None)
            _f.append(
                (
                    feature_dict.get("Text", None),
                    feature_dict.get("IconURL", None)
                )
            )

        return _f

    @property
    def can_be_displayed(self):
        now = time.time()
        if (
            0 in [self.start_time, self.end_time]
        ) or (
            now < self.start_time or now > self.end_time
        ):
            return False

        return True

    def __cache_icons(self):
        import concurrent.futures
        import re

        icon_tuple_collection = set()
        pattern = re.compile(r"[\/]{1}([a-zA-Z0-9-]+\.(png|jpeg|jpg))")
        self.__recursive_search_for_icons(self.offer, icon_tuple_collection, pattern)

        if not os.path.isdir(PROTON_XDG_CACHE_HOME_NOTIFICATION_ICONS):
            os.makedirs(PROTON_XDG_CACHE_HOME_NOTIFICATION_ICONS)

        if all(list(map(self.__check_if_icons_exist, icon_tuple_collection))):
            self.icon_paths = {
                os.path.join(PROTON_XDG_CACHE_HOME_NOTIFICATION_ICONS, icon_tuple[0])
                for icon_tuple in icon_tuple_collection
            }
            return

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.__download_and_store_icon, icon_tuple_collection)

    def __check_if_icons_exist(self, data):
        icon_name, url = data
        return self.__check_if_specific_icon_exists(icon_name)

    def __download_and_store_icon(self, data):
        icon_name, url = data

        if not self.__check_if_specific_icon_exists(icon_name):
            content = self.__download_icon(url)
            self.__store_icon(content, icon_name)

    def __download_icon(self, url):
        import requests
        try:
            r = requests.get(url, timeout=3)
        except requests.exceptions.BaseHTTPError as e:
            logger.exception(e)
            return

        return r.content

    def __store_icon(self, content, icon_name):
        from io import BytesIO
        from PIL import Image

        path = os.path.join(
            PROTON_XDG_CACHE_HOME_NOTIFICATION_ICONS,
            icon_name
        )

        i = Image.open(BytesIO(content))
        i.save(path)
        self.icon_paths.add(path)

    def __check_if_specific_icon_exists(self, icon_name):
        if not os.path.isfile(os.path.join(
            PROTON_XDG_CACHE_HOME_NOTIFICATION_ICONS,
            icon_name
        )):
            return False

        return True

    def __recursive_search_for_icons(self, data, icon_collection, pattern):
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str):
                    pattern_result = pattern.search(v)
                    if pattern_result:
                        icon_collection.add((pattern_result.group(1), v))
                elif isinstance(v, (dict, list)):
                    self.__recursive_search_for_icons(v, icon_collection, pattern)
        elif isinstance(data, list):
            for v in data:
                if isinstance(v, str):
                    pattern_result = pattern.search(v)
                    if pattern_result:
                        icon_collection.add((pattern_result.group(1), v))
                elif isinstance(v, (list, dict)):
                    self.__recursive_search_for_icons(v, icon_collection, pattern)
