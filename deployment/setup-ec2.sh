#!/bin/bash

# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p ~/plans-assistant

# Note to user: Next steps would be to upload .env and docker-compose.prod.yml files
echo "Setup complete! Next steps:"
echo "1. Upload your .env file to ~/plans-assistant/.env"
echo "2. Upload docker-compose.prod.yml to ~/plans-assistant/docker-compose.yml"
echo "3. Run 'docker-compose up -d' to start the application"