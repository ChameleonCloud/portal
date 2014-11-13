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

- TAS_URL: the full base URI for the TAS API, e.g. https://tas.tacc.utexas.edu/api
- TAS_CLIENT_KEY: the api key
- TAS_CLIENT_SECRET: the api secret

The following environment variables must be configured for `djangoRT`:

-RT_HOST: the hostname for the RT instance's REST endpoint, e.g., https://example.com/REST/1.0/
-RT_USERNAME: the RT account username
-RT_PASSWORD: the RT account password
-RT_DEFAULT_QUEUE: The default queue to which tickets will be submitted

*TODO document database*

## Running the portal

User the docker container! See the `Dockerfile`

Running the portal with local code mounted:

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
    -e "DB-PORT=$DB_PORT" \
    -e "DB_USER=$DB_USER" \
    -e "DB_PASSWORD=$DB_PASSWORD" \
    -v $(pwd):/project \
    --name chameleon_portal \
    -d -p ::8888 chameleon/portal python manage.py runserver 0.0.0.0:8888
```

Production run:

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
    -e "DB-PORT=$DB-PORT" \
    -e "DB_USER=$DB_USER" \
    -e "DB_PASSWORD=$DB_PASSWORD" \
    --name chameleon_portal \
    -dP chameleon/portal
```
