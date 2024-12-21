#!/usr/bin/env bash

PY310_V=$(pyenv versions | grep 3.10 | awk 'NR==1 {print $1; exit}')

if [[ -z "${PY310_V}" ]]; then
  echo "Python 3.10 not found"
  echo "Please install Python 3.10 using pyenv"
  exit 1
fi

pyenv local ${PY310_V}

if [ -d .venv ]; then
  echo "venv already exists"
  echo "To recreate venv, delete.venv and run this script again"
  exit 1
else
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip setuptools wheel six
fi

pip install --upgrade ipython
