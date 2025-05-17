sudo apt-get update 
sudo apt-get install -y libgl1 vim protobuf-compiler
curl -LsSf https://astral.sh/uv/install.sh | sh # install UV
source $HOME/.local/bin/env
uv sync
sudo apt-get full-upgrade
