
# This is not a Django application

This directory has the information and configuration files needed to run the Chameleon portal out of Docker.

## Installing Docker

[Install Docker](http://docs.docker.com/installation/) on your system

For CentOS 6 all you need to do is:

```
$ sudo yum install docker-io
```

## Accessing a Running Container

Use nsenter to access a container instead of running a sshd in the container:

```
$ sudo docker run -v $HOME/bin:/target jpetazzo/nsenter
```
* Installs nsenter in $HOME/bin
```
$ sudo $HOME/bin/docker-enter container_name_or_ID /bin/bash
```


## For Portal development

```
$ cd $HOME
$ git clone git@github.com:ChameleonCloud/portal.git
```

* We’ll just use the code and data out of here - it won’t be in a docker volume

```
$ cd portal/docker/django
$ sudo docker build -t chameleoncloud/django .
```

* create a docker image with the django packages we need
* saw a debconf warning about TERM, tty - maybe the -i will get rid of that

```
$ sudo docker run -i -v $HOME/portal:/portal -p 9000:80 -t chameleoncloud/django
```

* creates a container from the image
  * mounts $HOME/portal from the local file system into the container at /portal
  * bind port 80 of the container to port 9000

