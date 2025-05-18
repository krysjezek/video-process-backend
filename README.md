# Video Process Backend

A robust backend service for video processing with various effects, built with FastAPI and Celery.

## Features

- Video processing with effects
- Asynchronous task processing using Celery
- Object storage with MinIO
- Redis for task queue management
- Docker-based deployment
- Comprehensive test suite

## Prerequisites

- Docker and Docker Compose
- Make (for using Makefile commands)

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
API_KEY=your_api_key
MINIO_ACCESS_KEY=your_minio_access_key
MINIO_SECRET_KEY=your_minio_secret_key
```

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd video-process-backend
```

2. Build and start the services:
```bash
make build
make up
```

The services will be available at:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

## Available Commands

- Start services: `make up`
- Stop services: `make down`
- View logs: `make logs`
- Run tests: `make test`
- Rebuild services: `make build`

## Development

The project is containerized and ready for development. All necessary services (Redis, MinIO) are included in the Docker Compose setup.

### Code Quality

The project uses several tools for code quality:

- Black for code formatting
- Ruff for linting
- MyPy for type checking

Run all checks:
```bash
make lint
```

## Project Structure

```
.
├── app/                    # Main application code
├── assets/                 # Static assets
├── tests/                  # Test suite
├── uploads/               # Upload directory
├── docker-compose.yml     # Docker Compose configuration
├── Dockerfile            # Main Dockerfile
├── Dockerfile.test       # Test Dockerfile
├── pyproject.toml        # Project dependencies and configuration
└── requirements.txt      # Python dependencies
```

## API Documentation

Once the service is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]