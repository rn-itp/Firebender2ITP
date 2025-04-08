# Firebender2ITP

A proxy service for Firebender to interact with OpenAI compatible servers. It can translates between Anthropic and OpenAI API formats, allowing Firebender to interact with OpenAI-compatible APIs using Anthropic's API schema.
OpenAI type of requests will just be forwarded.
## Overview

Firebender2ITP acts as a middleware that:

1. Receives requests in Anthropic or OpenAI format
2. Converts them to OpenAI format (if necessary)
3. Forwards the request to an OpenAI-compatible API endpoint
4. Converts the response back to Anthropic format (if this is what was received)
5. Returns the response to the client

This allows tools like Firebender to communicate with OpenAI-compatible services using Anthropic's API schema.

## Prerequisites

Either:
- Python 3.11 or higher
- Docker

## Configuration

Modify the `.env` file with your data.

```
OPENAI_API_KEY=(insert-key)
OPENAI_API_URL=(insert-url)
```

## Running with Python

1. Clone this repository
2. Make sure to have Python installed
3. Run the provided script:

```bash
chmod +x run.sh
./run.sh
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Start the server on port 8000

## Running with Docker compose

```bash
docker-compose up
```

## Usage with Firebender

Configure Firebender to use this proxy by setting the API URLs:

### For Anthropic format:
- Set API URL to: `http://0.0.0.0:8000/v1`

### For OpenAI format:
- Set API URL to: `http://0.0.0.0:8000/v1`

## Health Check

Verify the service is running:

```bash
curl http://localhost:8000/health
```