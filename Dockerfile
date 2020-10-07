FROM python:3.7.9-stretch

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
