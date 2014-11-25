FROM mrhanlon/python-nginx:latest

MAINTAINER Matthew R Hanlon <mrhanlon@tacc.utexas.edu>

# kramdown for parsing static site content
RUN gem install kramdown

# setup project code
COPY . /project
WORKDIR /project

# install non-pip dependencies
RUN cd deps/pytas && python setup.py install && cd ../python-rt && python setup.py install

# install pip dependencies
RUN pip install -r requirements.txt

# configure nginx, uwsgi, supervisord
RUN \
    echo "daemon off;" >> /etc/nginx/nginx.conf \
    && rm /etc/nginx/sites-enabled/default \
    && ln -s /project/docker-conf/nginx-app.conf /etc/nginx/sites-enabled/ \
    && ln -s /project/docker-conf/supervisor-app.conf /etc/supervisor/conf.d/

# database migrations, if necessary
RUN python manage.py migrate

# setup static assets
RUN mkdir -p /var/www/static && mkdir -p /var/www/chameleoncloud.org/static && python manage.py collectstatic --noinput

EXPOSE 80 443
CMD ["supervisord", "-n"]
