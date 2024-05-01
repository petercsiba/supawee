# Connects to your localdatabase,
# re-generates the model.py file with Base models.
import os
import re

import argparse
import subprocess


def adjust_generated_models(model_file: str):
    with open(model_file, "r") as file:
        data = file.read()

    # Define the regex patterns and replacements
    old_line_pattern = r"example = PostgresqlDatabase\(.*?\)"
    new_line = (
        "# NOTE: this file is fully generated, if you change something, it will go away\n"
        "from example.client import database_proxy"
    )
    data = re.sub(old_line_pattern, new_line, data, flags=re.DOTALL)

    # For BaseModel.Meta.example
    data = data.replace("example = example", "example = database_proxy")

    # Rename all classes that inherit from BaseModel with 'Base', e.g.:
    # class ClassName(BaseModel):
    # replace to
    # class BaseClassName(BaseModel):
    base_model_pattern = r"class (\w*?)(\(BaseModel\))"
    replacement = r"class Base\1\2"
    data = re.sub(base_model_pattern, replacement, data)

    # Replace model=Users with model=BaseUsers (might be too lenient)
    model_pattern = r"model=(\w*?)"
    model_replacement = r"model=Base\1"
    data = re.sub(model_pattern, model_replacement, data)

    # Add schema for table_name
    table_name_pattern = r"table_name = \"(\w*?)\""
    table_name_replacement_public = r'schema = "public"\n        table_name = "\1"'
    table_name_replacement_auth = r'schema = "auth"\n        table_name = "\1"'
    data = re.sub(table_name_pattern, table_name_replacement_public, data)
    data = data.replace(
        'schema = "public"\n        table_name = "users"',
        'schema = "auth"\n        table_name = "users"',
    )

    data = data.replace("BaseBaseModel", "BaseModel")

    # Hacks for circular deps
    circular_deps_fields = ["merged_into"]
    for field_name in circular_deps_fields:
        pattern = re.compile(
            f"    {field_name}" + r" = ForeignKeyField\([\s\S]*?\)", re.MULTILINE  # noqa
        )

        # Text to replace with
        replacement_text = f"""    # To overcome ForeignKeyField circular dependency
        {field_name}_id = UUIDField(null=True)"""

        # Replace
        data = re.sub(pattern, replacement_text, data)

    with open(model_file, "w") as file:
        file.write(data)

    # NOTE: For reference cycles leading to "Possible reference cycle: account" in comments
    #   and "NameError: name 'BaseAccount' is not defined" during run-time there are some workarounds.
    # https://docs.peewee-orm.com/en/latest/peewee/models.html#circular-foreign-key-dependencies
    # P1(devx): Update model gen to handle these.
    if "Possible reference cycle" in data:
        print("WARNING: There are reference cycle your program might NOT run")


def main():
    parser = argparse.ArgumentParser(description='Generate example models.')
    parser.add_argument('model_file', help='Path to the model file')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', default='54322')
    parser.add_argument('--username', default='postgres')
    parser.add_argument('--database', default='postgres')
    parser.add_argument('--password', default='postgres')
    args = parser.parse_args()

    model_file = args.model_file
    host = args.host
    port = args.port
    username = args.username
    database = args.database
    password = args.password

    env = os.environ.copy()
    # Unfortunately, passing password in the command line arguments somehow does NOT work
    # TODO(P0, correctness): Save the old one, and be sure to set it back.
    env["PGPASSWORD"] = password

    # !! BEWARE !!!
    # TODO(P1, devx): This is a terrible hack to coerce pwiz to create the auth.users model (which is linked so often).
    # Create a temporary table
    subprocess.run(
        f"psql -h {host} -p {port} -U {username} -d {database} -c \"CREATE TABLE public.users AS SELECT * FROM auth.users WHERE FALSE;\"",
        shell=True,
        env=env,
    )

    # Generate models using pwiz
    with open(model_file, 'w') as f:
        subprocess.run(f"python -m pwiz -e postgresql -H {host} -p {port} -u {username} {database}", shell=True,
                       stdout=f,
                       env=env,
                       )

    # Drop the temporary table
    subprocess.run(f"psql -h {host} -p {port} -U {username} -d {database} -c \"DROP TABLE public.users;\"", shell=True,
                   env=env)

    # Format the model file
    subprocess.run(f"black {model_file}", shell=True)
    adjust_generated_models(model_file)
    subprocess.run(f"black {model_file}", shell=True)


if __name__ == "__main__":
    main()