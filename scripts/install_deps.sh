#!/usr/bin/env bash

# this script assumes that you have prepared a venv
# using prepare_venv.sh

CUR_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

pip install git+https://github.com/facebook/pyre2
pip install \
  qt5reactor \
  psutil \
  Twisted \
  adblockparser \
  xvfbwrapper \
  funcparserlib \
  Pillow \
  lupa \
  PyQt5-sip

pip install git+https://github.com/benquike/scrapely
pip install git+https://github.com/benquike/scrapy-splash.git
pip install git+https://github.com/benquike/portia2code

pip install ${CUR_DIR}/../slybot/requirements.txt
pip install ${CUR_DIR}/../slydt/requirements.txt
pip install ${CUR_DIR}/../portia_server/requirements.txt
