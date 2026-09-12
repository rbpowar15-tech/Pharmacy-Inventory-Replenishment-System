# Replenishment Worker

Logic App / Container worker that processes low-stock replenishment messages
from Service Bus and writes reports to Azure Blob Storage.

## Flow
1. Consumes message from Service Bus queue (replenishment-queue)
2. Updates ReplenishmentRequests status → 'processing' in Azure SQL
3. Generates JSON replenishment report
4. Uploads report to Blob Storage (replenishment-reports)
5. Updates ReplenishmentRequests status → 'completed' in Azure SQL

## Running Locally
1. Copy `.env.example` to `.env` and fill in values
2. Set `USE_SQL_LOGIN=true` for local development
3. Run: `python worker.py`
