#!/bin/bash
cd `dirname $0`
apt install -y python3-venv
python3 -m venv venv
. venv/bin/activate
python3 -m main
