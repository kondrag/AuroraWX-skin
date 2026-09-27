#!/bin/bash
set -e
.venv/bin/python tools/gen_install.py
git ls-files --cached --others --exclude-standard install.py bin skins -z |
  xargs -0 tar czf dist/aurorawx-1.0.0.tar.gz --transform 's#^#aurorawx/#'
cp weewx.conf /etc/weewx && chown weewx:weewx /etc/weewx/weewx.conf
weectl extension install dist/aurorawx-1.0.0.tar.gz --yes && systemctl restart weewx && echo "WeeWX restarted"
