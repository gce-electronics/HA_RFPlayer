FROM mcr.microsoft.com/devcontainers/python:1-3.12

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Uninstall pre-installed formatting and linting tools
# They would conflict with our pinned versions
RUN \
    pipx uninstall pydocstyle \
    && pipx uninstall pycodestyle \
    && pipx uninstall mypy \
    && pipx uninstall pylint

RUN \
    curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor > yarn.gpg \
    && mv yarn.gpg /etc/apt/trusted.gpg.d/yarn.gpg \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        # Additional library needed by some tests and accordingly by VScode Tests Discovery
        bluez \
        ffmpeg \
        libudev-dev \
        libavformat-dev \
        libavcodec-dev \
        libavdevice-dev \
        libavutil-dev \
        libgammu-dev \
        libswscale-dev \
        libswresample-dev \
        libavfilter-dev \
        libpcap-dev \
        libturbojpeg0 \
        libyaml-dev \
        libxml2 \
        git \
        cmake \
        clang \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv system-wide
RUN pip3 install uv

USER vscode
ENV HOME=/home/vscode
WORKDIR $HOME

# Install node for semantic release
ENV NVM_VERSION=v0.40.1
ENV NVM_DIR=$HOME/.nvm
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh | bash
RUN . "$NVM_DIR/nvm.sh" && nvm install --lts

# Create default python virtual env
ENV VIRTUAL_ENV="$HOME/.local/ha-venv"
RUN uv venv ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

WORKDIR /workspaces/HacsRfPlayer

# Set the default shell to bash instead of sh
ENV SHELL=/bin/bash
