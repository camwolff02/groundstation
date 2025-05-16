sudo apt update 
sudo apt install libgl1 vim -y
curl -LsSf https://astral.sh/uv/install.sh | sh # install UV
source $HOME/.local/bin/env
uv sync
sudo apt full-upgrade
