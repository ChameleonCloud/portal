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

~~Use the docker container! See the `Dockerfile`~~ Use [Docker Compose](https://docs.docker.com/compose/)! The portal now uses the [reference-api](https://github.com/ChameleonCloud/reference-api) container for Resource Discovery. See [docker-compose.yml](docker-compose.yml) and [the reference-api repository](https://github.com/ChameleonCloud/reference-api).

#### Development

The docker-compose.yml included in this repo is setup for running the composition locally. First, clone the reference-api repository and build that image:

```bash
git clone git@github.com:ChameleonCloud/reference-api.git
cd reference-api
docker build -t referenceapi .
```

Copy the [chameleon_env.sample](chameleon_env.sample) file to `.chameleon_env` and configure the variables as necessary.

Finally, from this repository run:

```bash
docker-compose up
```

If you need to rebuild the image, simply run:

```bash
docker-compose build
```

#### Production

There are a few additional requirements for running the composition in production. We want to run Django with uWSGI and Nginx in production (not with the [development server](https://docs.djangoproject.com/en/1.7/ref/django-admin/#django-admin-runserver)!) so the ports and command are different. We also need to mount in SSL certificates and log file directories.

The Production `docker-compose.yml` would look more like the following:

```yaml
portal:
  image: mrhanlon/chameleon_portal:release
  env_file:
    - .chameleon_env
  volumes:
    - logs/nginx_access_chameleoncloud.log:/var/log/nginx/access_chameleoncloud.log
    - logs/nginx_error_chameleoncloud.log:/var/log/nginx/error_chameleoncloud.log
    - logs/django_chameleon_auth.log:/tmp/chameleon_auth.log
    - logs/django_chameleon.log:/tmp/chameleon.log
    - certs/certs0:/etc/ssl/chameleoncloud.org
    - certs/certs1:/etc/ssl/www.chameleon.tacc.utexas.edu
    - certs/certs2:/etc/ssl/api.chameleoncloud.org
    - media:/project/media
  ports:
    - 80:80
    - 443:443
  links:
    - referenceapi:referenceapi
referenceapi:
  image: referenceapi:latest
  ports:
    - 8000:8000
```

## Release History

See the [Changelog](CHANGELOG.md).
