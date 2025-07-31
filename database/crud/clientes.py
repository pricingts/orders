from sqlalchemy import text
from database.db import SessionLocal  # o tu conexión

def obtener_clientes():
    query = text("""
        SELECT id_cliente, cliente, nit, direccion, telefono_contacto, correo, pais
        FROM clientes
        ORDER BY cliente
    """)
    with SessionLocal() as db:
        return db.execute(query).mappings().all()


def insertar_cliente(cliente, nit, direccion, telefono_contacto, correo, pais):
    query = text("""
        INSERT INTO clientes (cliente, nit, direccion, telefono_contacto, correo, pais)
        VALUES (:cliente, :nit, :direccion, :telefono_contacto, :correo, :pais)
    """)
    with SessionLocal() as db:
        db.execute(query, {
            "cliente": cliente,
            "nit": nit,
            "direccion": direccion,
            "telefono_contacto": telefono_contacto,
            "correo": correo,
            "pais": pais
        })
        db.commit()