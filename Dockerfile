FROM ubuntu:22.04
WORKDIR /app/slyd

# ENV PATH="/opt/qt59/5.9.1/gcc_64/bin:${PATH}"
ENV DEBIAN_FRONTEND=noninteractive
# ENV QT_MIRROR http://ftp.fau.de/qtproject/official_releases/qt/5.9/5.9.1/qt-opensource-linux-x64-5.9.1.run
# ENV QT_MIRROR https://master.qt.io/new_archive/qt/5.9/5.9.1/qt-opensource-linux-x64-5.9.1.run


RUN apt-get update
RUN apt-get install -y --no-install-recommends \
        curl \
        software-properties-common \
        apt-transport-https \
        python3-software-properties \
        ca-certificates \
        pkg-config \
        netbase \
        nginx

RUN apt install -y qtcreator qtbase5-dev qt5-qmake

RUN apt-get install --no-install-recommends -y \
        fonts-liberation \
        ttf-wqy-zenhei \
        fonts-arphic-gbsn00lp \
        fonts-arphic-bsmi00lp \
        fonts-arphic-gkai00mp \
        fonts-arphic-bkai00mp \
        fonts-beng && \
    echo ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true | debconf-set-selections && \
    apt-get install --no-install-recommends -y ttf-mscorefonts-installer


RUN apt install -y  libqt5webkit5-dev
RUN apt install -y python3-pyqt5.qtsvg python3-pyqt5.qtwebkit

RUN apt-get install -y git

RUN apt-get install -y --no-install-recommends \
          libmysqlclient-dev \
            python3-mysql.connector \
            python3-numpy \
            python3-openssl

RUN apt-get install -y --no-install-recommends \
        python3 \
        python3-dev \
        nodejs

RUN apt-get install -y --no-install-recommends python3-pip
RUN apt-get install -y build-essential
RUN apt-get install -y vim

# RUN curl https://pyenv.run | bash

# RUN echo 'export PYENV_ROOT="$HOME/.pyenv"' >> $HOME/.bashrc
# RUN echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> $HOME/.bashrc
# RUN echo 'eval "$(pyenv init -)"' >> $HOME/.bashrc

# ENV HOME  /root
# ENV PYENV_ROOT $HOME/.pyenv
# ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

# RUN apt-get install -y liblzma-dev \
#                       libncursesw5-dev \
#                       libsqlite3-dev \
#                       libreadline-dev \
#                       libbz2-dev \
#                       libffi-dev \
#                       libssl-dev \
#                       libgdbm-dev \
#                       zlib1g-dev \
#                       libjpeg-dev \
#                       libtiff-dev \
#                       libpq-dev \
#                       libxml2-dev \
#                       libxslt1-dev \
#                       libsdl2-dev \
#                       libgstreamer-plugins-base1.0-dev \
#                       libnotify-dev \
#                       freeglut3-dev \
#                       libsm-dev \
#                       libgtk-3-dev \
#                       libwebkitgtk-6.0-dev \
#                       libxtst-dev

# RUN pyenv install 3.7.17
# RUN pyenv global 3.7.17

# RUN pyenv install 3.9.21
# RUN pyenv global 3.9.21

RUN pip install pip -U

RUN apt-get install -y libre2-dev

# RUN pip install git+https://github.com/sunu/pyre2
RUN pip install git+https://github.com/facebook/pyre2

RUN pip install numpy

RUN pip install setuptools six && \
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



# RUN apt-get install -y --no-install-recommends \
#        liblua5.4-dev \
#        zlib1g \
#        zlib1g-dev

COPY docker/portia.conf /app/portia.conf
COPY docker/qt_install.qs /app/script.qs
COPY docker/provision.sh /app/provision.sh

RUN pip install git+https://github.com/benquike/scrapely
RUN pip install git+https://github.com/benquike/scrapy-splash.git

RUN pip install git+https://github.com/benquike/portia2code

COPY slybot/requirements.txt /app/slybot/requirements.txt
COPY slyd/requirements.txt /app/slyd/requirements.txt
COPY portia_server/requirements.txt /app/portia_server/requirements.txt

RUN pip install -r "/app/slyd/requirements.txt"
RUN pip install -r "/app/portia_server/requirements.txt"

RUN pip install -r "/app/slybot/requirements.txt"

ADD docker/nginx /etc/nginx
ADD . /app
RUN pip install -e /app/slyd
RUN pip install -e /app/slybot

RUN python3 /app/portia_server/manage.py migrate

EXPOSE 9001
ENTRYPOINT ["/app/docker/entry"]
