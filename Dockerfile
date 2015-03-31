FROM mrhanlon/python-nginx:latest

MAINTAINER Matthew R Hanlon <mrhanlon@tacc.utexas.edu>

# gettext for i18n
RUN apt-get install -y gettext

# kramdown for parsing static site content
RUN gem install kramdown

# copy requirements.txt, deps, and config separate from the rest of the project
COPY requirements.txt /setup/requirements.txt
COPY deps /setup/deps
COPY docker-conf /setup/docker-conf

# install pip dependencies
RUN pip install -r /setup/requirements.txt

# install non-pip dependencies
RUN cd /setup/deps/pytas && python setup.py install

# configure nginx, uwsgi, supervisord
RUN \
    echo "daemon off;" >> /etc/nginx/nginx.conf \
    && rm /etc/nginx/sites-enabled/default \
    && ln -s /setup/docker-conf/nginx-app.conf /etc/nginx/sites-enabled/ \
    && ln -s /setup/docker-conf/supervisor-app.conf /etc/supervisor/conf.d/

# setup project code
COPY . /project
WORKDIR /project


# logs
RUN mkdir /var/log/django


# database migrations, if necessary
# maybe remove this in the future? - @mrhanlon
RUN python manage.py migrate


# translation messages, if necessary
RUN python manage.py compilemessages


# setup static assets
RUN mkdir -p /var/www/static && mkdir -p /var/www/chameleoncloud.org/static && python manage.py collectstatic --noinput


EXPOSE 80 443
CMD ["supervisord", "-n"]
