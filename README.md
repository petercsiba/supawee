# SupaWee

SupaWee is a Peewee model generation primarily to be used with Supabase (and other PostgresSQL).
It intends to be what [sqlacodegen](https://pypi.org/project/sqlacodegen/) is for SQLAlchemy. 

Born out of laziness of learning the mainstream SQLAlchemy, and shivers of using plain SQL.
I liked PeeWee as I am familiar with Django and seems lightweight to be deployed into AWS Lambdas or other edge functions. 
The generated models over just plain DB queries help with autocomplete and code navigation (e.g. what are the uses of `order.state`).

## Example models

```python
# your/models.py
class BaseUsers(BaseModel):
    email = CharField(null=True)
    id = UUIDField(null=True)
```

which you then can subclass to have relevant functionality right on the Model:

```python
# your/auth/related/objects/user.py
from your.models import BaseUsers

class Users(BaseUsers):
    class Meta:
        db_table = "users"

    @staticmethod
    def exists_by_email(email_raw: str) -> bool:
        email = email_raw.lower()
        return Users.select().where(Users.email == email).exists()
```

## Features
- Auto-generate PeeWee models from your local database (handles basic circular deps)
- Minimalistic so it can be easily packaged to Lambdas and Edge functions.
- Easy setup^TM and integration with Supabase and PostgreSQL.

BEWARE: This performs one *terrible hack* including dropping local temp table `public.users` to generate `auth.users`. 


## Installation
Install SupaWee using pip:

```shell
pip install git+https://github.com/petercsiba/supawee.git
```

And run it:
```shell
# model_file, description='filepath to models.py which will have all base models'
# '--host', default='localhost'
# '--port', default='54322'
# '--username', default='postgres'
# '--database', default='postgres'
# '--password', default='postgres'
supawee example/models.py
```

### !! DO NOT USE ON YOUR PRODUCTION DATABASE !! ###

### Requirements

- `psql` installed
- can run `python -m pwiz ...`

## Possible Future Things:
- Understand if async and connection pooling work well with this
  - Supabase has connection pooling: https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler
  - There is peewee async for some reason: https://peewee-async.readthedocs.io/en/latest/
- Look into FastAPI template to maybe support that too https://github.com/AndyPythonCode/FastAPI-crud-with-peewee/tree/main/backend


## Development Setup

In case you want to contribute! 

### Setup
```shell
git clone https://github.com/yourusername/supawee.git
cd supawee
```
### Python
Setup Python your preferred way. For your emotional stability please use a virtualenv.
The package creator used `pyenv virtualenv 3.9.16 supawee`

```shell
pip install -r requirements/common.txt -r requirements/local.txt
```
 
### Testing
TODO I promise!

Currently, best bet is to test manually with:
```shell
# lazy way
python -m supawee.generate_models

# proper way
pip install -e .
supawee example/models.py 
```

NOTE: You would need a local PostgreSQL Server running (e.g. `supabase start`). 

# FAQ
### But there is Supabase Python SDK
Yes you right, but I dislike using plain strings for column and table names:
```shell
# Snapshot of Supabase Python SDK (released mid 2022):

    for i in range(iterator):
        value = {'vendor_id': vendor_id, 'product_name': fake.ecommerce_name(),
                 'inventory_count': fake.random_int(1, 100), 'price': fake.random_int(45, 100)}
        main_list.append(value)
    data = supabase.table('Product').insert(main_list).execute()
```
https://supabase.com/blog/loading-data-supabase-python#inserting-data-into-supabase
