
# This isn't a Django application

This directory has the information and configuration files needed to run the Chameleon portal out of Docker.

## Installing Docker

[Install Docker](http://docs.docker.com/installation/) on your system

For CentOS 6 all you need to do is:
'''
$ sudo yum install docker-io
'''

## For Portal development
'''
    $ cd $HOME
    $ git clone git@github.com:ChameleonCloud/portal.git
'''
* We’ll just use the code and data out of here - it won’t be in a docker volume

'''
    $ cd portal/docker/django
    $ sudo docker build -i -t chameleoncloud/django .
'''
* create a docker image with the django packages we need
* saw a debconf warning about TERM, tty - maybe the -i will get rid of that

'''
    $ sudo docker run -v $HOME/portal:/portal -p 9000:80 -t chameleoncloud/django
'''
* creates a container from the image
  * mounts $HOME/portal from the local file system into the container at /portal
  * bind port 80 of the container to port 9000
