# TruthGit API Reference

## Base URL

**Production:** `https://truthgit-production.up.railway.app`

## Authentication

Currently, the API is open. Authentication will be added in a future release.

## Endpoints

### Health Check

```http
GET /
```

**Response:**
```json
{
  "name": "TruthGit API",
  "version": "0.4.0",
  "status": "healthy",
  "docs": "/docs"
}
```

---

### Verify Claim

Verify a claim using multi-validator AI consensus.

```http
POST /api/verify
Content-Type: application/json
```

**Request Body:**
```json
{
  "claim": "Water boils at 100 degrees Celsius at sea level",
  "domain": "physics"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "passed": true,
    "consensus": 0.94,
    "validators": [
      {
        "name": "CLAUDE",
        "confidence": 0.95,
        "reasoning": "Accurate under standard atmospheric pressure..."
      },
      {
        "name": "LOGOS6",
        "confidence": 0.93,
        "reasoning": "Verified with Logos principles..."
      }
    ],
    "claimHash": "a7f3b2c1",
    "timestamp": "2026-01-03T00:45:53.304741Z"
  },
  "error": null,
  "meta": {
    "timestamp": "2026-01-03T00:45:53.304760Z",
    "processingTime": 9244
  }
}
```

**Domains:**
- `physics` - Physical sciences
- `math` - Mathematics
- `history` - Historical facts
- `programming` - Software/coding
- `general` - Default domain

---

### Generate Proof

Generate a cryptographic proof certificate for a verified claim.

```http
POST /api/prove
Content-Type: application/json
```

**Request Body:**
```json
{
  "claim": "E=mc²",
  "domain": "physics",
  "format": "json"
}
```

**Parameters:**
- `format`: `json` (default) or `compact` (base64)

**Response:**
```json
{
  "success": true,
  "data": {
    "certificate": {
      "version": "1.0.0",
      "claim_hash": "abc123...",
      "claim_content": "E=mc²",
      "claim_domain": "physics",
      "consensus_value": 0.94,
      "consensus_passed": true,
      "validators": ["CLAUDE", "LOGOS6"],
      "timestamp": "2026-01-03T00:00:00Z",
      "signature": "base64..."
    }
  }
}
```

---

### Verify Proof

Verify a proof certificate.

```http
POST /api/verify-proof
Content-Type: application/json
```

**Request Body:**
```json
{
  "certificate": { ... }
}
```

Or with compact format:
```json
{
  "certificate": "base64-encoded-certificate..."
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "message": "Valid proof: 94% consensus from 2 validators",
    "claim": {
      "content": "E=mc²",
      "domain": "physics"
    },
    "verification": {
      "consensus": 0.94,
      "validators": ["CLAUDE", "LOGOS6"],
      "timestamp": "2026-01-03T00:00:00Z"
    }
  }
}
```

---

### Search Claims

Search for verified claims in the repository.

```http
GET /api/search?query=boiling&domain=physics&limit=10
```

**Query Parameters:**
- `query` (required): Search text
- `domain` (optional): Filter by domain
- `limit` (optional): Max results (1-100, default 10)

---

### Repository Status

Get repository status and statistics.

```http
GET /api/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "initialized": true,
    "objectCounts": {
      "claims": 42,
      "axioms": 5,
      "verifications": 38,
      "contexts": 3
    },
    "consensusThreshold": 0.66,
    "repoId": "abc123..."
  }
}
```

---

## Debug Endpoints

### Test Claude Validator

```http
GET /api/debug/test-claude
```

Returns raw Claude API response for debugging.

### Check Validators

```http
GET /api/debug/validators
```

Returns status of all validators and environment configuration.

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "success": false,
  "data": null,
  "error": "Error message describing what went wrong",
  "meta": {
    "timestamp": "2026-01-03T00:00:00Z",
    "processingTime": 150
  }
}
```

## Rate Limits

Currently no rate limits. Subject to change.

## Code Examples

### Python

```python
import httpx

API_URL = "https://truthgit-production.up.railway.app"

# Verify a claim
response = httpx.post(f"{API_URL}/api/verify", json={
    "claim": "The speed of light is approximately 300,000 km/s",
    "domain": "physics"
})
result = response.json()
print(f"Consensus: {result['data']['consensus']:.0%}")
```

### JavaScript

```javascript
const API_URL = "https://truthgit-production.up.railway.app";

// Verify a claim
const response = await fetch(`${API_URL}/api/verify`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    claim: "Python was created by Guido van Rossum",
    domain: "programming"
  })
});
const result = await response.json();
console.log(`Passed: ${result.data.passed}`);
```

### cURL

```bash
curl -X POST https://truthgit-production.up.railway.app/api/verify \
  -H "Content-Type: application/json" \
  -d '{"claim": "Water is H2O", "domain": "chemistry"}'
```
