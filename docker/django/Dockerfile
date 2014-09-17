# Chameleon Portal
#
# VERSION               0.0.1

FROM      ubuntu:14.04
MAINTAINER Warren Smith <wsmith@tacc.utexas.edu>

RUN apt-get update

# best editor
RUN apt-get install -y emacs24-nox

RUN apt-get install -y mysql-client python-mysqldb

RUN apt-get install -y apache2

RUN apt-get install -y python-dev
RUN apt-get install -y python-pip
RUN pip install django

RUN apt-get install -y python-ldap
RUN pip install django-auth-ldap

RUN pip install django-simple-menu

RUN pip install django-markdown-deux

RUN apt-get install -y ruby
# the gem install fails sometimes with "too many connections" - just try again
RUN gem install sass
RUN pip install django-pipeline

RUN pip install django-helpdesk

EXPOSE 80

WORKDIR /portal
CMD python manage.py runserver 0.0.0.0:80
