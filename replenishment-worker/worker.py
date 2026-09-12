import os, json, pyodbc, struct
from datetime import datetime
from dotenv import load_dotenv
from azure.servicebus import ServiceBusClient
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

load_dotenv()

SERVICE_BUS_CONN_STR = os.getenv("SERVICE_BUS_CONNECTION_STRING")
QUEUE_NAME           = os.getenv("SERVICE_BUS_QUEUE_NAME", "replenishment-queue")
BLOB_CONN_STR        = os.getenv("BLOB_CONNECTION_STRING")
BLOB_CONTAINER       = os.getenv("BLOB_CONTAINER", "replenishment-reports")
SQL_SERVER           = os.getenv("SQL_SERVER")
SQL_DATABASE         = os.getenv("SQL_DATABASE", "inventorydb")

# ─────────────────────────────────────────────
# DB Connection — Managed Identity on Azure,
# SQL login fallback for local dev
# ─────────────────────────────────────────────
def get_db_connection():
    if os.getenv("USE_SQL_LOGIN", "false").lower() == "true":
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
            f"UID={os.getenv('SQL_USER')};PWD={os.getenv('SQL_PASSWORD')};"
            f"Encrypt=yes;TrustServerCertificate=no;"
        )
        return pyodbc.connect(conn_str)

    credential   = DefaultAzureCredential()
    token        = credential.get_token("https://database.windows.net/.default")
    token_bytes  = token.token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(conn_str, attrs_before={1256: token_struct})


# ─────────────────────────────────────────────
# Update ReplenishmentRequests status in Azure SQL
# ─────────────────────────────────────────────
def update_status_in_db(replenishment_id: str, status: str):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE ReplenishmentRequests SET Status = ?, UpdatedAt = GETDATE() "
        "WHERE ReplenishmentId = ?",
        status, replenishment_id
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# Process a single Service Bus message:
# 1. Update status → processing
# 2. Generate JSON report
# 3. Upload report to Blob Storage
# 4. Update status → completed
# ─────────────────────────────────────────────
def process_message(msg_body: dict):
    replenishment_id = msg_body.get(
        "replenishmentId",
        f"REP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )
    print(f"📦 Processing replenishment for: {msg_body['medicineName']} ({msg_body['pharmacyId']})")

    # Update status to processing
    update_status_in_db(replenishment_id, "processing")

    # Generate replenishment report
    report_name    = (
        f"replenishment-{msg_body['pharmacyId']}-"
        f"{msg_body['medicineCode']}-"
        f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"
    )
    report_content = json.dumps({
        "replenishmentId": replenishment_id,
        "pharmacyId":      msg_body["pharmacyId"],
        "medicineCode":    msg_body["medicineCode"],
        "medicineName":    msg_body["medicineName"],
        "currentStock":    msg_body["currentStock"],
        "reorderLevel":    msg_body["reorderLevel"],
        "quantityNeeded":  msg_body["reorderLevel"] - msg_body["currentStock"],
        "processedAt":     datetime.utcnow().isoformat(),
        "status":          "completed"
    }, indent=2)

    # Upload report to Blob Storage (replenishment-reports container)
    blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
    container    = blob_service.get_container_client(BLOB_CONTAINER)
    container.upload_blob(name=report_name, data=report_content, overwrite=True)
    print(f"✅ Report uploaded to Blob Storage: {report_name}")

    # Update status to completed in DB
    update_status_in_db(replenishment_id, "completed")
    print(f"✅ Status updated to 'completed' for {replenishment_id}")


# ─────────────────────────────────────────────
# Main — Listen on Service Bus queue
# ─────────────────────────────────────────────
def main():
    print("🚀 Replenishment Worker started — listening on Service Bus queue...")
    with ServiceBusClient.from_connection_string(SERVICE_BUS_CONN_STR) as client:
        with client.get_queue_receiver(QUEUE_NAME, max_wait_time=30) as receiver:
            for msg in receiver:
                try:
                    body = json.loads(str(msg))
                    process_message(body)
                    receiver.complete_message(msg)   # Acknowledge message
                except Exception as e:
                    print(f"❌ Failed to process message: {e}")
                    receiver.abandon_message(msg)    # Return to queue for retry

if __name__ == "__main__":
    main()
