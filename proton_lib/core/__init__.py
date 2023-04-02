import configparser
import os
from ..constants import APP_CONFIG, APP_VERSION, LOGGER_NAME


def set_exception_catcher():
    def local_capture_exception(e):
        pass

    try:
        import sentry_sdk
        from sentry_sdk import capture_exception  # noqa
        from sentry_sdk.integrations.logging import ignore_logger
    except ModuleNotFoundError:
        return local_capture_exception
    else:
        configure_sentry(ignore_logger, sentry_sdk)

        return capture_exception


def configure_sentry(ignore_logger, sentry_sdk):
    ignore_logger(LOGGER_NAME)
    config = configparser.ConfigParser()
    config.read(APP_CONFIG)

    env = "development" if os.environ.get("protonvpn_env") else "production"  # noqa

    sentry_sdk.init(
        dsn=config["sentry"]["dsn"],
        ignore_errors=["KeyboardInterrupt"],
        release="protonvpn-nm-core@" + APP_VERSION,
        environment=env
    )


capture_exception = set_exception_catcher()
