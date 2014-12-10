#!/bin/bash
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
sudo pip install virtualenv
sudo apt-get install python-dev
virtualenv $DIR/../piautomatorenv
source $DIR/../piautomatorenv/bin/activate
pip install -r $DIR/../conf/requirements-pi.txt