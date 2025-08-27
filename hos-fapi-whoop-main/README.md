# hos-fapi-whoop-main

WHOOP Health Data Microservice - MVP Implementation

## Overview

This is a standalone FastAPI microservice that handles WHOOP health data integration. It operates as an internal service called by the main entry point API (`hos-fapi-hm-sahha-main`) when WHOOP data is needed.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Run the service:
```bash
python -m app.main
```

## Documentation

See the `/documentation` folder for complete implementation plans and architecture details.

## Project Structure

```
hos-fapi-whoop-main/
├── app/                    # FastAPI application
│   ├── api/               # API route handlers  
│   ├── services/          # Business logic
│   ├── models/            # Data models
│   ├── config/            # Configuration
│   ├── utils/             # Utilities
│   └── security/          # Security utilities
├── documentation/         # Complete project documentation
├── migrations/            # Database migrations
├── tests/                 # Test suites
└── docker/               # Docker configuration
```

## Development

This is an MVP implementation focused on:
- Sequential data processing
- Basic error handling  
- Simple authentication
- Core WHOOP API integration

Future versions will add parallel processing, advanced caching, and real-time features.