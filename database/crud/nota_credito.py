from sqlalchemy import text
from database.db import SessionLocal
from services.sheets_writer import save_nota_credito, delete_nota_credito_sheet

def insertar_nota_credito(no_solicitud: str, no_factura: str, tipo_nc: str, valor_nc: float, razon: str, id_venta_master: int):
    """
    Inserta una nueva nota de crédito asociada a una operación (no_solicitud)
    y a una venta consolidada (id_venta_master), y la guarda también en Google Sheets.
    """
    with SessionLocal() as db:
        try:
            # 1. Obtener id_operacion
            query_id = text("""
                SELECT id_operacion 
                FROM operaciones 
                WHERE no_solicitud = :no_solicitud
            """)
            result = db.execute(query_id, {"no_solicitud": no_solicitud}).fetchone()
            if not result:
                raise ValueError(f"No se encontró la operación con no_solicitud={no_solicitud}")

            id_operacion = result[0]

            # 2. Insertar en notas_credito usando id_venta_master
            query_insert = text("""
                INSERT INTO notas_credito (id_operacion, id_venta_master, no_factura, tipo_nc, valor_nc, razon)
                VALUES (:id_operacion, :id_venta_master, :no_factura, :tipo_nc, :valor_nc, :razon)
                RETURNING id_nc
            """)
            new_id = db.execute(query_insert, {
                "id_operacion": id_operacion,
                "id_venta_master": id_venta_master,
                "no_factura": no_factura,
                "tipo_nc": tipo_nc,
                "valor_nc": valor_nc,
                "razon": razon
            }).scalar()

            db.commit()

            # 3. Guardar en Google Sheets
            save_nota_credito({
                "id_nc": new_id,
                "no_solicitud": no_solicitud,
                "id_venta_master": id_venta_master,
                "no_factura": no_factura,
                "tipo_nc": tipo_nc,
                "valor_nc": valor_nc,
                "razon": razon
            })

        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Error al insertar la nota de crédito: {e}")


def obtener_notas_credito(no_solicitud: str):
    """
    Obtiene todas las notas de crédito asociadas a una operación (no_solicitud).
    """
    with SessionLocal() as db:
        query = text("""
            SELECT nc.* 
            FROM notas_credito nc
            JOIN operaciones op ON op.id_operacion = nc.id_operacion
            WHERE op.no_solicitud = :no_solicitud
        """)
        result = db.execute(query, {"no_solicitud": no_solicitud}).mappings().all()
        return [dict(row) for row in result]


def eliminar_nota_credito(id_nc: int):
    """
    Elimina una nota de crédito por su ID (en BD y en Google Sheets).
    """
    with SessionLocal() as db:
        try:
            # 1. Eliminar de la base de datos
            query = text("DELETE FROM notas_credito WHERE id_nc = :id_nc")
            db.execute(query, {"id_nc": id_nc})
            db.commit()

            # 2. Eliminar de Google Sheets
            delete_nota_credito_sheet(id_nc)

        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Error al eliminar la nota de crédito: {e}")
