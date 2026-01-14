from pathlib import Path
from app.db import DATABASE_URL

cwd = Path.cwd().resolve()
db_path = (cwd / "retbet.db").resolve()

print("DATABASE_URL:", DATABASE_URL)
print("CWD:", cwd)
print("DB assoluto:", db_path)
print("ESISTE?:", db_path.exists())
