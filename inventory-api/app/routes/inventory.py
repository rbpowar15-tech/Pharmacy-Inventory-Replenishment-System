from fastapi import APIRouter, HTTPException
from app.database import get_connection
from azure.servicebus import ServiceBusClient, ServiceBusMessage
import os, json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# ─────────────────────────────────────────────
# GET /inventory/{pharmacyId}
# Returns all medicines for a given pharmacy
# ─────────────────────────────────────────────
@router.get("/inventory/{pharmacyId}")
def get_inventory(pharmacyId: str):
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT PharmacyId, MedicineCode, MedicineName, CurrentStock, ReorderLevel, LastUpdated "
            "FROM MedicineInventory WHERE PharmacyId = ?",
            pharmacyId
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            raise HTTPException(status_code=404, detail=f"No inventory found for pharmacy {pharmacyId}")

        return [
            {
                "pharmacyId":         row[0],
                "medicineCode":       row[1],
                "medicineName":       row[2],
                "currentStock":       row[3],
                "reorderLevel":       row[4],
                "lastUpdated":        str(row[5]),
                "needsReplenishment": row[3] < row[4]
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# PUT /inventory/{pharmacyId}/{medicineCode}
# Deducts stockUsed from currentStock
# newStock = currentStock - stockUsed
# Publishes to Service Bus if stock drops below reorder level
# ─────────────────────────────────────────────
@router.put("/inventory/{pharmacyId}/{medicineCode}")
def update_inventory(pharmacyId: str, medicineCode: str, body: dict):
    try:
        stock_used = body.get("stockUsed")

        if stock_used is None:
            raise HTTPException(status_code=400, detail="stockUsed is required")
        if stock_used < 0:
            raise HTTPException(status_code=400, detail="stockUsed cannot be negative")

        conn   = get_connection()
        cursor = conn.cursor()

        # ── Step 1: Fetch current stock from DB ──
        cursor.execute(
            "SELECT CurrentStock FROM MedicineInventory "
            "WHERE PharmacyId = ? AND MedicineCode = ?",
            pharmacyId, medicineCode
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"Medicine {medicineCode} not found for pharmacy {pharmacyId}"
            )

        current_stock = row[0]

        # ── Step 2: Calculate new stock ──
        new_stock = current_stock - stock_used

        if new_stock < 0:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Cannot dispense {stock_used} units. Only {current_stock} units available."
            )

        # ── Step 3: Update stock in DB ──
        cursor.execute(
            "UPDATE MedicineInventory SET CurrentStock = ?, LastUpdated = GETDATE() "
            "WHERE PharmacyId = ? AND MedicineCode = ?",
            new_stock, pharmacyId, medicineCode
        )
        conn.commit()

        # ── Step 4: Check if now below reorder level ──
        cursor.execute(
            "SELECT MedicineName, CurrentStock, ReorderLevel FROM MedicineInventory "
            "WHERE PharmacyId = ? AND MedicineCode = ? AND CurrentStock < ReorderLevel",
            pharmacyId, medicineCode
        )
        low_stock = cursor.fetchone()

        # ── Step 5: If low stock — save to ReplenishmentRequests AND publish to Service Bus ──
        if low_stock:
            # Generate replenishmentId here in the API
            replenishment_id = (
                f"REP-{pharmacyId}-{medicineCode}"
                f"-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            )
            qty_needed = low_stock[2] - low_stock[1]

            # Save to ReplenishmentRequests table with status = submitted
            cursor.execute(
                """INSERT INTO ReplenishmentRequests
                (ReplenishmentId, PharmacyId, MedicineCode, MedicineName,
                CurrentStock, ReorderLevel, QuantityNeeded, Status, CreatedAt, UpdatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'submitted', GETDATE(), GETDATE())""",
                replenishment_id, pharmacyId, medicineCode,
                low_stock[0], low_stock[1], low_stock[2], qty_needed
            )
            conn.commit()

            # Publish to Service Bus WITH replenishmentId so worker can update DB
            publish_to_service_bus({
                "replenishmentId": replenishment_id,  # ← KEY FIX: worker uses this to update DB
                "pharmacyId":      pharmacyId,
                "medicineCode":    medicineCode,
                "medicineName":    low_stock[0],
                "currentStock":    low_stock[1],
                "reorderLevel":    low_stock[2],
                "quantityNeeded":  qty_needed
            })

        conn.close()

        return {
            "message":       "Stock updated successfully",
            "previousStock": current_stock,
            "stockUsed":     stock_used,
            "newStock":      new_stock,
            "lowStockAlert": bool(low_stock)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# Helper — Publish low-stock event to Service Bus
# ─────────────────────────────────────────────
def publish_to_service_bus(payload: dict):
    conn_str   = os.getenv("SERVICE_BUS_CONNECTION_STRING")
    queue_name = os.getenv("SERVICE_BUS_QUEUE_NAME", "replenishment-queue")
    with ServiceBusClient.from_connection_string(conn_str) as client:
        with client.get_queue_sender(queue_name) as sender:
            sender.send_messages(ServiceBusMessage(json.dumps(payload)))
