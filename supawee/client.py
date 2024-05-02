import signal
from contextlib import contextmanager
from typing import Any, Generator, Optional

from peewee import DatabaseProxy, PostgresqlDatabase

# `database_proxy` is referenced from the generated models.py
# The DatabaseProxy simply defers the configuration of the database until a later time,
# but all interaction with the database (like connecting) should be done via the actual Database instance.
database_proxy = DatabaseProxy()
_postgres: Optional[PostgresqlDatabase] = None


def _remove_postgres_scheme(postgres_login_url):
    url = None
    if postgres_login_url.startswith("postgresql://"):
        url = postgres_login_url[13:]  # remove scheme
    elif postgres_login_url.startswith("postgres://"):
        url = postgres_login_url[11:]  # remove scheme

    if url is None:
        raise ValueError(
            "Invalid postgres login url, must start with postgres:// or postgresql://"
        )

    return url


def _get_postgres_kwargs(postgres_login_url):
    if postgres_login_url is None:
        raise ValueError("postgres_login_url is required, None given")

    # AWS Lambda only supports archaic package versions,
    #   also some passwords might contain wildcards like ? or & (yeah, thank you G chrome password manager)
    # This didn't work: parsed_url = urlparse(postgres_login_url)
    url = _remove_postgres_scheme(postgres_login_url)
    user, rest = url.split("@")[0], url.split("@")[1]
    login, password = user.split(":")[0], user.split(":")[1]

    host_port, database_name = rest.split("/")[0], rest.split("/")[1]
    host, port = host_port.split(":")[0], host_port.split(":")[1]

    res = {
        "database": database_name,
        "user": login,
        "password": password,
        "host": host,
        "port": int(port),  # convert string to int
    }
    return res


def _is_database_connected():
    global _postgres
    return _postgres is not None and not _postgres.is_closed()


# Prefer using `with connect_to_postgres` when you can.
# Only use the return value if you know what you are doing.
def connect_to_postgres_i_will_call_disconnect_i_promise(
    postgres_login_url: str,
    statement_timeout: int = None,
) -> PostgresqlDatabase:
    global _postgres
    if _is_database_connected():
        print("supawee.client: database connection already initialized, skipping")
        return _postgres

    # kwargs also has the password, so do not print all of it
    kwargs = _get_postgres_kwargs(postgres_login_url)
    print(
        f"supawee.client: postgres login url parsed into {kwargs['host']} port {kwargs['port']}"
        f" for db {kwargs['database']}"
    )

    _postgres = PostgresqlDatabase(**kwargs)
    # TODO(P2, reliability): Attach the function as a hook for when a connection is acquired (or when we re-connect)
    # _postgres.set_hooks({
    #  'after_connect': set_statement_timeout,
    # })
    _postgres.connect()
    _postgres.execute_sql("SELECT 1")
    if statement_timeout:
        set_statement_timeout(_postgres, statement_timeout)
    database_proxy.initialize(_postgres)
    return _postgres


def disconnect_from_postgres_as_i_promised():
    if _is_database_connected():
        print("supawee.client: closing connection to postgres database")
        _postgres.close()


# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    print("supawee.client: shutdown signal received - cleaning up...")
    disconnect_from_postgres_as_i_promised()


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Handle termination requests


def set_statement_timeout(db, seconds: int = 60):
    print(
        f"supawee.client: setting postgres client-side timeout for this session to {seconds} seconds"
    )
    db.execute_sql(f"SET statement_timeout TO {1000 * seconds}")


@contextmanager
def connect_to_postgres(postgres_login_url: str) -> Generator[Any, None, None]:
    try:
        connect_to_postgres_i_will_call_disconnect_i_promise(postgres_login_url)
        yield
    finally:
        disconnect_from_postgres_as_i_promised()
