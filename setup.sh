sudo apt-get update 
sudo apt-get install -y libgl1 vim tmux protobuf-compiler
curl -LsSf https://astral.sh/uv/install.sh | sh # install UV
source $HOME/.local/bin/env
uv sync
cd protobufs
protoc *.proto --python_out=..
cd ..
cp .vimrc ~/.vimrc
sudo apt-get full-upgrade
