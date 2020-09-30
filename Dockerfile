FROM python:3.7.9-stretch
# MAINTAINER Alejandro Rocha <rochaa@tacc.utexas.edu>

RUN apt-get update \
  && curl -sL https://deb.nodesource.com/setup_6.x | bash \
  && apt-get install -y \
    nginx supervisor gettext curl build-essential nodejs ruby-sass ruby-compass \
  && rm -rf /var/lib/apt/lists/* \
  && pip install uwsgi \
  && npm install -g yuglify

CMD ["supervisord", "-n"]

COPY docker-conf /setup/docker-conf

# configure nginx, uwsgi, supervisord
RUN echo "daemon off;" >> /etc/nginx/nginx.conf \
    && rm /etc/nginx/sites-enabled/default \
    && ln -s /setup/docker-conf/nginx-app.conf /etc/nginx/sites-enabled/ \
    && ln -s /setup/docker-conf/supervisor-app.conf /etc/supervisor/conf.d/

COPY requirements.txt /setup/requirements.txt
COPY upper-constraints.txt /setup/upper-constraints.txt
# install pip dependencies
RUN pip install --upgrade pip \
    && pip install -r /setup/requirements.txt -c /setup/upper-constraints.txt

# setup project code
COPY . /project
WORKDIR /project

# logs
RUN mkdir /var/log/django

# translation messages, if necessary
RUN python manage.py compilemessages

# setup static assets
RUN mkdir -p /var/www/static \
  && mkdir -p /var/www/chameleoncloud.org/static \
  && python manage.py collectstatic --noinput

EXPOSE 80 443
