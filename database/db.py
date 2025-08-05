# database/db.py

# database/db.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Intentamos usar st.secrets si estamos en Streamlit Cloud
try:
    import streamlit as st
    DATABASE_URL = st.secrets["DATABASE_URL"]
except Exception:
    # Si no estamos en Streamlit, intentamos usar .env
    from dotenv import load_dotenv
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no está definida. Revisa tus secretos o tu archivo .env")

# Crear el engine de SQLAlchemy
engine = create_engine(DATABASE_URL)

# Fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
