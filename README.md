# Plans Assistant

A Streamlit application that uses LangGraph with Claude to query plan information from a database and API.

## Features

- Natural language interface for querying plan information
- Integration with MySQL database for plan data
- API integration for detailed plan information
- LangGraph agent architecture with Claude for natural language processing
- Streamlit UI for easy interaction

## Local Development Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose

### Running Locally with Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/kaarthi611/plans-assistant.git
   cd plans-assistant
   ```

2. Create an `.env` file with your configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

3. Build and run the Docker container:
   ```bash
   docker-compose up -d
   ```

4. Access the application at [http://localhost:8501](http://localhost:8501)

### Running Locally without Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/plans-assistant.git
   cd plans-assistant
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create an `.env` file with your configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

5. Start the application:
   ```bash
   streamlit run app.py
   ```

6. Access the application at [http://localhost:8501](http://localhost:8501)

## Deployment

### AWS EC2 Deployment

1. Launch an EC2 instance with Amazon Linux 2023 or Ubuntu Server.

2. Configure security groups:
   - Allow SSH (port 22) from your IP
   - Allow HTTP (port 80) from anywhere (if using Nginx)
   - Allow port 8501 from anywhere (if accessing Streamlit directly)

3. Connect to your instance:
   ```bash
   ssh -i your-key.pem ec2-user@your-instance-public-ip
   ```

4. Copy the setup script and run it:
   ```bash
   # Copy setup-ec2.sh to the instance
   scp -i your-key.pem deployment/aws-ec2/setup-ec2.sh ec2-user@your-instance-public-ip:~/

   # SSH into instance and run the script
   ssh -i your-key.pem ec2-user@your-instance-public-ip
   chmod +x setup-ec2.sh
   ./setup-ec2.sh
   ```

5. Upload configuration files:
   ```bash
   # From your local machine
   scp -i your-key.pem .env ec2-user@your-instance-public-ip:~/plans-assistant/
   scp -i your-key.pem deployment/aws-ec2/docker-compose.prod.yml ec2-user@your-instance-public-ip:~/plans-assistant/docker-compose.yml
   ```

6. Start the application:
   ```bash
   # SSH into your instance
   ssh -i your-key.pem ec2-user@your-instance-public-ip
   
   # Start the application
   cd ~/plans-assistant
   docker-compose up -d
   ```

7. Access your application at `http://your-instance-public-ip:8501`

## Monitoring and Logs

To view logs from your Docker container:
```bash
docker logs -f plans-assistant
```

## Troubleshooting

If you encounter issues:

1. Check if the container is running:
   ```bash
   docker ps
   ```

2. Check container logs:
   ```bash
   docker logs plans-assistant
   ```

3. Verify environment variables:
   ```bash
   docker exec plans-assistant env
   ```

4. Ensure the DB and API are accessible from the container:
   ```bash
   docker exec -it plans-assistant bash
   ping your-db-host
   curl your-api-url:8080
   ```

5. Common errors:
   - "invalid x-api-key" - Check your ANTHROPIC_API_KEY value
   - Database connection failures - Verify DB_HOST and credentials
   - API connection errors - Check API_BASE_URL and network connectivity
