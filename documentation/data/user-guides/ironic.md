---
title: Ironic User Guide
---

# Ironic User Guide

## Overview

Ironic is bare metal provisioning system that is integrated into the Openstack cloud platform.

## Images

### Creating an Image

Building images is slightly different than for normal Openstack systems.

Here we will build a custom CentOS 7 image. You will need to have sudo privileges on the build host.

    yum install git libguestfs-tools-c 
    cd ~
    git clone https://github.com/openstack/diskimage-builder.git
    wget http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud-20141129_01.qcow2c
    mkdir mnt
    guestmount --rw -a CentOS-7-x86_64-GenericCloud-20141129_01.qcow2c -m /dev/sda1 mnt

Build up your cloud.cfg file. Link to sample here: ![cloud.cfg](/static/documentation/cloud.cfg)

    cp ~/cloud.cfg mnt/etc/cloud/cloud.cfg
    guestunmount mnt
    export DIB_LOCAL_IMAGE=~/CentOS-7-x86_64-GenericCloud-20141129_01.qcow2c
    diskimage-builder/bin/disk-image-create centos7 baremetal -o CentOS-7
    glance image-create --name my-centos7-kernel --is-public False --progress --disk-format aki < CentOS-7.vmlinuz

Save id as $MY_VMLINUZ_UUID.

    glance image-create --name my-centos7-initrd --is-public False --progress --disk-format ari < CentOS-7.initrd

Save id as $MY_INITRD_UUID.

    glance image-create --name my-centos7 --is-public False --disk-format qcow2 --container-format bare --property kernel_id=$MY_VMLINUZ_UUID --property ramdisk_id=$MY_INITRD_UUID < CentOS-7.qcow2

**Please Note** that we include a *ccadmin* user. Please do not disable this account; it allows us to login to your instance for troubleshooting and security purposes.

### Updating / Altering an Image

    glance image-download image

## Booting A Node

You should be able to 
