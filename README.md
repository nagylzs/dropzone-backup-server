# Dropzone-backup server

This is a lightweight HTTP server that provides an endpoint where users can drop (POST or PUT) files. It is a write-only
service, it is not possible to fetch the uploaded files from the server.

**WARNING** - this project is still under development!

## Installation

At this point of the development, installation instructions are given for debian based Linux only.

### Prerequisites

You need to have python 3 and pipenv. On ubuntu:

    sudo apt install python3 python3-pip git
    sudo python3 -m pip install pip --upgrade
    sudo python3 -m pip install pipenv --upgrade

### Download and configure

    git clone https://github.com/nagylzs/dropzone-backup-server.git
    cd dropzone-backup-server
    pipenv install # you might need to specity --python



It is recommended that you create an unprivileged user that will run the server.

    sudo adduser dropzone