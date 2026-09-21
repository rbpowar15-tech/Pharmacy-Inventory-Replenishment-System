import os, json, time
from datetime import datetime
from dotenv import load_dotenv
from azure.servicebus import ServiceBusClient
from azure.storage.blob import BlobServiceClient
import pyodbc

load_dotenv()

SERVICE_BUS_CONN_STR = os.getenv("SERVICE_BUS_CONNECTION_STRING")
QUEUE_NAME           = os.getenv("SERVICE_BUS_QUEUE_NAME", "replenishment-queue")
BLOB_CONN_STR        = os.getenv("BLOB_CONNECTION_STRING")
BLOB_CONTAINER       = os.getenv("BLOB_CONTAINER", "replenishment-reports")
SQL_SERVER           = os.getenv("SQL_SERVER")
SQL_DATABASE         = os.getenv("SQL_DATABASE", "inventorydb")
SQL_USER             = os.getenv("SQL_USER")
SQL_PASSWORD         = os.getenv("SQL_PASSWORD")
USE_SQL_LOGIN        = os.getenv("USE_SQL_LOGIN", "false").lower() == "true"

# ─────────────────────────────────────────────
# DB Connection
# ─────────────────────────────────────────────
def get_db_connection():
    if USE_SQL_LOGIN:
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD};"
            f"TrustServerCertificate=yes;"
        )
    else:
        # Managed Identity for production on Azure VM
        from azure.identity import DefaultAzureCredential
        import struct
        credential   = DefaultAzureCredential()
        token        = credential.get_token("https://database.windows.net/.default")
        token_bytes  = token.token.encode("UTF-16-LE")
        token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"TrustServerCertificate=yes;"
        )
        return pyodbc.connect(conn_str, attrs_before={1256: token_struct})

    return pyodbc.connect(conn_str)

# ─────────────────────────────────────────────
# Update Status in ReplenishmentRequests table
# ─────────────────────────────────────────────
def update_status_in_db(replenishment_id: str, status: str):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE ReplenishmentRequests SET Status = ?, UpdatedAt = GETDATE() "
            "WHERE ReplenishmentId = ?",
            status, replenishment_id
        )
        conn.commit()
        conn.close()
        print(f"  ✅ Status updated to '{status}' for {replenishment_id}")
    except Exception as e:
        print(f"  ❌ Failed to update status in DB: {e}")

# ─────────────────────────────────────────────
# Process a single Service Bus message
# ─────────────────────────────────────────────
def process_message(msg_body: dict):
    replenishment_id = msg_body.get("replenishmentId", f"REP-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}")

    print(f"  📦 Processing replenishment for: {msg_body['medicineName']} ({msg_body['pharmacyId']})")

    # Step 1 — Update status to processing
    update_status_in_db(replenishment_id, "processing")

    # Step 2 — Generate replenishment report
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

    # Step 3 — Upload report to Blob Storage
    blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
    container    = blob_service.get_container_client(BLOB_CONTAINER)
    container.upload_blob(name=report_name, data=report_content, overwrite=True)
    print(f"  ✅ Report uploaded to Blob Storage: {report_name}")

    # Step 4 — Update status to completed
    update_status_in_db(replenishment_id, "completed")

# ─────────────────────────────────────────────
# Main — Infinite loop listener
# Runs forever just like uvicorn in inventory-api
# ─────────────────────────────────────────────
def main():
    print("🚀 Replenishment Worker started — listening on Service Bus queue forever...")

    while True:                                          # ← Runs forever like uvicorn
        try:
            with ServiceBusClient.from_connection_string(SERVICE_BUS_CONN_STR) as client:
                with client.get_queue_receiver(
                    QUEUE_NAME,
                    max_wait_time=30                     # ← Waits 30s for messages
                ) as receiver:
                    for msg in receiver:
                        try:
                            body = json.loads(str(msg))
                            process_message(body)
                            receiver.complete_message(msg)   # ← Removes from queue
                        except Exception as e:
                            print(f"  ❌ Failed to process message: {e}")
                            receiver.abandon_message(msg)    # ← Returns to queue for retry

            print("  🔄 No messages in last 30s — polling again...")

        except Exception as e:
            print(f"  ❌ Connection error: {e} — retrying in 10s...")
            time.sleep(10)                               # ← Wait before reconnecting

if __name__ == "__main__":
    main()
