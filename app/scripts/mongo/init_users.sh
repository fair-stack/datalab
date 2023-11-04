#!/usr/bin/env bash

echo "Creating users..."
mongo admin --host localhost -u root -p root --eval "db.createUser({user:'datalab', pwd: 'datalab123', roles: [{role:'dbOwner', db: 'datalab'}]});"
echo "Users created."
