import json
import random
import time
import weakref

from ... import exceptions
from ...enums import FeatureEnum
from ...logger import logger
from ..environment import ExecutionEnvironment
# For simplification, we'll use format as coming from the API here,
# although that might not be a good approach for genericity


class PhysicalServer:
    def __init__(self, data):
        self._data = data

    @property
    def entry_ip(self):
        return self._data["EntryIP"]

    @property
    def exit_ip(self):
        return self._data["ExitIP"]

    @property
    def domain(self):
        return self._data["Domain"]

    # Domain can be set to new value when
    # searching for matching domain
    @domain.setter
    def domain(self, newvalue):
        self._data["Domain"] = newvalue

    @property
    def enabled(self):
        return self._data["Status"] == 1

    @property
    def generation(self):
        return self._data["Generation"]

    @property
    def label(self):
        return self._data["Label"]

    @property
    def services_down_reason(self):
        return self._data["ServicesDownReason"]

    def get_configuration(self, proto):
        from ..vpn import VPNConfiguration
        return VPNConfiguration.factory(proto, self)

    def __repr__(self):
        if self.label != '':
            return 'PhysicalServer<{}+b:{}>'.format(self.domain, self.label)
        else:
            return 'PhysicalServer<{}>'.format(self.domain)


class LogicalServer:
    """
    LogicalServer is a view of ServerList.

    Due to the way Python works, data is basically a reference
    to the inside of the ServerList data.
    Beware that this is intended to be a short-lived object,
    if ServerList reloads completely, a LogicalServer will not
    retain its bound to the list.
    """
    def __init__(self, data):
        self._data = data

    @property
    def id(self):
        return self._data["ID"]

    # Score, load and status can be modified (needed to update loads)
    @property
    def load(self):
        return self._data["Load"]

    @load.setter
    def load(self, newvalue):
        self._data["Load"] = int(newvalue)

    @property
    def score(self):
        return self._data["Score"]

    @score.setter
    def score(self, newvalue):
        self._data["Score"] = float(newvalue)

    @property
    def enabled(self):
        return self._data["Status"] == 1 and any(
            x.enabled for x in self.physical_servers
        )

    @enabled.setter
    def enabled(self, newvalue):
        self._data["Status"] = newvalue

    # Every other propriety is readonly
    @property
    def name(self):
        return self._data["Name"]

    @property
    def entry_country(self):
        return self._data["EntryCountry"]

    @property
    def exit_country(self):
        return self._data["ExitCountry"]

    @property
    def host_country(self):
        return self._data["HostCountry"]

    # We do not expose on purpose the domain, it should be deprecated soob
    @property
    def features(self):
        return self.__unpack_bitmap_features(self._data["Features"])

    def __unpack_bitmap_features(self, server_value):
        server_features = [
            feature_enum
            for feature_enum
            in FeatureEnum.list()
            if (server_value & feature_enum) != 0 or feature_enum == 0
        ]
        return server_features

    @property
    def region(self):
        return self._data["Region"]

    @property
    def city(self):
        return self._data["City"]

    @property
    def tier(self):
        return self._data["Tier"]

    @property
    def latitude(self):
        return self._data["Location"]["Lat"]

    @property
    def longitude(self):
        return self._data["Location"]["Long"]

    @property
    def data(self):
        return self._data.copy()

    @property
    def physical_servers(self):
        return [PhysicalServer(x) for x in self._data["Servers"]]

    def get_random_physical_server(self):
        enabled_servers = [x for x in self.physical_servers if x.enabled]
        if len(enabled_servers) == 0:
            logger.error("List of physical servers is empty")
            raise exceptions.EmptyServerListError("No servers could be found")

        return random.choice(enabled_servers)

    def __repr__(self):
        return 'LogicalServer<{}>'.format(self._data.get("Name", "??"))


class ServerList:
    """
    This class handles the list of logicals.

    There are two variants:
    - the toplevel list (which contains and owns the data in itself)
    - the sublists, which are in practice views of the toplevel one,
        with a criteria

    All of these classes refer have an _ids property, which is the list of
    toplevel indices (logicals) this class has access to.

    When the toplevel
    """
    def __init__(
        self, toplevel=None,
        condition=None,
        sort_key=None,
        sort_reverse=False
    ):
        if toplevel is not None:
            assert isinstance(toplevel, self.__class__)
            self._toplevel = toplevel
            self._toplevel._views.add(self)
            self._condition = condition
            self._views = set()
        else:
            assert condition is None

            self._toplevel = None
            self._condition = None
            self.__data = {'LogicalServers': {}}
            self._views = weakref.WeakSet()

        self._sort_key = sort_key
        self._sort_reverse = sort_reverse

        self.refresh_indexes()

    @property
    def _data(self):
        if self.is_toplevel:
            return self.__data
        else:
            return self._toplevel.__data

    @property
    def is_toplevel(self):
        return self._toplevel is None

    def ensure_toplevel(self):
        if not self.is_toplevel:
            raise ValueError(
                "This function has to be called in "
                "a toplevel ServerList"
            )

    @property
    def logicals_update_timestamp(self):
        return self._data.get('LogicalsUpdateTimestamp', 0.)

    @property
    def loads_update_timestamp(self):
        return self._data.get('LoadsUpdateTimestamp', 0.)

    def json_dumps(self):
        self.ensure_toplevel()
        return json.dumps(self._data)

    def json_loads(self, data):
        self.ensure_toplevel()
        self.__data = json.loads(data)

        # Refresh indexes
        self.refresh_indexes()

    def update_logical_data(self, data):
        assert 'Code' in data
        assert 'LogicalServers' in data

        self.ensure_toplevel()

        if data["Code"] != 1000:
            raise ValueError("Invalid data with code != 1000")

        self.__data = data
        # We update both LastLogicalUpdate and LastLoadUpdate, as Load contains
        self.__data["LogicalsUpdateTimestamp"] = time.time()
        self.__data["LoadsUpdateTimestamp"] = time.time()

        self.refresh_indexes()

    def update_load_data(self, data):
        assert 'Code' in data
        assert 'LogicalServers' in data

        self.ensure_toplevel()

        if data["Code"] != 1000:
            raise ValueError("Invalid data with code != 1000")

        self.__data["LoadsUpdateTimestamp"] = time.time()

        for s in data["LogicalServers"]:
            if s["ID"] not in self._logicals_by_id:
                # This server doesn't exists in the cached list
                continue
            server = self[s["ID"]]

            server.load = s.get("Load", server.load)
            server.score = s.get("Score", server.score)
            server.enabled = s.get("Status", server.enabled)

        # Required to sort lists again if needed
        self.refresh_indexes()

    def refresh_indexes(self):
        # Create indexes
        self._ids = []
        self._logicals_by_id = {}
        self._logicals_by_name = {}

        # Re-apply filter condition (if any)
        for logical_id, logical in enumerate(self._data["LogicalServers"]):
            server = LogicalServer(logical)
            if self._condition is None or self._condition(server):
                self._logicals_by_id[logical["ID"]] = logical_id
                self._logicals_by_name[logical["ID"]] = logical_id
                self._ids.append(logical_id)

        # Re-apply filter condition on children (if any)
        for v in self._views:
            v.refresh_indexes()

        # Sort (if needed)
        self._sort()

    def __len__(self):
        return len(self._ids)

    def __getitem__(self, idx):
        if type(idx) == str:
            internal_idx = self._logicals_by_id[idx]
        else:
            internal_idx = self._ids[idx]

        return LogicalServer(self._data["LogicalServers"][internal_idx])

    def __iter__(self):
        for idx in range(len(self)):
            yield self[idx]

    def __repr__(self):
        if self.is_toplevel:
            return 'ServerList<{} servers>'.format(len(self))
        else:
            return 'ServerList<{}/{} servers>'.format(
                len(self), len(self._toplevel)
            )

    def filter(self, condition):
        if self.is_toplevel:
            return ServerList(self, condition)
        else:
            return ServerList(
                self._toplevel,
                lambda x: self._condition(x) and condition(x)
            )

    def filter_servers_by_tier(self):
        # Filter servers bye tier
        server_list = list(self.filter(
            lambda server: server.tier <= ExecutionEnvironment().api_session.vpn_tier # noqa
        ))
        return server_list

    def get_random_server(self):
        self.__ensure_cache_exists()
        server_list = self.filter_servers_by_tier()
        return server_list[random.randint(0, len(server_list) - 1)]

    def get_fastest_server(self):
        return self.get_fastest_servers(1)[0]

    def get_fastest_servers(self, n):
        # Get the fastest enabled server
        self.__ensure_cache_exists()
        servers_ordered = list(
            self.filter(
                lambda server: server.enabled
                and server.tier <= ExecutionEnvironment().api_session.vpn_tier
            ).sort(
                lambda server: server.score
            )
        )
        if len(servers_ordered) == 0:
            logger.error("List of logical servers is empty")
            raise exceptions.EmptyServerListError(
                "No logical server could be found"
            )
        return servers_ordered[:n]

    def __ensure_cache_exists(self):
        """Ensure that cache exists."""
        try:
            if self._toplevel.__data is None:
                logger.error("Server cache not found")
                raise exceptions.ServerCacheNotFound("Server cache not found")
        except AttributeError:
            if self.__data is None:
                logger.error("Server cache not found")
                raise exceptions.ServerCacheNotFound("Server cache not found")

    def match_server_domain(self, physical_server):
        domain = physical_server.domain

        for logical_server in self:
            if FeatureEnum.SECURE_CORE not in logical_server.features:
                servers = logical_server.physical_servers
                servers = [
                    _physical_server
                    for _physical_server
                    in servers
                    if _physical_server.exit_ip == physical_server.exit_ip
                ]

                if len(servers) > 0:
                    domain = servers.pop().domain
                    break

        physical_server.domain = domain

    def sort(self, key=None, reverse=False):
        """
        Sort, in place, the current ServerList, and return it.

        Example: sort the servers by name:
        sl.sort(lambda x: x.name)
        """

        self._sort_key = key
        self._sort_reverse = reverse
        return self._sort()

    def _sort(self):
        """Sort (or re-sort) the list"""
        if self._sort_key is None:
            self._ids.sort(reverse=self._sort_reverse)
        else:
            self._ids.sort(
                key=lambda i: self._sort_key(
                    LogicalServer(self._data["LogicalServers"][i])
                ),
                reverse=self._sort_reverse
            )

        # This is practical as we can chain these calls
        return self
