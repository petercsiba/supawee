# SupaWee

SupaWee is a Peewee integration for Supabase that simplifies the process of using Peewee as your ORM in Python projects that interact with PostgreSQL.

Was created out of frustration between tradeoffs of plain SQL and big SQLAlchemy (which I didn't know).
The hope is to be in the middle ground of that spectrum.

Yes, there is Supabase Python SDK but I want the ORM for ease of autocomplete, and code navigation (e.g. what are the uses of `order.state`).

BEWARE: This performs one *terrible hack* including dropping temp table `public.users`. 

```shell
# Snapshot of Supabase Python SDK (released mid 2022):

    for i in range(iterator):
        value = {'vendor_id': vendor_id, 'product_name': fake.ecommerce_name(),
                 'inventory_count': fake.random_int(1, 100), 'price': fake.random_int(45, 100)}
        main_list.append(value)
    data = supabase.table('Product').insert(main_list).execute()
```
https://supabase.com/blog/loading-data-supabase-python#inserting-data-into-supabase

## Features

- Easy setup^TM and integration with Supabase and PostgreSQL.
- Auto-generate PeeWee models from your local database (handles basic circular deps)
- Minimalistic so it can be easily packaged to Lambdas and Edge functions.

## Requirements

- `psql` installed
- can run `python -m pwiz ...`

## Installation

Install SupaWee using pip:

```bash
pip install git+https://github.com/petercsiba/SupaWee.git
```

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