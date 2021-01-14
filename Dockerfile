ARG PY_IMG_TAG=3.7.9-stretch
FROM python:${PY_IMG_TAG}

# Set shell to use for run commands
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install repos for node6.x. 
# WARNING: EOL on 2019-04-30
# https://github.com/nodejs/Release#end-of-life-releases
ARG NODE_VER=lts
RUN curl -sL https://deb.nodesource.com/setup_${NODE_VER}.x | bash -

# Install apt packages
RUN apt-get update && apt-get install --no-install-recommends -y \
  gettext \
  curl \
  build-essential \
  nodejs \
  ruby-sass \
  ruby-compass \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install npm packages
RUN npm install -g \
  yuglify@^2.0.0

# install python dependencies
WORKDIR /setup

# Use pip to install poetry. We don't use virtualenvs in the build context.
# Therefore, the vendored install provides no additional isolation.
RUN pip install \
  poetry~=1.1 \
  uWSGI~=2.0

COPY poetry.lock /setup/poetry.lock
COPY pyproject.toml /setup/pyproject.toml
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install --no-dev --no-root

RUN mkdir /var/log/django
VOLUME ["/media"]
VOLUME ["/static"]

COPY . /project
WORKDIR /project
# translation messages, if necessary
RUN python manage.py compilemessages
# copy compiled JS assets
COPY --from=client /project/static/vue /project/static/vue
COPY --from=client /project/webpack-stats.json /project/webpack-stats.json

EXPOSE 80 443
