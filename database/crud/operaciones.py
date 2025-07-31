from sqlalchemy import text
from database.db import SessionLocal
import json

def guardar_operacion_completa(operacion, carga, ventas, costos):
    """
    Guarda una operación completa en la base de datos.
    - Si la operación (no_solicitud) existe, la actualiza y elimina datos previos de cargas, ventas y costos.
    - Si no existe, la crea desde cero.
    """

    with SessionLocal() as db:
        try:
            # --- 1. Verificar si la operación existe ---
            query_check = text("SELECT id_operacion FROM operaciones WHERE no_solicitud = :no_solicitud")
            result = db.execute(query_check, {"no_solicitud": operacion["no_solicitud"]}).fetchone()

            if result:
                id_operacion = result[0]
                # Actualizar la operación
                query_update = text("""
                    UPDATE operaciones
                    SET comercial = :comercial,
                        comentarios = :comentarios
                    WHERE id_operacion = :id_operacion
                """)
                db.execute(query_update, {
                    "comercial": operacion.get("comercial"),
                    "comentarios": operacion.get("comentarios", ""),  # default vacío
                    "id_operacion": id_operacion
                })

                # Eliminar datos previos
                db.execute(text("DELETE FROM ventas WHERE id_operacion = :id_operacion"), {"id_operacion": id_operacion})
                db.execute(text("DELETE FROM costos WHERE id_operacion = :id_operacion"), {"id_operacion": id_operacion})
                db.execute(text("DELETE FROM cargas WHERE id_operacion = :id_operacion"), {"id_operacion": id_operacion})
            else:
                # Insertar nueva operación (incluyendo comentarios)
                query_insert = text("""
                    INSERT INTO operaciones (no_solicitud, comercial, comentarios)
                    VALUES (:no_solicitud, :comercial, :comentarios)
                    RETURNING id_operacion
                """)
                id_operacion = db.execute(query_insert, {
                    "no_solicitud": operacion["no_solicitud"],
                    "comercial": operacion.get("comercial"),
                    "comentarios": operacion.get("comentarios", "")
                }).scalar()

            # --- 2. Insertar carga ---
            carga_serializada = {**carga, "id_operacion": id_operacion}
            carga_serializada["referencia"] = carga.get("referencia", "")
            # Serializamos detalle (JSONB)
            if isinstance(carga_serializada.get("detalle"), dict):
                carga_serializada["detalle"] = json.dumps(carga_serializada["detalle"])

            query_carga = text("""
                INSERT INTO cargas (id_operacion, bl_awb, tipo_carga, pol_aol, pod_aod, shipper, consignee,
                                    detalle, unidad_medida, cantidad_suelta, referencia)
                VALUES (:id_operacion, :bl_awb, :tipo_carga, :pol_aol, :pod_aod, :shipper, :consignee,
                        :detalle, :unidad_medida, :cantidad_suelta, :referencia)
            """)
            db.execute(query_carga, carga_serializada)

            # --- 3. Insertar ventas ---
            for venta in ventas:
                query_venta = text("""
                    INSERT INTO ventas (id_operacion, cliente, concepto, cantidad, tarifa, monto, moneda, comentarios)
                    VALUES (:id_operacion, :cliente, :concepto, :cantidad, :tarifa, :monto, :moneda, :comentarios)
                """)
                db.execute(query_venta, {
                    "id_operacion": id_operacion,
                    "cliente": venta.get("cliente"),
                    "concepto": venta.get("concepto"),
                    "cantidad": venta.get("cantidad", 0),
                    "tarifa": venta.get("tarifa", 0),
                    "monto": venta.get("monto", 0),
                    "moneda": venta.get("moneda", "USD"),
                    "comentarios": venta.get("comentarios", "")  # default vacío
                })

            # --- 4. Insertar costos ---
            for costo in costos:
                query_costo = text("""
                    INSERT INTO costos (id_operacion, concepto, cantidad, tarifa, monto, moneda, comentarios)
                    VALUES (:id_operacion, :concepto, :cantidad, :tarifa, :monto, :moneda, :comentarios)
                """)
                db.execute(query_costo, {
                    "id_operacion": id_operacion,
                    "concepto": costo.get("concepto"),
                    "cantidad": costo.get("cantidad", 0),
                    "tarifa": costo.get("tarifa", 0),
                    "monto": costo.get("monto", 0),
                    "moneda": costo.get("moneda", "USD"),
                    "comentarios": costo.get("comentarios", "")  # default vacío
                })

            db.commit()

        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Error al guardar la operación: {e}")

def obtener_operacion_completa(no_solicitud):
    """
    Devuelve toda la información de una operación:
    - Datos generales de la operación.
    - Información de la carga (con 'detalle' convertido de JSON a dict).
    - Ventas asociadas.
    - Costos asociados.
    """
    with SessionLocal() as db:
        # --- 1. Obtener operación ---
        query_operacion = text("""
            SELECT * FROM operaciones WHERE no_solicitud = :no_solicitud
        """)
        operacion = db.execute(query_operacion, {"no_solicitud": no_solicitud}).mappings().first()

        if not operacion:
            return None  # No existe la operación

        id_operacion = operacion["id_operacion"]

        # --- 2. Obtener carga ---
        query_carga = text("""
            SELECT * FROM cargas WHERE id_operacion = :id_operacion
        """)
        carga = db.execute(query_carga, {"id_operacion": id_operacion}).mappings().first()

        # Deserializar detalle JSONB
        if carga and carga.get("detalle"):
            if isinstance(carga["detalle"], str):  # Solo deserializar si es string
                try:
                    carga = dict(carga)
                    carga["detalle"] = json.loads(carga["detalle"])
                except json.JSONDecodeError:
                    carga["detalle"] = {}
            else:
                carga = dict(carga)  # Ya es dict

        # --- 3. Obtener ventas ---
        query_ventas = text("""
            SELECT * FROM ventas WHERE id_operacion = :id_operacion
        """)
        ventas = db.execute(query_ventas, {"id_operacion": id_operacion}).mappings().all()

        # --- 4. Obtener costos ---
        query_costos = text("""
            SELECT * FROM costos WHERE id_operacion = :id_operacion
        """)
        costos = db.execute(query_costos, {"id_operacion": id_operacion}).mappings().all()

        return {
            "operacion": dict(operacion),
            "carga": dict(carga) if carga else {},
            "ventas": [dict(v) for v in ventas],
            "costos": [dict(c) for c in costos]
        }
