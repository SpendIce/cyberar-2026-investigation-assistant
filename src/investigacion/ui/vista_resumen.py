"""Pestaña Resumen: estado, procedencia, contexto declarado y custodia."""

from __future__ import annotations

import streamlit as st

from investigacion.modelos import Caso, ModalidadInferencia
from investigacion.ui.metricas import (
    hosts_del_caso,
    numeros_sigma,
    severidad_caso,
    topologia_hosts,
)
from investigacion.ui.presentacion import estado_caso
from investigacion.ui.servicio import ServicioDeCasos
from investigacion.validacion import contiene_lenguaje_concluyente, prosa_revisable


def mostrar(servicio: ServicioDeCasos, caso: Caso) -> None:
    estado = dict(estado_caso(caso))
    numeros = numeros_sigma(caso)
    columnas = st.columns(6)
    columnas[0].metric("Eventos", len(caso.eventos))
    columnas[1].metric("Eventos detectados", numeros["eventos_con_deteccion"])
    columnas[2].metric("Hallazgos", estado["Hallazgos"])
    columnas[3].metric("Reglas Sigma que activaron", numeros["reglas_distintas"])
    columnas[4].metric("Técnicas heredadas", numeros["tecnicas_heredadas"])
    columnas[5].metric(
        "Señal máxima",
        severidad_caso(caso),
        help="La severidad (Level) más alta que marcaron las reglas "
        "defensivas sobre los eventos del caso.",
    )

    hosts = hosts_del_caso(caso)
    st.caption(
        f"Fuente: {estado['Fuente']} · SHA-256: `{estado['SHA-256']}` · "
        f"Procedencia: {estado['Procedencia']} · "
        f"Hosts: {', '.join(hosts) if hosts else 'no declarados'}"
    )

    if caso.contexto.strip():
        st.markdown(f"**Contexto declarado por el operador:** {caso.contexto}")
    else:
        st.caption("Sin contexto declarado: la narrativa se apoya sólo en la evidencia.")

    st.subheader("Interpretación del modelo")
    if caso.hallazgos:
        st.badge("Generado por IA · pendiente de revisión humana", color="violet")
        for hallazgo in caso.hallazgos:
            if contiene_lenguaje_concluyente(prosa_revisable(hallazgo)):
                st.markdown(
                    "- *Formulación no mostrada: lenguaje concluyente "
                    "incompatible con una hipótesis pendiente de revisión.*"
                )
            else:
                st.markdown(f"- {hallazgo.hipotesis}")
        st.caption(
            "Son hipótesis sobre la evidencia, no un veredicto: el detalle "
            "de referencias, alternativas y evidencia faltante está en la "
            "pestaña Hipótesis IA."
        )
    elif caso.modalidad_inferencia == ModalidadInferencia.DEGRADADO:
        st.caption(
            "Sin interpretación del modelo: el caso se procesó sólo con "
            "reglas defensivas (modo degradado)."
        )
    else:
        st.caption("El motor no produjo hipótesis para este caso.")

    topologia = topologia_hosts(caso)
    if topologia:
        st.subheader("Topología observada")
        lineas = [
            "digraph {",
            'rankdir="LR";',
            'node [shape=box style=filled fillcolor="#1f2937" fontcolor="#e5e7eb"];',
            'edge [color="#9d9da8" dir=none];',
        ]
        for host, remotos in topologia.items():
            for remoto in sorted(remotos):
                lineas.append(f'"{host}" -> "{remoto}";')
        lineas.append("}")
        st.graphviz_chart("\n".join(lineas))
        st.caption(
            "Aristas sin dirección: son referencias observadas en campos de "
            "la evidencia (IPs de origen, destinos, workstations). Una "
            "referencia no implica compromiso ni dirección de ataque."
        )

    if caso.errores:
        st.warning(
            "Advertencias registradas:\n" + "\n".join(f"- {e}" for e in caso.errores)
        )

    st.subheader("Custodia")
    cadena = servicio.repositorio.cadena_custodia(caso.id)
    st.caption(f"{len(cadena)} escrituras encadenadas en la cadena del caso.")
    if st.button("Verificar integridad", key="verificar-custodia"):
        verificacion = servicio.modulo.verificar_caso(caso.id)
        if verificacion.integro:
            st.success(f"Caso íntegro. Sello: `{verificacion.sello}`")
        else:
            st.error("Discrepancias: " + "; ".join(verificacion.discrepancias))

    with st.expander("Modificar caso"):
        nuevo_nombre = st.text_input(
            "Nombre visible", value=servicio.titulo_de(caso), key="renombrar"
        )
        if st.button("Renombrar", key="boton-renombrar"):
            servicio.modulo.renombrar_caso(caso.id, nuevo_nombre)
            st.rerun()
        nuevo_contexto = st.text_area(
            "Contexto declarado",
            value=caso.contexto,
            key="editar-contexto",
            help="Describe el ambiente del host; viaja al prompt al re-inferir.",
        )
        guardar, reinferir = st.columns(2)
        if guardar.button("Guardar contexto", key="boton-contexto"):
            servicio.modulo.actualizar_contexto(caso.id, nuevo_contexto)
            st.rerun()
        if reinferir.button(
            "Guardar y re-inferir",
            key="boton-reinferir",
            help="Vuelve a correr el motor de inferencia con el contexto nuevo.",
        ):
            servicio.modulo.actualizar_contexto(caso.id, nuevo_contexto)
            with st.spinner("Re-infiriendo con el contexto declarado…"):
                servicio.modulo.investigar_caso(caso.id)
            st.rerun()
