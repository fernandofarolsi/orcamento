#!/bin/bash

# Pull latest code
git pull

# Update dependencies
./venv/bin/pip install -r requirements.txt

# Restart service
sudo systemctl restart orcamento

echo "Atualizado com sucesso!"
