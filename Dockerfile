ARG NODE_IMG=node
ARG NODE_VER_NAME=20
ARG PY_IMG=python

FROM ${NODE_IMG}:${NODE_VER_NAME} AS client
WORKDIR /project
COPY package.json yarn.lock ./
RUN yarn install --network-timeout 1000000
COPY . ./
RUN yarn build --production

FROM ${PY_IMG}:3.12
# Set shell to use for run commands
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN curl -sL https://deb.nodesource.com/setup_20.x | bash -

# Install apt packages
RUN apt-get update && apt-get install --no-install-recommends -y \
  gettext \
  curl \
  build-essential \
  nodejs \
  default-mysql-client \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# install python dependencies
WORKDIR /setup

# BUG: this is not being carried over from the builder somehow
COPY package.json yarn.lock ./
# uglify-js: for JS compression
# yuglify: for CSS compression
RUN npm install -g \
  uglify-js \
  yuglify \
  sass@1.82

# Use pip to install poetry. We don't use virtualenvs in the build context.
# Therefore, the vendored install provides no additional isolation.
RUN pip install --upgrade pip && \
  pip install \
  poetry~=1.2

COPY poetry.lock pyproject.toml /setup/
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install --no-root --only main

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
