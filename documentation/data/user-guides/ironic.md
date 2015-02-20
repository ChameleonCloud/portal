---
title: Ironic User Guide
---

# Ironic User Guide

## Overview

Ironic is bare metal provisioning system that is integrated into the OpenStack cloud platform.

## Chameleon Default Environment 

We provide an initial CentOS 7 image (called CC-CentOS7 in Nova/Glance). It has the following characteristics:

* A *cc* user for users to access to the system. It has passwordless sudo access. 
* Auto-login from the console.
* Standard development tools such as make, gcc, gfortran, etc.
* A few config management apps such as Puppet, Ansible, etc.
* The EPEL & OpenStack-Juno yum repositories.
* A *ccadmin* user for Chameleon administrative staff access. Please do not disable this account; it allows us to login to your instance for troubleshooting and security purposes.
 
## Images

### Creating an Image

Building images is slightly different than for normal OpenStack systems.

Here we will build a custom CentOS 7 image. Run these commands as root.

    export LIBGUESTFS_BACKEND=direct
    yum install git libguestfs-tools-c 
    cd ~
    git clone https://github.com/openstack/diskimage-builder.git
    wget http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud-20141129_01.qcow2c
    export DIB_LOCAL_IMAGE=~/CentOS-7-x86_64-GenericCloud-20141129_01.qcow2c
    diskimage-builder/bin/disk-image-create centos7 baremetal -o CC-CentOS7
    glance image-create --name CC-CentOS7-kernel --is-public True --progress --disk-format aki < CC-CentOS7.vmlinuz

Save id as $VMLINUZ_UUID.

    glance image-create --name CC-CentOS7-initrd --is-public True --progress --disk-format ari < CC-CentOS7.initrd

Save id as $INITRD_UUID.

    glance image-create --name CC-CentOS7 --is-public True --disk-format qcow2 --container-format bare --property kernel_id=$VMLINUZ_UUID --property ramdisk_id=$INITRD_UUID < CC-CentOS7.qcow2

    This provides a generic CentOS 7 image. In the next section we will customize it.

### Updating / Altering an Image

    glance image-download CC-CentOS7 > CC-CentOS7.custom.qcow2

    mkdir mnt
    guestmount --rw -a CC-CentOS7.custom.qcow2 -i mnt

Configure your cloud.cfg file & make any other changes you like. Here is a link to the cloud-init documentation:[http://cloudinit.readthedocs.org/en/latest/index.html]

    vi mnt/etc/cloud/cloud.cfg
    guestunmount mnt

Note we re-use the VMLINUZ_UUID & INITRD_UUID from the previous section.

    glance image-delete CC-CentOS7
    glance image-create --name CC-CentOS7 --is-public True --disk-format qcow2 --container-format bare --property kernel_id=$VMLINUZ_UUID --property ramdisk_id=$INITRD_UUID < CC-CentOS7.custom.qcow2

## Booting A Node

You should now be able to boot a node with standard nova commands, for example:

    nova boot --flavor my-baremetal-flavor --image CC-CentOS7 --key-name default --nic net-id=d4e6c5e0-0477-4efd-bd2e-a25ccc960de7 my-centos-instance

