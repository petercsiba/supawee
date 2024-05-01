from contextlib import contextmanager
from typing import Any, Generator, Optional

from peewee import DatabaseProxy, OperationalError, PostgresqlDatabase

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

    # AWS Lambda only supports archaic package versions, also some passwords might contain wildcards like ? or &
    # parsed_url = urlparse(postgres_login_url)
    #
    # res = {
    #     "database": parsed_url.path[1:],
    #     "user": parsed_url.username,
    #     "password": parsed_url.password,
    #     "host": parsed_url.hostname,
    #     "port": parsed_url.port,
    # }
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


def set_statement_timeout(db):
    print("NOTE: Setting postgres client-side timeout for this session to 1 minute")
    db.execute_sql("SET statement_timeout TO 60000")  # 60000 milliseconds = 1 minute


# Prefer using `with connect_to_postgres` when you can.
# Only use the return value if you know what you are doing.
def connect_to_postgres_i_will_call_disconnect_i_promise(
    postgres_login_url: str,
) -> PostgresqlDatabase:
    global _postgres
    if _is_database_connected():
        print("database connection already initialized, skipping")
        return _postgres

    kwargs = _get_postgres_kwargs(postgres_login_url)
    print(f"postgres login url parsed into {kwargs['host']} port {kwargs['port']} for db {kwargs['database']}")

    _postgres = PostgresqlDatabase(**kwargs)
    # TODO(P2, reliability): Attach the function as a hook for when a connection is acquired (or when we re-connect)
    # _postgres.set_hooks({
    #  'after_connect': set_statement_timeout,
    # })
    _postgres.connect()
    _postgres.execute_sql("SELECT 1")
    set_statement_timeout(_postgres)
    database_proxy.initialize(_postgres)
    return _postgres


def disconnect_from_postgres_as_i_promised():
    if _postgres is not None:
        _postgres.close()


@contextmanager
def connect_to_postgres(postgres_login_url: str) -> Generator[Any, None, None]:
    try:
        connect_to_postgres_i_will_call_disconnect_i_promise(postgres_login_url)
        yield
    except OperationalError:
        print("Couldn't connect to the database, running in offline mode.")
        yield
    finally:
        print("closing connection to postgres database")
        disconnect_from_postgres_as_i_promised()
