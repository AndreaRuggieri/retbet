from app.db import engine
from app.models import Base

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("DB creato/aggiornato: retbet.db")
