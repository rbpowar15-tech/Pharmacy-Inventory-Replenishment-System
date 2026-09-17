from fastapi import APIRouter, HTTPException
from app.database import get_connection
from datetime import datetime

router = APIRouter()

# ─────────────────────────────────────────────
# POST /replenishments
# Triggers replenishment for all low-stock medicines
# Saves each request to ReplenishmentRequests table
# ─────────────────────────────────────────────
@router.post("/replenishments")
def create_replenishment(body: dict):
    try:
        pharmacy_id = body.get("pharmacyId")
        if not pharmacy_id:
            raise HTTPException(status_code=400, detail="pharmacyId is required")

        conn   = get_connection()
        cursor = conn.cursor()

        # Fetch all low-stock items for this pharmacy
        cursor.execute(
            "SELECT PharmacyId, MedicineCode, MedicineName, CurrentStock, ReorderLevel "
            "FROM MedicineInventory "
            "WHERE PharmacyId = ? AND CurrentStock < ReorderLevel",
            pharmacy_id
        )
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return {"message": "No replenishment needed", "items": []}

        replenishment_id = f"REP-{pharmacy_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        items = []

        for row in rows:
            qty_needed = row[4] - row[3]
            item_rep_id = f"{replenishment_id}-{row[1]}"

            # Save each low-stock item as a replenishment request in DB
            cursor.execute(
                """INSERT INTO ReplenishmentRequests
                   (ReplenishmentId, PharmacyId, MedicineCode, MedicineName,
                    CurrentStock, ReorderLevel, QuantityNeeded, Status, CreatedAt, UpdatedAt)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'submitted', GETDATE(), GETDATE())""",
                item_rep_id, row[0], row[1], row[2], row[3], row[4], qty_needed
            )

            items.append({
                "replenishmentId": item_rep_id,
                "pharmacyId":      row[0],
                "medicineCode":    row[1],
                "medicineName":    row[2],
                "currentStock":    row[3],
                "reorderLevel":    row[4],
                "quantityNeeded":  qty_needed
            })

        conn.commit()
        conn.close()

        return {
            "replenishmentId": replenishment_id,
            "pharmacyId":      pharmacy_id,
            "status":          "submitted",
            "items":           items,
            "createdAt":       datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# GET /replenishments/{id}
# Fetch replenishment request status from DB
# ─────────────────────────────────────────────
@router.get("/replenishments/{id}")
def get_replenishment(id: str):
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ReplenishmentId, PharmacyId, MedicineCode, MedicineName, "
            "CurrentStock, ReorderLevel, QuantityNeeded, Status, CreatedAt, UpdatedAt "
            "FROM ReplenishmentRequests WHERE ReplenishmentId = ?",
            id
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"Replenishment {id} not found")

        return {
            "replenishmentId": row[0],
            "pharmacyId":      row[1],
            "medicineCode":    row[2],
            "medicineName":    row[3],
            "currentStock":    row[4],
            "reorderLevel":    row[5],
            "quantityNeeded":  row[6],
            "status":          row[7],
            "createdAt":       str(row[8]),
            "updatedAt":       str(row[9])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
