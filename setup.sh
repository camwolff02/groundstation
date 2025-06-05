### Install desired packages ###
sudo apt-get update 
sudo apt-get install -y libgl1 vim tmux 
cp .vimrc ~/.vimrc

### Install Protoc ###
# Replace VERSION with the desired version (e.g., 31.1)
VERSION=31.0
ARCH=$(uname -m)  # Detect architecture (e.g., x86_64)

# Download the precompiled binary
curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v${VERSION}/protoc-${VERSION}-linux-${ARCH}.zip

# Unzip the downloaded file
unzip protoc-${VERSION}-linux-${ARCH}.zip -d protoc-${VERSION}

# Move the binaries to a directory in your PATH
sudo mv protoc-${VERSION}/bin/protoc /usr/local/bin/
sudo mv protoc-${VERSION}/include/* /usr/local/include/

# Clean up
rm -rf protoc-${VERSION} protoc-${VERSION}-linux-${ARCH}.zip

### Install UV and init ###
curl -LsSf https://astral.sh/uv/install.sh | sh # install UV
source $HOME/.local/bin/env
uv sync

### Prepare protobufs ###
git submodule update --init --recursive
cd protobufs
protoc *.proto --python_out=..
cd ..

### Finally, upgrade all packages ###
sudo apt-get full-upgrade && sudo apt-get autoremove -y
