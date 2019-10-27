# Dropzone-backup server

This is a lightweight HTTP server that provides an endpoint where users can drop (POST or PUT) files. It is a write-only
service - it is not possible to fetch the uploaded files from the server. It should be used behind a server side proxy
(nginx, apache haproxy etc.) with strong HTTPS encryption.

Features:

* Works with simple HTTPS, the clients can backup files from almost anywhere. It can traverse multiple NATs, goes
  through most firewalls and caching proxies.
* Dead simple, it is trivial to write your own client for backing up files.
* It has a simple upload page - you can use a browser to backup a file from any computer, without installing anything.
* There is a simple, portable Windows program that can be used with it ( https://github.com/nagylzs/dropzone-postfile )
* Does not require special permissions, the server can run with an unprivileged user.
* Works on Linux and Windows as a service (Windows setup instructions are coming soon.)
* Supports multiple users with configurable upload directories.

Planned features:

* CAPTCHA for anonymous uploads (right now where is no CATPCHA for anonymous uploads so you should disable it in
  production).


**WARNING** - this project is still under development!

## Installation

At this point of the development, installation instructions are given for Ubuntu Linux only. Instructions for
Windows are coming soon.

### Prerequisites

You need to have python 3 and pipenv. On ubuntu:

    sudo apt install python3 python3-pip git
    sudo python3 -m pip install pip --upgrade
    sudo python3 -m pip install pipenv --upgrade

### Download and configure

    git clone https://github.com/nagylzs/dropzone-backup-server.git
    cd dropzone-backup-server
    pipenv install

It is useful to create a "dzbackup" script for executing commands in this environment:

    #!/bin/bash
    set +v
    set -e
    DIR="$(dirname $(realpath $0))"
    export PYTHONPATH=.
    pipenv run python scripts/dzbackup.py ${@}

Then you need to create some users who will be able to upload files. It is also possible to allow anonymous
uploads, but there isn't any protection yet, so it is not recommended.

    ./dzbackup adduser --username someuser --prefix some/subdir

Finally, you can start the server:

    mkdir ~/dropzone
    .dzbackup serve --upload-base-dir ~/dropzone --auto-create-user-dirs -v

### Add as systemd service

First, you create a script for starting the server:

    #!/bin/bash
    cd /home/dropzone/dropzone-backup-server
    ./dzbackup.py serve --upload-base-dir /home/dropzone/dropzone --auto-create-user-dirs --pidfile ./dzbackup.pid

Then you create a new service file for systemd under /etc/systemd/system/dropzone-daemon.service

    [Unit]
    Description=The Dropzone-Backup file backup service
    After=syslog.target network.target remote-fs.target nss-lookup.target

    [Service]
    Type=simple
    PIDFile=/home/dropzone/dropzone-backup-server/dzbackup.pid
    ExecStart=/home/dropzone/start.sh
    ExecStop=/bin/kill -s QUIT $MAINPID
    PrivateTmp=true
    User=dropzone
    Group=dropzone

    [Install]
    WantedBy=multi-user.target

Install and start:

    sudo chown root:root /etc/systemd/system/dropzone-daemon.service
    sudo chmod 664 /etc/systemd/system/dropzone-daemon.service
    sudo systemctl daemon-reload
    sudo systemctl start dropzone-daemon
    sudo systemctl status dropzone-daemon

Enable to auto start on reboot:

    sudo systemctl enable dropzone-daemon

## Detailed description

TODO!