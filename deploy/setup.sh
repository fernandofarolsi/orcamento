#!/bin/bash

# Update system
sudo apt update
sudo apt install -y python3-venv python3-dev git libxml2-dev libxslt-dev zlib1g-dev libjpeg-dev

# Create virtual environment
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install gunicorn

# Setup Service
sudo cp deploy/orcamento.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable orcamento
sudo systemctl start orcamento

echo "Setup concluído! O app deve estar rodando em http://<IP-DO-PI>:5000"
