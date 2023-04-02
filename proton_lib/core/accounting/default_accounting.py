from ... import exceptions
from ..environment import ExecutionEnvironment
from ..utilities import Utilities
from ._base import Accounting
from ...logger import logger


class DefaultAccounting(Accounting):
    accounting = "default"

    def __init__(self):
        self._env = ExecutionEnvironment()

    def ensure_accounting_has_expected_values(self):
        """Ensure that accounting data is correct."""
        try:
            Utilities.ensure_internet_connection_is_available()
        except Exception as e: # noqa
            logger.exception(e)
            return

        try:
            self.refresh_vpn_data()
        except Exception as e:
            logger.exception(e)
            return

        if self.has_account_become_delinquent:
            raise exceptions.AccountIsDelinquentError("User is delinquent")
        elif self.has_account_been_downgraded:
            raise exceptions.AccountWasDowngradedError("Account has been downgraded")
        elif self.has_vpn_password_changed:
            raise exceptions.VPNUsernameOrPasswordHasBeenChangedError("VPN password has been changed")
        elif self.has_account_exceeded_max_ammount_of_connections:
            raise exceptions.ExceededAmountOfConcurrentSessionsError(
                "Too many concurrent sessions"
            )

    def refresh_vpn_data(self):
        self._previous_tier = self._env.api_session.vpn_tier
        self._previous_vpn_username = self._env.api_session.vpn_username
        self._previous_vpn_password = self._env.api_session.vpn_password
        self._previous_delinquent = self._env.api_session.delinquent

        self._env.api_session.refresh_vpn_data()

    @property
    def has_account_become_delinquent(self):
        return bool(self._env.api_session.delinquent) # noqa

    @property
    def has_account_been_downgraded(self):
        return self._previous_tier > self._env.api_session.vpn_tier

    @property
    def has_vpn_password_changed(self):
        return (
            self._previous_vpn_password != self._env.api_session.vpn_password
            or self._previous_vpn_username != self._env.api_session.vpn_username
        )

    @property
    def has_account_exceeded_max_ammount_of_connections(self):
        try:
            current_sessions = len(self._env.api_session.get_sessions())
        except: # noqa
            current_sessions = self._env.api_session.max_connections

        return current_sessions > self._env.api_session.max_connections
