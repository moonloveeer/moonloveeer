# QRL Web Wallet API Documentation

## Overview
The QRL Web Wallet provides a RESTful API for interacting with the QRL blockchain.

## Base URL
```
http://localhost:5001
```

## Authentication
Most endpoints require authentication via JWT token in cookies.

## Endpoints

### Wallet Management

#### Create Wallet
```http
POST /register
Content-Type: application/json

{
  "password": "your_password"
}
```

#### Login (Web3)
```http
POST /web3/init-login
Content-Type: application/json

{
  "address": "0x..."
}
```

#### Verify Web3 Login
```http
POST /web3/verify
Content-Type: application/json

{
  "address": "0x...",
  "signature": "0x..."
}
```

### Transactions

#### Send Transaction
```http
POST /send
Content-Type: application/x-www-form-urlencoded

recipient=Q...&amount=100.0
```

#### Mine Block
```http
POST /mine
Authorization: Bearer <jwt_token>
```

### Blockchain Data

#### Get Blocks
```http
GET /api/blocks?count=10&offset=0
```

#### Get Block Details
```http
GET /api/block/<block_hash>
```

#### Get Transactions
```http
GET /api/transactions?limit=10&pending=true
```

#### Get Transaction Details
```http
GET /api/transaction/<tx_hash>
```

#### Get Wallet Details
```http
GET /api/wallet/<address>
```

### Payment Processing

#### Initiate Purchase
```http
POST /api/buy/initiate
Content-Type: application/json

{
  "amount": 100.0
}
```

#### Check Payment Status
```http
GET /api/buy/status/<payment_id>
```

## Error Responses

All endpoints return appropriate HTTP status codes:
- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `429` - Too Many Requests (Rate Limited)
- `500` - Internal Server Error

Error response format:
```json
{
  "error": "Error message description"
}
```

## Rate Limits
- Default: 200 requests per day, 50 per hour
- Login: 5 requests per minute
- Mining: 10 requests per minute
- Send Transaction: 20 requests per minute

## WebSocket Connection
Real-time updates available via WebSocket at:
```
ws://localhost:5001/ws
```

## Security Notes
- All sensitive endpoints require authentication
- CSRF protection enabled
- Rate limiting implemented
- Security events logged to `security.log`
