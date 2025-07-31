import streamlit as st
import pandas as pd
from database.crud.nota_credito import (
    obtener_notas_credito,
    insertar_nota_credito,
    eliminar_nota_credito
)

def reset_nc_form():
    """Reinicia los campos del formulario de nueva nota."""
    st.session_state.pop("new_no_factura", None)
    st.session_state.pop("new_tipo_nc", None)
    st.session_state.pop("new_valor_nc", None)
    st.session_state.pop("new_razon", None)

def show():
    st.subheader("Notas Crédito")

    # --- Entrada de No Solicitud ---
    no_solicitud = st.text_input("Número del Caso (M)*", key="nc_no_solicitud")

    if no_solicitud:
        # --- Mostrar Notas de Crédito Existentes ---
        notas = obtener_notas_credito(no_solicitud)

        if notas:
            df_notas = pd.DataFrame(notas)[["id_nc", "no_factura", "tipo_nc", "valor_nc", "razon"]]
            df_notas = df_notas.rename(columns={
                "id_nc": "ID Nota",
                "no_factura": "Número Factura",
                "tipo_nc": "Tipo de Nota",
                "valor_nc": "Valor",
                "razon": "Razón"
            })
            st.dataframe(df_notas, use_container_width=True)

            # --- Selección de Nota para Eliminar ---
            with st.expander("🗑 Eliminar Nota"):
                selected_id = st.selectbox(
                    "Seleccione el ID de la Nota a Eliminar",
                    [n["id_nc"] for n in notas],
                    key="delete_nc_id"
                )
                if st.button("🗑 Eliminar Nota Crédito", key="delete_nc_btn"):
                    try:
                        eliminar_nota_credito(selected_id)
                        st.success("Nota de crédito eliminada.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("No hay notas de crédito registradas para este caso.")

        # --- Agregar Nueva Nota ---
        with st.expander("➕ Agregar Nueva Nota de Crédito"):
            no_factura = st.text_input("Número de Factura (TS)*", key="new_no_factura")
            tipo_nc = st.selectbox("Tipo de Nota Credito", ["Valor Parcial", "Valor Total"], key="new_tipo_nc")

            valor_nc = 0.0
            if tipo_nc == "Valor Parcial":
                valor_nc = st.number_input("Ingrese el valor", min_value=0.0, step=0.1, key='new_valor_nc')

            # --- Razón de la Nota ---
            razon = st.selectbox(
                "Razón de la Nota Crédito*",
                [
                    "CAMBIOS DE VENTA - COMERCIAL O CUSTOMER",
                    "CLIENTE SOLICITA FACTURAR A OTRA RAZON SOCIAL",
                    "NO ENTRO EN EL CIERRE DE MES",
                    "FALTO PO"
                ],
                key="new_razon"
            )

            if st.button("💾 Guardar Nueva Nota", key="save_new_nc"):
                if no_factura:
                    try:
                        insertar_nota_credito(no_solicitud, no_factura, tipo_nc, valor_nc, razon)
                        st.success("Nueva nota de crédito guardada.")

                        # Resetear campos y recargar
                        reset_nc_form()
                        st.success("Nueva nota de crédito guardada.")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Debe ingresar el Número de Factura.")
    else:
        st.warning("Ingrese el Número de Caso (M)* para ver o agregar notas.")
