RECEIPT PROCESSOR
================

[![FastAPI](https://img.shields.io/badge/FastAPI-0.103.1-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-20.10+-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A containerized REST API service for processing retail receipts and calculating reward points.

## 🚀 Quick Start with Docker

```bash
# Clone and build
git clone https://github.com/yourusername/receipt-processor.git
cd receipt-processor
docker build -t receipt-processor .

# Run container
docker run -d -p 8000:8000 --name receipt-api receipt-processor

# Verify it's running
curl http://localhost:8000/docs
```

### Test the API

```bash
# Process a receipt
curl -X POST http://localhost:8000/receipts/process \
  -H "Content-Type: application/json" \
  -d '{
    "retailer": "Target",
    "purchaseDate": "2022-01-01",
    "purchaseTime": "13:01",
    "items": [
      {
        "shortDescription": "Mountain Dew 12PK",
        "price": "6.49"
      }
    ],
    "total": "6.49"
  }'

# Sample response:
# {"id": "adb6b560-0eef-42bc-9d16-df48f30e89b2"}

# Get points for the receipt
curl http://localhost:8000/receipts/adb6b560-0eef-42bc-9d16-df48f30e89b2/points

# Sample response:
# {"points": 15}
```

## 📚 API Specification

### Endpoints

#### 1. Process Receipt
- **Path**: `/receipts/process`
- **Method**: `POST`
- **Request Schema**:
```json
{
    "retailer": "string",         // Store name (alphanumeric, &, - and space)
    "purchaseDate": "YYYY-MM-DD", // ISO 8601 date format
    "purchaseTime": "HH:MM",      // 24-hour time format
    "items": [                    // At least one item required
        {
            "shortDescription": "string", // Alphanumeric, - and space
            "price": "string"            // Decimal format: ##.##
        }
    ],
    "total": "string"            // Decimal format: ##.##
}
```
- **Response**: `{"id": "uuid-string"}`

#### 2. Get Points
- **Path**: `/receipts/{id}/points`
- **Method**: `GET`
- **Response**: `{"points": integer}`

## 🔧 Docker Configuration

### Build Arguments
None required. Default configuration works out of the box.

### Environment Variables
- `PORT`: API port (default: 8000)
- `PYTHONUNBUFFERED`: Python output buffering (default: 1)
- `PYTHONDONTWRITEBYTECODE`: Python bytecode generation (default: 1)

### Container Management
```bash
# Stop container
docker stop receipt-api

# View logs
docker logs receipt-api

# Remove container
docker rm receipt-api

# Remove image
docker rmi receipt-processor
```

## 🎮 Points Calculation Rules

1. Retailer name: 1 point per alphanumeric character
2. Round dollar total (no cents): 50 points
3. Total is multiple of 0.25: 25 points
4. Every 2 items: 5 points
5. Description length multiple of 3: multiply price by 0.2 and round up
6. Odd purchase day: 6 points
7. Time between 2:00 PM and 4:00 PM: 10 points

## ⚡ Implementation Notes

- **Data Storage**: In-memory (non-persistent)
- **Performance**: Single-container, stateless design
- **Security**: Runs as non-root user
- **Validation**: Request validation via Pydantic models
- **Documentation**: OpenAPI/Swagger UI at `/docs`

## 🔍 Development

For those who want to develop without Docker:

```bash
# Requires Python 3.9+
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📋 Testing

```bash
# Run in Docker
docker exec receipt-api pytest

# Run locally
pytest
```