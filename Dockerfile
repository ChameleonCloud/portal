FROM python:3.7.9-stretch as base

RUN apt-get update \
  && curl -sL https://deb.nodesource.com/setup_6.x | bash \
  && apt-get install -y \
    gettext curl build-essential nodejs ruby-sass ruby-compass \
  && rm -rf /var/lib/apt/lists/* \
  && pip install uwsgi \
  && npm install -g yuglify

# install python dependencies
COPY requirements.txt /setup/requirements.txt
COPY upper-constraints.txt /setup/upper-constraints.txt
RUN pip install --upgrade pip \
    && pip install -r /setup/requirements.txt -c /setup/upper-constraints.txt

FROM node:lts as js_builder

COPY . /project
WORKDIR /project

RUN yarn install
RUN yarn build --production

FROM base as release

COPY . /project
WORKDIR /project

RUN mkdir /var/log/django

# translation messages, if necessary
RUN python manage.py compilemessages
# copy compiled JS assets
COPY --from=js_builder /project/static/vue /project/static/vue
COPY --from=js_builder /project/webpack-stats.json /project/webpack-stats.json
# setup static assets
RUN mkdir -p /var/www/static \
  && mkdir -p /var/www/chameleoncloud.org/static \
  && python manage.py collectstatic --noinput

EXPOSE 80 443
