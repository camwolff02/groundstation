### Install desired packages ###
sudo apt-get update 
sudo apt-get install -y libgl1 vim tmux 
cp .vimrc ~/.vimrc

### Install Protoc ###
# Replace VERSION with the desired version (e.g., 31.1)
# VERSION=29.5
VERSION=30.0
#ARCH=$(uname -m)  # Detect architecture (e.g., x86_64)
if [ $ARCH == aarch64 ]; then
	ARCH=aarch_64
fi

PROTOC_ZIP=protoc-${VERSION}-linux-${ARCH}.zip 
curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v${VERSION}/${PROTOC_ZIP}
sudo unzip -o $PROTOC_ZIP -d /usr/local bin/protoc
sudo unzip -o $PROTOC_ZIP -d /usr/local 'include/*'
rm -f $PROTOC_ZIP

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
sudo apt-get full-upgrade -y && sudo apt-get autoremove -y
