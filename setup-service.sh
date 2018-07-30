#!/bin/bash
set -x

mkdir -p /var/log/bathroomavailable
chown pi.pi /var/log/bathroomavailable
touch /var/log/bathroomavailable/bathroomavailable.log
chown pi.pi /var/log/bathroomavailable/bathroomavailable.log
cp bathroomavailable.service /lib/systemd/system/bathroomavailable.service
chmod 644 /lib/systemd/system/bathroomavailable.service
systemctl daemon-reload
systemctl enable bathroomavailable.service
systemctl start bathroomavailable.service
systemctl status bathroomavailable.service
