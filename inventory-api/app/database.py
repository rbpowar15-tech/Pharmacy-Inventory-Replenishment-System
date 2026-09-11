import pyodbc
import os
import struct
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential

load_dotenv()

def get_connection():
    """
    Uses Managed Identity (Entra ID) when running on Azure VM.
    Falls back to SQL login for local development via .env.
    Architecture: Managed Identity — Least-privilege access to data, queue and storage.
    """
    server   = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE", "inventorydb")

    # ── Local dev: use SQL login from .env ──
    if os.getenv("USE_SQL_LOGIN", "false").lower() == "true":
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={server};DATABASE={database};"
            f"UID={os.getenv('SQL_USER')};PWD={os.getenv('SQL_PASSWORD')};"
            f"Encrypt=yes;TrustServerCertificate=no;"
        )
        return pyodbc.connect(conn_str)

    # ── Azure VM: use Managed Identity (no credentials needed) ──
    credential   = DefaultAzureCredential()
    token        = credential.get_token("https://database.windows.net/.default")
    token_bytes  = token.token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};DATABASE={database};"
        f"Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(conn_str, attrs_before={1256: token_struct})
