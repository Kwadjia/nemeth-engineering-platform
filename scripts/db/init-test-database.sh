#!/bin/sh
# Runs once when the PostgreSQL volume is first initialised: creates the test database
# next to the development database so `pytest` works out of the box.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE nemeth_test;
EOSQL
