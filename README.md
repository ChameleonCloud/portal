# Chameleon User Portal

## Dependencies

Most dependencies are specified in [requirements.txt](requirements.txt) and can
be installed via pip. External depdencies not available via pip:

- https://bitbucket.org/mrhanlon/pytas.git
- https://gitlab.labs.nic.cz/labs/python-rt.git

These are configured as git submodules and can be checked out using

```
git submodule update --recursive --init
```

If using the Docker container to run the portal, the submodules should be
checked out before building the image.

## Configuration

The following environment variables must be configured for `pytas`:

- `TAS_URL`: the full base URI for the TAS API, e.g. https://tas.tacc.utexas.edu/api
- `TAS_CLIENT_KEY`: the api key
- `TAS_CLIENT_SECRET`: the api secret

The following environment variables must be configured for `djangoRT`:

- `RT_HOST`: the hostname for the RT instance's REST endpoint, e.g., https://example.com/REST/1.0/
- `RT_USERNAME`: the RT account username
- `RT_PASSWORD`: the RT account password
- `RT_DEFAULT_QUEUE`: The default queue to which tickets will be submitted

If you omit the `DB_*` environment variables, Django will create and use
the default SQLite database. This is intended only for development/testing.
For production, provide the following environment variables to configure the
MySQL database connection:

- `DB_HOST`: The hostname to connect to, e.g., database.example.com
- `DB_PORT`: The MySQL port, e.g., 3306
- `DB_NAME`: The database name
- `DB_USER`: The username to authenticate
- `DB_PASSWORD`: The password to authenticate

## Running the portal

User the docker container! See the `Dockerfile`

#### Development

Running the portal with local code:

```bash
docker run \
    -e "TAS_URL=$TAS_URL" \
    -e "TAS_CLIENT_KEY=$TAS_CLIENT_KEY" \
    -e "TAS_CLIENT_SECRET=$TAS_CLIENT_SECRET" \
    -e "RT_HOST=$RT_HOST" \
    -e "RT_USERNAME=$RT_USERNAME" \
    -e "RT_PASSWORD=$RT_PASSWORD" \
    -e "RT_DEFAULT_QUEUE=$RT_DEFAULT_QUEUE" \
    -v $(pwd):/project \
    -d -p ::8888 chameleon/portal python manage.py runserver 0.0.0.0:8888
```

You can specify database ENV variables to connect to a MySQL backend
(see production options below), otherwise it will just use the default
SQLite db.

#### Production

Runs the code in the container

**SSL certificates** are expected by nginx to be in
`/etc/ssl/chameleoncloud.org`. This should be mounted into the
container from the host. It looks for `bundle.crt` and `site.key`.

```bash
docker run \
    -e "TAS_URL=$TAS_URL" \
    -e "TAS_CLIENT_KEY=$TAS_CLIENT_KEY" \
    -e "TAS_CLIENT_SECRET=$TAS_CLIENT_SECRET" \
    -e "RT_HOST=$RT_HOST" \
    -e "RT_USERNAME=$RT_USERNAME" \
    -e "RT_PASSWORD=$RT_PASSWORD" \
    -e "RT_DEFAULT_QUEUE=$RT_DEFAULT_QUEUE" \
    -e "DB_NAME=$DB_NAME" \
    -e "DB_HOST=$DB_HOST" \
    -e "DB_PORT=$DB-PORT" \
    -e "DB_USER=$DB_USER" \
    -e "DB_PASSWORD=$DB_PASSWORD" \
    -e "DJANGO_ENV=Production" \
    -v $(pwd)/certificates:/etc/ssl/chameleoncloud.org \
    --name chameleon_portal \
    -dP chameleon/portal
```

## Release History

### v1.1.2

- Fix new institution creation when not listed

### v1.1.1

- Fixed documentation errors

### v1.1.0

- Added PI eligibility at registration and new project creation

### v1.0.1

- Improve workflow for FG project migration

### v1.0.0

- Initial release
