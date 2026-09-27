#!/bin/bash
cp weewx.conf /etc/weewx && chown weewx:weewx /etc/weewx/weewx.conf
weectl extension install dist/aurorawx-1.0.0.tar.gz --yes && systemctl restart weewx && echo "WeeWX restarted"
