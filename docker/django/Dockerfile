# Chameleon Portal
#
# VERSION               0.0.1

FROM      ubuntu:14.04
MAINTAINER Warren Smith <wsmith@tacc.utexas.edu>

# this may get rid of TERM errors
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update

# need a good editor :-P
RUN apt-get install -y emacs24-nox

# for later
#RUN apt-get install -y mysql-client python-mysqldb
#RUN apt-get install -y apache2

RUN apt-get install -y python-dev
RUN apt-get install -y python-pip
RUN pip install django

RUN pip install django-countries

RUN pip install django-simple-menu

RUN apt-get install -y ruby
# the gem install fails sometimes with "too many connections" - just try again
RUN gem install sass
RUN pip install django-pipeline

RUN pip install django-bootstrap-form
RUN pip install django-markdown-deux
RUN pip install email-reply-parser
# the version of helpdesk currently available with pip doesn't work with django 1.7
#RUN pip install django-helpdesk
# so install it from git
RUN apt-get install -y git
WORKDIR /tmp
RUN git clone https://github.com/rossp/django-helpdesk.git
WORKDIR /tmp/django-helpdesk
# version from 9/18/2014
RUN git checkout -b 863effdcb6f956171193607662da03efd5ce97fb
RUN python setup.py install
RUN rm -rf /tmp/django-helpdesk

RUN apt-get install -y libtiff4-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.5-dev tk8.5-dev python-tk
RUN pip install pillow


RUN apt-get install -y libxml2-dev libxslt1-dev

# this doesn't seem to be working quite right
#RUN pip install django_openstack_auth
# so try from git
#RUN apt-get install -y python-pbr
#WORKDIR /tmp
#RUN git clone https://github.com/openstack/django_openstack_auth.git
#WORKDIR /tmp/django_openstack_auth
# version from 9/21/2014
#RUN git checkout -b b2c06648f48eeecc1c7572492dd220c41f436172
#RUN python setup.py install
#RUN rm -rf /tmp/django_openstack_auth
# a custom version of openstack_auth outside of the container needs:
#RUN apt-get install -y python-keystoneclient
#RUN pip install pbr

RUN apt-get install -y python-ldap
RUN pip install django-auth-ldap

RUN pip install django-password-reset
# django-registration is no longer maintained
# django-allauth has a password reset that we could use
RUN pip install django-allauth

EXPOSE 80

WORKDIR /portal
CMD python manage.py runserver 0.0.0.0:80
