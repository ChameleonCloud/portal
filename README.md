# Chameleon User Portal

## Dependencies

Running the portal locally or in production requires Docker and Docker-Compose.

## Configuration

A `.chameleon_env` file is sourced and used to configure some parts of the application.

The database is configured via the following environment variables:

- `DB_HOST`: The hostname to connect to, e.g., database.example.com
- `DB_PORT`: The MySQL port, e.g., 3306
- `DB_NAME`: The database name
- `DB_USER`: The username to authenticate
- `DB_PASSWORD`: The password to authenticate

The following environment variables must be configured for `pytas`:

- `TAS_URL`: the full base URI for the TAS API, e.g. https://tas.tacc.utexas.edu/api
- `TAS_CLIENT_KEY`: the api key
- `TAS_CLIENT_SECRET`: the api secret

The following environment variables must be configured for `djangoRT`:

- `RT_HOST`: the hostname for the RT instance's REST endpoint, e.g., https://example.com/REST/1.0/
- `RT_USERNAME`: the RT account username
- `RT_PASSWORD`: the RT account password
- `RT_DEFAULT_QUEUE`: The default queue to which tickets will be submitted

## Running the portal

Use [Docker Compose](https://docs.docker.com/compose/)! The portal now uses the [reference-api](https://github.com/ChameleonCloud/reference-api) container for Resource Discovery. See [docker-compose.yml](docker-compose.yml) and [the reference-api repository](https://github.com/ChameleonCloud/reference-api).

#### Development

The `docker-compose.yml` included in this repo is setup for running the composition locally. However, a few additional dependencies need to be in place first.

1. First, clone the reference-api repository and build that image:

```bash
git clone git@github.com:ChameleonCloud/reference-api.git
cd reference-api
git submodule init && git submodule update
docker build -t referenceapi .
```

2. Seed the local database (optional, but recommended). Since Portal is a CMS-based system, much of the content is embedded within the database. It can be helpful to seed your local environment with a dump from an existing database (e.g. the development database). You can do a `mysqldump` of the database and extract the SQL dump file to the `./db` folder. This folder is mounted inside a MariaDB container when running Portal locally, and this SQL dump will be automatically detected and used to seed the database when it starts.

3. Seed the media repository (optional, but recommended.) If you have seeded the local database, there will be links to files assumed to exist in the media folder. If you want these files to be properly served/displayed locally, you will also have to copy down these media files. A simple way is to create a tarball and extract it to `./media`, which will be mounted as a media directory in the local container.

4. Copy the [chameleon_env.sample](chameleon_env.sample) file to `.chameleon_env` and configure the variables as necessary.

Finally, you can start up the containers:

```bash
docker-compose -f docker-compose.dev.yml up
```

If you need to (re)build the image, simply run:

```bash
docker-compose -f docker-compose.dev.yml build
```

#### Production

There are a few additional requirements for running the composition in production. We want
to run Django with uWSGI and Nginx in production
(not with the [development server](https://docs.djangoproject.com/en/1.7/ref/django-admin/#django-admin-runserver)!)
so the ports and command are different. We also need to mount in certificates and sensitive
configuration for SSL/TLS and the media directory for Django.

The Production `docker-compose.yml` would look more like the following:

```yaml
portal:
  image: docker.chameleoncloud.org/portal:1.8
  env_file:
    - /path/to/chameleon.env
  volumes:
    - /path/to/certs/certs0:/etc/ssl/chameleoncloud.org
    - /path/to/certs/certs1:/etc/ssl/www.chameleon.tacc.utexas.edu
    - /path/to/certs/certs2:/etc/ssl/api.chameleoncloud.org
    - /path/to/dhparams.pem:/etc/ssl/dhparams.pem
    - /path/to//media:/project/media
  ports:
    - 80:80
    - 443:443
  links:
    - referenceapi:referenceapi
referenceapi:
  image: referenceapi:latest
  ports:
    - 8000:8000
  log_driver: syslog
  log_opt:
    syslog-tag: referenceapi
```

## Release History

See the [Changelog](CHANGELOG.md).
