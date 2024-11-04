FROM registry.izaber.com/devops/base-docker-images/ubuntu:20.04

# Make the src directory
USER root
RUN mkdir /src && chown -R zaber: /src
USER zaber

# Let's sit in the src directory by default
WORKDIR /src

USER root

RUN apt update ; apt install -y software-properties-common ; add-apt-repository ppa:deadsnakes/ppa \
    && apt install -y \
            build-essential \
            curl \
            git \
            libssl-dev \
            libxml2-dev \
            libxslt1-dev \
            python3-distutils \
            python3.8 \
            python3.8-dev \
            python3.8-venv \
            python3.9 \
            python3.9-distutils \
            python3.9-dev \
            python3.10 \
            python3.10-dev \
            python3.10-distutils \
            python3.11 \
            python3.11-dev \
            python3.11-distutils \
            python3.12 \
            python3.12-dev \
            python3.12-distutils \
            python3.13 \
            python3.13-dev \
            telnet \
            vim-nox \
    # Install pypy3
    && curl -L -o /tmp/pypy.tar.bz2 https://downloads.python.org/pypy/pypy3.10-v7.3.17-linux64.tar.bz2 && \
        tar -xjf /tmp/pypy.tar.bz2 -C /opt && \
        rm /tmp/pypy.tar.bz2 && \
        mv /opt/pypy3.10-v7.3.17-linux64 /opt/pypy3 \
    # Pip is handy to have around
    && curl https://bootstrap.pypa.io/get-pip.py -o /root/get-pip.py \
    && python3 /root/get-pip.py \
    # We also use Nox
    && python3 -m pip install nox \
    # Cleanup caches to reduce image size
    && python3 -m pip cache purge \
    && apt clean \
    && rm -rf ~/.cache \
    && rm -rf /var/lib/apt/lists/*

USER zaber

# Copy over the data files
COPY --chown=zaber:zaber . /src

ENV PATH=/home/zaber/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RUN /src/docker/setup-env.sh

CMD /src/docker/run-test.sh

