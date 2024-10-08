# Connects to your localdatabase,
# re-generates the model.py file with Base models.
import argparse
import difflib
import logging
import os
import re
import subprocess

# Previously was BaseModel which somewhat conflicted with pydantic.
BASE_MODEL_NAME = "BaseDatabaseModel"


def _print_diff(orig_data: str, data: str):
    # Split the strings into lines
    lines1 = orig_data.splitlines()
    lines2 = data.splitlines()

    # Generate the diff
    diff = difflib.unified_diff(lines1, lines2, lineterm="")

    # Write the diff to a file
    with open("/tmp/adjust_generated_models_output.txt", "w") as file:
        for line in diff:
            file.write(line + "\n")

    # Optionally, log that the diff has been written
    logging.debug("Diff has been written to /tmp/adjust_generated_models_output.txt")


def adjust_generated_models(
    model_file: str, circular_deps_fields: list[str], is_print_diff: bool = False
):
    with open(model_file, "r") as file:
        orig_data = file.read()
    data = orig_data

    # `pwiz` generates model code with the super-heave PostgresqlDatabase object requiring it to be initiated ASAP.
    # So here we wrap it with peewee.DatabaseProxy which you can initiate (and connect) through
    # supawee.client.connect_to_postgres_i_will_call_disconnect_i_promise
    old_line_pattern = r"database = PostgresqlDatabase\(.*?\)"
    new_line = (
        "# NOTE: this file is fully generated, if you change something, it will go away\n"
        "# database_proxy is an abstraction around PostgresqlDatabase so we can defer initialization after model\n"
        "# declaration (i.e. the BaseDatabaseModels don't need to import that heavy object).\n"
        "from supawee.client import database_proxy"
    )
    data = re.sub(old_line_pattern, new_line, data, flags=re.DOTALL)

    # For BaseDatabaseModel.Meta.database
    data = data.replace("database = database", "database = database_proxy")

    # Rename all classes that inherit from BaseDatabaseModel with 'Base', e.g.:
    # class ClassName(BaseDatabaseModel):
    # replace to
    # class BaseClassName(BaseDatabaseModel):
    base_model_pattern = r"class (\w*?)(\(BaseModel\))"
    replacement = r"class Base\1(" + BASE_MODEL_NAME + ")"
    data = re.sub(base_model_pattern, replacement, data)

    # Replace model=Users with model=BaseUsers (might be too lenient)
    model_pattern = r"model=(\w*?)"
    model_replacement = r"model=Base\1"
    data = re.sub(model_pattern, model_replacement, data)

    # Add schema for table_name
    table_name_pattern = r"table_name = \"(\w*?)\""
    table_name_replacement_public = r'schema = "public"\n        table_name = "\1"'
    data = re.sub(table_name_pattern, table_name_replacement_public, data)
    data = data.replace(
        'schema = "public"\n        table_name = "users"',
        'schema = "auth"\n        table_name = "users"',
    )

    data = data.replace("class BaseModel", "class " + BASE_MODEL_NAME)

    # Hacks for circular deps - tested in prod.
    for field_name in circular_deps_fields:
        pattern = re.compile(
            f"    {field_name}" + r" = ForeignKeyField\([\s\S]*?\)",
            re.MULTILINE,  # noqa
        )

        # Text to replace with
        replacement_text = (
            "    # To overcome ForeignKeyField circular dependency\n"
            f"    {field_name}_id = UUIDField(null=True)"
        )

        # Replace
        data = re.sub(pattern, replacement_text, data)

    with open(model_file, "w") as file:
        file.write(data)

    if is_print_diff:
        _print_diff(orig_data, data)

    # NOTE: For reference cycles leading to "Possible reference cycle: account" in comments
    #   and "NameError: name 'BaseAccount' is not defined" during run-time there are some workarounds.
    # https://docs.peewee-orm.com/en/latest/peewee/models.html#circular-foreign-key-dependencies
    # P1(devx): Update model gen to handle these.
    if "Possible reference cycle" in data:
        print("supawee WARNING: There are reference cycle your program might NOT run")


def main():
    parser = argparse.ArgumentParser(description="Generate example models.")
    parser.add_argument("model_file", help="Path to the model file")
    parser.add_argument("--host", default="localhost", help="Host for the database")
    parser.add_argument("--port", default="54322", help="Port for the database")
    parser.add_argument(
        "--username", default="postgres", help="Username for the database"
    )
    parser.add_argument("--database", default="postgres", help="Database name")
    parser.add_argument(
        "--password", default="postgres", help="Password for the database"
    )
    parser.add_argument(
        "--circular_deps_fields",
        default="",
        help="Comma-separated field names for handling circular dependencies (without the _id suffix)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()

    # Set logging level based on verbose flag
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        logging.debug("Verbose logging enabled.")
    else:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    model_file = args.model_file
    host = args.host
    port = args.port
    username = args.username
    database = args.database
    password = args.password
    circular_deps_fields = args.circular_deps_fields.split(",")

    env = os.environ.copy()
    # Unfortunately, passing password in the command line arguments somehow does NOT work
    # TODO(P0, correctness): Save the old one, and be sure to set it back.
    logging.debug("PGPASSWORD env variable is set to the --password param.")
    env["PGPASSWORD"] = password

    # !! BEWARE !!!
    # TODO(P1, devx): This is a terrible hack to coerce pwiz to create the auth.users model (which is linked so often).
    logging.debug(
        "Creating a temporary table public.users as a hack to coerce pwiz to create the auth.users model."
    )
    subprocess.run(
        f"psql -h {host} -p {port} -U {username} -d {database} "
        + '-c "CREATE TABLE public.users AS SELECT * FROM auth.users WHERE FALSE;"',
        shell=True,
        env=env,
    )

    # Generate models using pwiz
    # TODO(P1, ux): Sometimes this generates a single-quote string file which in some cases leads to compile errors.
    #   https://github.com/coleifer/peewee/issues/2922#issuecomment-2331534413
    with open(model_file, "w") as f:
        command = (
            f"python -m pwiz -e postgresql -H {host} -p {port} -u {username} {database}"
        )
        logging.debug(f"Running model gen command: '{command}'")
        subprocess.run(
            command,
            shell=True,
            stdout=f,
            env=env,
        )

    # Drop the temporary table
    logging.debug("Dropping the temporary table public.users.")
    subprocess.run(
        f'psql -h {host} -p {port} -U {username} -d {database} -c "DROP TABLE public.users;"',
        shell=True,
        env=env,
    )

    # Format the model file
    subprocess.run(f"black {model_file}", shell=True)
    adjust_generated_models(
        model_file, circular_deps_fields, is_print_diff=args.verbose
    )
    logging.debug("Running black on the generated model file")
    subprocess.run(f"black {model_file}", shell=True)


if __name__ == "__main__":
    main()
