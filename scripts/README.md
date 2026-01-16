# Scripts

## create_api_key.py

Script to create a new API key for the Health Insurance API.

### Usage

**Local (outside Docker):**
```bash
python scripts/create_api_key.py --name "My API Key" --description "Description here"
```

**Inside Docker container:**
```bash
docker exec api_health_insurance-api-1 python scripts/create_api_key.py --name "My API Key" --description "Description here"
```

### Arguments

- `--name` (required): Name for the API key
- `--description` (optional): Description for the API key

### Example

```bash
python scripts/create_api_key.py --name "Backend Service" --description "API key for backend service integration"
```

### Output

The script will:
1. Generate a secure random API key
2. Hash and store it in the database
3. Display the plain text API key **once** (save it immediately!)

### Important Notes

- The plain text API key is only shown once during creation
- Store the API key securely
- Use the API key in the `X-API-Key` header for authenticated requests
- API keys do not expire (as per requirements)

