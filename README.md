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

### Development

The `docker-compose.yml` included in this repo is setup for running the composition locally. However, a few additional dependencies need to be in place first.

1. First, clone the reference-api repository and build that image:

```shell
git clone git@github.com:ChameleonCloud/reference-api.git
cd reference-api
make
```

2. Seed the local database (optional, but recommended). Since Portal is a CMS-based system, much of the content is embedded within the database. It can be helpful to seed your local environment with a dump from an existing database (e.g. the development database). You can do a `mysqldump` of the database and extract the SQL dump file to the `./db` folder. This folder is mounted inside a MariaDB container when running Portal locally, and this SQL dump will be automatically detected and used to seed the database when it starts.

```shell
# On portal host
source /opt/portal-camino/conf/portal/.chameleon_env
mysqldump -h $DB_HOST -u $DB_USER --all-databases -p | gzip >/home/$USER/portal_dump.sql.gz
```

```shell
# On local host
scp $PORTAL_HOST:portal_dump.sql.gz ./db/
gunzip ./db/portal_dump.sql.gz
```

3. Seed the media repository (optional, but recommended.) If you have seeded the local database, there will be links to files assumed to exist in the media folder. If you want these files to be properly served/displayed locally, you will also have to copy down these media files. A simple way is to create a tarball and extract it to `./media`, which will be mounted as a media directory in the local container.

```shell
# On portal host
tar -czf /home/$USER/portal_media.tar.gz -C /var/www/chameleon/media/ .
```

```shell
# On local host
scp $PORTAL_HOST:portal_media.tar.gz .
tar -xzf portal_media.tar.gz -C ./media
```

4. Copy the [chameleon_env.sample](chameleon_env.sample) file to `.chameleon_env` and configure the variables as necessary. Two items in particular are **required**:

  * Update the `OIDC_RP_CLIENT_SECRET` to the client secret stored in the development Keycloak IdP server for the "portal-local-dev" client in the "chameleon" realm.
  * Update the `KEYCLOAK_PORTAL_ADMIN_CLIENT_SECRET` to the client secret stored in the development Keycloak IdP server for the "portal-local-dev-admin" client in the "master" realm.

Finally, you can start up the containers:

```bash
make start
```

If you need to (re)build the image, simply run:

```bash
make build
```

## Deployment

The production deployment of Portal is managed via [portal-camino](https://github.com/ChameleonCloud/portal-camino).
