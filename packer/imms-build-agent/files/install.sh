#!/usr/bin/env bash

set -e

# user tools install

export PYENV_ROOT="/home/agent/.pyenv"

# poetry (version is fixed until we upgrade the base ubuntu and python version)
curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.8.5 python3 -
export PATH=${HOME}/.local/bin:$PATH

echo '' >> ~/.profile
echo '' >> ~/.profile

echo 'export PATH="/home/agent/.rvm/bin:/home/agent/.local/bin:/home/agent/.poetry/bin:/home/agent/.tfenv/bin:/home/agent/.pyenv/bin:/home/agent/bin:$PATH"' >> ~/.profile
echo 'eval "$(pyenv init -)"' >> ~/.profile
echo '' >> ~/.profile
echo 'eval "$(direnv hook bash)"' >> ~/.profile
echo '' >> ~/.profile

git clone https://github.com/pyenv/pyenv.git ~/.pyenv
git clone https://github.com/tfutils/tfenv.git ~/.tfenv


# Recent version of docker-buildx
echo "Installing recent docker buildx..."
mkdir -p ~/.docker/cli-plugins
curl -L  https://github.com/docker/buildx/releases/download/v0.9.1/buildx-v0.9.1.linux-amd64 -o ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx

echo "********************************************"
echo "ls -ltrh ~/.docker/cli-plugins/docker-buildx"
ls -ltrh ~/.docker/cli-plugins/docker-buildx
echo "********************************************"

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh | bash

source ~/.profile
export PATH="~/.rvm/bin:~/.poetry/bin:~/.local/bin:~/.tfenv/bin:~/.pyenv/bin:~/bin:${PATH}"

# install versions
for version in 3.8.2 3.8.10 3.9.5 3.10.8; do
  pyenv install "${version}"
  mkdir -p "/agent/_work/_tool/Python/${version}"
  ln -s "${HOME}/.pyenv/versions/${version}/" "/agent/_work/_tool/Python/${version}/x64"
  touch "/agent/_work/_tool/Python/${version}/x64.complete"
done

tfenv install 0.13.6
tfenv install 0.14.6
tfenv install 0.14.10
tfenv install 0.14.11
tfenv install 0.15.1
tfenv install 1.0.0
tfenv install 1.1.6
tfenv install 1.2.3
tfenv install 1.3.4

tfenv use 0.14.11


mkdir -p ~/bin && curl -s https://bitbucket.org/mjensen/mvnvm/raw/master/mvn > ~/bin/mvn && chmod 0755 ~/bin/mvn

source ~/.nvm/nvm.sh

for version in 14.21.1 16.18.1 18.12.1; do
    nvm install v${version};
    npm_major_version=$(echo ${version} | cut -c1-2)
    nvm use ${npm_major_version}
    nvm install-latest-npm
    # Symlink our installed version to where azure devops agent expects to find it...
    mkdir -p /agent/_work/_tool/node/$version
    ln -s "$HOME/.nvm/versions/node/v${version}/" /agent/_work/_tool/node/${version}/x64
    touch /agent/_work/_tool/node/${version}/x64.complete
done
# Add the final version in the loop do the default PATH
echo PATH="export PATH=/agent/_work/_tool/node/${version}/x64:$PATH" >> ~/.profile