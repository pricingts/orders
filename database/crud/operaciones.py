from sqlalchemy import text
from database.db import SessionLocal
import json

def guardar_operacion_completa(operacion, carga, ventas, costos):
    """
    Guarda una operación completa con el nuevo modelo:
    - ventas_master (venta consolidada)
    - ventas_detalle (recargos de cada venta)
    """

    with SessionLocal() as db:
        try:
            # 1. Verificar si la operación ya existe
            result = db.execute(
                text("SELECT id_operacion FROM operaciones WHERE no_solicitud = :no_solicitud"),
                {"no_solicitud": operacion["no_solicitud"]}
            ).fetchone()

            if result:
                id_operacion = result[0]

                # Actualizar datos generales
                db.execute(text("""
                    UPDATE operaciones
                    SET comercial = :comercial,
                        comentarios = :comentarios
                    WHERE id_operacion = :id_operacion
                """), {
                    "comercial": operacion.get("comercial"),
                    "comentarios": operacion.get("comentarios", ""),
                    "id_operacion": id_operacion
                })

                # Eliminar datos previos
                db.execute(text("""
                    DELETE FROM ventas_detalle 
                    WHERE id_venta_master IN (
                        SELECT id_venta_master FROM ventas_master WHERE id_operacion = :id_operacion
                    )
                """), {"id_operacion": id_operacion})

                db.execute(text("DELETE FROM ventas_master WHERE id_operacion = :id_operacion"), {"id_operacion": id_operacion})
                db.execute(text("DELETE FROM costos WHERE id_operacion = :id_operacion"), {"id_operacion": id_operacion})
                db.execute(text("DELETE FROM cargas WHERE id_operacion = :id_operacion"), {"id_operacion": id_operacion})

            else:
                # Insertar nueva operación
                id_operacion = db.execute(text("""
                    INSERT INTO operaciones (no_solicitud, comercial, comentarios)
                    VALUES (:no_solicitud, :comercial, :comentarios)
                    RETURNING id_operacion
                """), {
                    "no_solicitud": operacion["no_solicitud"],
                    "comercial": operacion.get("comercial"),
                    "comentarios": operacion.get("comentarios", "")
                }).scalar()

            # 2. Insertar carga
            carga_serializada = {**carga, "id_operacion": id_operacion}
            if isinstance(carga_serializada.get("detalle"), dict):
                carga_serializada["detalle"] = json.dumps(carga_serializada["detalle"])

            db.execute(text("""
                INSERT INTO cargas (id_operacion, bl_awb, tipo_carga, pol_aol, pod_aod, shipper, consignee,
                                     detalle, unidad_medida, cantidad_suelta, referencia)
                VALUES (:id_operacion, :bl_awb, :tipo_carga, :pol_aol, :pod_aod, :shipper, :consignee,
                        :detalle, :unidad_medida, :cantidad_suelta, :referencia)
            """), carga_serializada)

            # 3. Insertar ventas_master y ventas_detalle
            for venta in ventas:
                monto_total = sum(d.get("monto", 0) for d in venta.get("detalles", []))

                id_venta_master = db.execute(text("""
                    INSERT INTO ventas_master (id_operacion, cliente, monto_total, moneda, comentarios)
                    VALUES (:id_operacion, :cliente, :monto_total, :moneda, :comentarios)
                    RETURNING id_venta_master
                """), {
                    "id_operacion": id_operacion,
                    "cliente": venta.get("cliente"),
                    "monto_total": monto_total,
                    "moneda": venta.get("moneda", "USD"),
                    "comentarios": venta.get("comentarios", "")
                }).scalar()

                # Insertar detalles de venta
                for detalle in venta.get("detalles", []):
                    db.execute(text("""
                        INSERT INTO ventas_detalle (id_venta_master, concepto, cantidad, tarifa, monto, moneda)
                        VALUES (:id_venta_master, :concepto, :cantidad, :tarifa, :monto, :moneda)
                    """), {
                        "id_venta_master": id_venta_master,
                        "concepto": detalle.get("concepto"),
                        "cantidad": detalle.get("cantidad", 0),
                        "tarifa": detalle.get("tarifa", 0),
                        "monto": detalle.get("monto", 0),
                        "moneda": detalle.get("moneda", "USD")
                    })

            # 4. Insertar costos
            for costo in costos:
                db.execute(text("""
                    INSERT INTO costos (id_operacion, concepto, cantidad, tarifa, monto, moneda, comentarios)
                    VALUES (:id_operacion, :concepto, :cantidad, :tarifa, :monto, :moneda, :comentarios)
                """), {
                    "id_operacion": id_operacion,
                    "concepto": costo.get("concepto"),
                    "cantidad": costo.get("cantidad", 0),
                    "tarifa": costo.get("tarifa", 0),
                    "monto": costo.get("monto", 0),
                    "moneda": costo.get("moneda", "USD"),
                    "comentarios": costo.get("comentarios", "")
                })

            db.commit()

        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Error al guardar la operación: {e}")


def obtener_operacion_completa(no_solicitud):
    """
    Devuelve toda la información de una operación:
    - Datos generales de la operación.
    - Información de la carga (detalle JSON a dict).
    - Ventas_master con sus ventas_detalle.
    - Costos.
    """
    with SessionLocal() as db:
        # 1. Obtener operación
        query_operacion = text("""
            SELECT * FROM operaciones WHERE no_solicitud = :no_solicitud
        """)
        operacion = db.execute(query_operacion, {"no_solicitud": no_solicitud}).mappings().first()
        if not operacion:
            return None

        id_operacion = operacion["id_operacion"]

        # 2. Obtener carga
        query_carga = text("""
            SELECT * FROM cargas WHERE id_operacion = :id_operacion
        """)
        carga = db.execute(query_carga, {"id_operacion": id_operacion}).mappings().first()
        if carga and carga.get("detalle"):
            if isinstance(carga["detalle"], str):
                try:
                    carga = dict(carga)
                    carga["detalle"] = json.loads(carga["detalle"])
                except json.JSONDecodeError:
                    carga["detalle"] = {}
            else:
                carga = dict(carga)

        # 3. Obtener ventas consolidadas (ventas_master)
        query_ventas_master = text("""
            SELECT * FROM ventas_master WHERE id_operacion = :id_operacion
        """)
        ventas_master = db.execute(query_ventas_master, {"id_operacion": id_operacion}).mappings().all()

        # Para cada venta, obtener detalles (ventas_detalle)
        ventas_completas = []
        for venta in ventas_master:
            venta_dict = dict(venta)

            query_detalles = text("""
                SELECT * FROM ventas_detalle WHERE id_venta_master = :id_venta_master
            """)
            detalles = db.execute(query_detalles, {"id_venta_master": venta["id_venta_master"]}).mappings().all()
            venta_dict["detalles"] = [dict(d) for d in detalles]

            ventas_completas.append(venta_dict)

        # 4. Obtener costos
        query_costos = text("""
            SELECT * FROM costos WHERE id_operacion = :id_operacion
        """)
        costos = db.execute(query_costos, {"id_operacion": id_operacion}).mappings().all()

        return {
            "operacion": dict(operacion),
            "carga": dict(carga) if carga else {},
            "ventas": ventas_completas,
            "costos": [dict(c) for c in costos]
        }


def obtener_ventas_por_solicitud(no_solicitud: str, incluir_detalles: bool = False):
    """
    Obtiene las ventas consolidadas (ventas_master) para una solicitud.
    Si incluir_detalles=True, también incluye los recargos de cada venta.
    """
    with SessionLocal() as db:
        query = text("""
            SELECT vm.id_venta_master, vm.cliente, vm.monto_total, vm.moneda, vm.comentarios
            FROM ventas_master vm
            JOIN operaciones o ON o.id_operacion = vm.id_operacion
            WHERE o.no_solicitud = :no_solicitud
        """)
        ventas = db.execute(query, {"no_solicitud": no_solicitud}).mappings().all()

        ventas_lista = [dict(v) for v in ventas]

        if incluir_detalles:
            for venta in ventas_lista:
                query_detalles = text("""
                    SELECT vd.id_detalle, vd.concepto, vd.cantidad, vd.tarifa, vd.monto, vd.moneda
                    FROM ventas_detalle vd
                    WHERE vd.id_venta_master = :id_venta_master
                """)
                detalles = db.execute(query_detalles, {"id_venta_master": venta["id_venta_master"]}).mappings().all()
                venta["detalles"] = [dict(d) for d in detalles]

        return ventas_lista

def obtener_notas_credito_por_venta(id_venta_master: int):
    """
    Obtiene las notas crédito registradas para una venta completa (ventas_master).
    """
    with SessionLocal() as db:
        query = text("""
            SELECT id_nc, id_operacion, no_factura, tipo_nc, valor_nc, razon, id_venta_master
            FROM notas_credito
            WHERE id_venta_master = :id_venta_master
        """)
        result = db.execute(query, {"id_venta_master": id_venta_master}).mappings().all()
        return [dict(r) for r in result]



