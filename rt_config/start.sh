#!/bin/sh
set -e

if [ ! -f "/data/rt5-dev.sqlite" ]; then
  mkdir /data
  echo "Initializing RT SQLite database..."
  cpanm --notest DBD::SQLite
  /opt/rt/sbin/rt-setup-database --action init #--dba root
  echo "Initialized db"
else
  echo "Database already exists."
fi

echo "Running server"
/opt/rt/sbin/rt-server --port 8892 --standalone
