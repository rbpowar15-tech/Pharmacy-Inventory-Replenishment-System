# Inventory API

Containerized REST API running on Azure VMs (Inventory API 01 & 02) behind Application Gateway.

## Endpoints
| Method | Endpoint                              | Description                        |
|--------|---------------------------------------|------------------------------------|
| GET    | /health                               | Health check for gateway probe     |
| GET    | /inventory/{pharmacyId}               | Get all medicines for a pharmacy   |
| PUT    | /inventory/{pharmacyId}/{medicineCode}| Update stock level                 |
| POST   | /replenishments                       | Trigger replenishment for low stock|
| GET    | /replenishments/{id}                  | Get replenishment request status   |

## Running Locally
1. Copy `.env.example` to `.env` and fill in values
2. Set `USE_SQL_LOGIN=true` for local development
3. Run: `uvicorn app.main:app --reload --port 8000`
