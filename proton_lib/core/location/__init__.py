class CurrentLocation:

    def __init__(self, raw_data):
        self.__ip = raw_data.get("IP")
        self.__lat = raw_data.get("Lat")
        self.__long = raw_data.get("Long")
        self.__country = raw_data.get("Country")
        self.__isp = raw_data.get("ISP")

    @property
    def ip(self):
        return self.__ip

    @property
    def latitude(self):
        return self.__lat

    @property
    def longitude(self):
        return self.__long

    @property
    def country_code(self):
        return self.__country

    @property
    def isp(self):
        return self.__isp
