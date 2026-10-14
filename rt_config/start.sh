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

# The image hardcodes SMTP to localhost:25 and ignores $MailCommand, so point it at MailHog
sed -i "s/host => 'localhost',/host => 'mail',/; s/port => 25,/port => 1025,/" \
  /opt/rt/lib/RT/Interface/Email.pm

echo "Running server"
/opt/rt/sbin/rt-server --port 8892 --standalone
