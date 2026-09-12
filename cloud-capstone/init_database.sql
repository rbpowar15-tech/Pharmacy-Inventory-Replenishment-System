-- ══════════════════════════════════════════════════════════════
-- Pharmacy Inventory Replenishment System — Database Init Script
-- Run this against the 'inventorydb' database on your Azure SQL Server
-- ══════════════════════════════════════════════════════════════

-- Step 1: Create the MedicineInventory table
CREATE TABLE MedicineInventory (
    PharmacyId    VARCHAR(30),
    MedicineCode  VARCHAR(30),
    MedicineName  VARCHAR(100),
    CurrentStock  INT,
    ReorderLevel  INT,
    LastUpdated   DATETIME2,
    PRIMARY KEY (PharmacyId, MedicineCode)
);
GO

-- Step 2: Insert 5 sample inventory rows (Mandatory Test Case #74)
INSERT INTO MedicineInventory (PharmacyId, MedicineCode, MedicineName, CurrentStock, ReorderLevel, LastUpdated)
VALUES
    ('PH001', 'MED001', 'Amoxicillin 500mg',   150, 50,  GETDATE()),
    ('PH001', 'MED002', 'Lisinopril 10mg',      30, 40,  GETDATE()),   -- ⚠ Below reorder level!
    ('PH001', 'MED003', 'Metformin 850mg',      200, 60,  GETDATE()),
    ('PH002', 'MED001', 'Amoxicillin 500mg',    80,  50,  GETDATE()),
    ('PH002', 'MED004', 'Omeprazole 20mg',      10,  25,  GETDATE());  -- ⚠ Below reorder level!
GO

-- Step 3: Verify low-stock query (Mandatory Test Case #76)
SELECT *
FROM MedicineInventory
WHERE CurrentStock < ReorderLevel;
GO

-- Step 4: Create ReplenishmentRequests table to track status
CREATE TABLE ReplenishmentRequests (
    ReplenishmentId   VARCHAR(50) PRIMARY KEY,
    PharmacyId        VARCHAR(30),
    MedicineCode      VARCHAR(30),
    MedicineName      VARCHAR(100),
    CurrentStock      INT,
    ReorderLevel      INT,
    QuantityNeeded    INT,
    Status            VARCHAR(30) DEFAULT 'submitted',
    CreatedAt         DATETIME2  DEFAULT GETDATE(),
    UpdatedAt         DATETIME2  DEFAULT GETDATE()
);
GO
