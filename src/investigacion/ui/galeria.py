"""Galería de casos persistidos: la entrada exploratoria de la interfaz."""

from __future__ import annotations

from typing import Any, Literal

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from investigacion.modelos import Caso, ModalidadInferencia
from investigacion.ui.dialogos import dialogo_alta, dialogo_baja
from investigacion.ui.metricas import detecciones, hosts_del_caso, severidad_caso
from investigacion.ui.servicio import ServicioDeCasos

_ColorBadge = Literal[
    "red", "orange", "yellow", "blue", "green", "violet", "gray", "grey", "primary"
]

_ETIQUETA_MODALIDAD: dict[ModalidadInferencia, tuple[str, _ColorBadge]] = {
    ModalidadInferencia.NODO_PRIVADO: ("nodo privado", "green"),
    ModalidadInferencia.MODELO_LOCAL: ("modelo local", "green"),
    ModalidadInferencia.MODELO_EXTERNO: ("modelo externo", "orange"),
    ModalidadInferencia.DEGRADADO: ("modo degradado", "gray"),
}

_OPCIONES_MODALIDAD: dict[str, ModalidadInferencia | None] = {
    "todas": None,
    "externo": ModalidadInferencia.MODELO_EXTERNO,
    "local": ModalidadInferencia.MODELO_LOCAL,
    "degradado": ModalidadInferencia.DEGRADADO,
}

_TONO_SEVERIDAD: dict[str, str] = {
    "critical": "red",
    "high": "orange",
    "medium": "yellow",
    "low": "blue",
    "informational": "gray",
}

# Tarjeta de caso como componente CCv2: todo el control visual y de clicks
# vive en el shadow root (título, badges, stats, ✕, click en cualquier lado).
# Los textos llegan por `data` y se asignan con textContent: son valores
# persistidos/editables por el operador y no deben interpretarse como HTML.
# El registro se hace en cada ejecución del script (una vez por run, en
# `mostrar`): el registro de componentes es por instancia de app y en
# AppTest cada test monta una app nueva.
def _tarjeta_componente() -> Any:
    return st.components.v2.component(
        "tarjeta_caso",
    html="""
<div class="card" role="button" tabindex="0">
  <button class="del" type="button" aria-label="Eliminar caso" title="Eliminar caso">✕</button>
  <div class="titulo"></div>
  <div class="badges"></div>
  <div class="linea stats"></div>
  <div class="linea host"></div>
  <div class="hint">Abrir caso →</div>
</div>
""",
    css="""
:host { display: block; }
.card {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  min-height: 10rem;
  padding: .9rem 1rem .8rem;
  border: 1px solid var(--st-border-color-light, rgba(140,140,150,.3));
  border-radius: var(--st-base-radius, .75rem);
  background: var(--st-secondary-background-color, rgba(140,140,150,.07));
  color: var(--st-text-color, inherit);
  font-family: var(--st-font, inherit);
  cursor: pointer;
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
}
.card:hover {
  border-color: var(--st-primary-color, #4c9aff);
  box-shadow: 0 6px 18px rgba(0, 0, 0, .28);
  transform: translateY(-1px);
}
.card:focus-visible {
  outline: 2px solid var(--st-primary-color, #4c9aff);
  outline-offset: 2px;
}
.del {
  position: absolute;
  top: .5rem;
  right: .5rem;
  width: 1.55rem;
  height: 1.55rem;
  border-radius: 50%;
  border: 1px solid var(--st-border-color-light, rgba(140,140,150,.4));
  background: transparent;
  color: var(--st-gray-text-color, #9a9da8);
  font-size: .85rem;
  line-height: 1;
  padding: 0;
  cursor: pointer;
  transition: color .15s ease, border-color .15s ease;
}
.del:hover {
  border-color: var(--st-red-color, #ff4d4f);
  color: var(--st-red-text-color, #ff6b6b);
}
.titulo {
  font-weight: 600;
  font-size: .92rem;
  line-height: 1.3;
  padding-right: 1.4rem;
  margin-bottom: .55rem;
  word-break: break-word;
}
.badge {
  display: inline-block;
  font-size: .7rem;
  font-weight: 500;
  padding: .12rem .55rem;
  border-radius: 999px;
  margin: 0 .3rem .3rem 0;
}
.badge.green { background: var(--st-green-background-color); color: var(--st-green-text-color); }
.badge.orange { background: var(--st-orange-background-color); color: var(--st-orange-text-color); }
.badge.blue { background: var(--st-blue-background-color); color: var(--st-blue-text-color); }
.badge.violet { background: var(--st-violet-background-color); color: var(--st-violet-text-color); }
.badge.red { background: var(--st-red-background-color); color: var(--st-red-text-color); }
.badge.yellow { background: var(--st-yellow-background-color); color: var(--st-yellow-text-color); }
.badge.gray { background: var(--st-gray-background-color); color: var(--st-gray-text-color); }
.linea {
  font-size: .78rem;
  color: var(--st-gray-text-color, rgba(160,160,170,.9));
  margin-top: .4rem;
}
.hint {
  margin-top: .65rem;
  font-size: .78rem;
  letter-spacing: .03em;
  color: var(--st-link-color, #7aa8ff);
}
""",
    js="""
export default function (component) {
  const { parentElement, data, setTriggerValue } = component

  const card = parentElement.querySelector(".card")
  const titulo = parentElement.querySelector(".titulo")
  const badges = parentElement.querySelector(".badges")
  const stats = parentElement.querySelector(".stats")
  const host = parentElement.querySelector(".host")
  const del = parentElement.querySelector(".del")
  if (!card || !titulo || !badges || !stats || !host || !del) return

  titulo.textContent = data.titulo ?? ""
  stats.textContent = data.stats ?? ""
  host.textContent = data.host ?? ""
  card.setAttribute("aria-label", "Abrir caso " + (data.titulo ?? ""))

  badges.replaceChildren()
  for (const b of data.badges ?? []) {
    const s = document.createElement("span")
    s.className = "badge " + (b.tono ?? "gray")
    s.textContent = b.etiqueta ?? ""
    badges.appendChild(s)
  }

  const abrir = () => setTriggerValue("open", data.id)
  card.onclick = abrir
  card.onkeydown = e => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      abrir()
    }
  }
  del.onclick = e => {
    e.stopPropagation()
    setTriggerValue("delete", data.id)
  }
}
""",
)


def _abrir(caso_id: str) -> None:
    st.session_state["caso_abierto"] = caso_id
    st.session_state.pop("evento_abierto", None)


def _badges(servicio: ServicioDeCasos, caso: Caso) -> list[dict[str, str]]:
    badges: list[dict[str, str]] = []
    modalidad = caso.modalidad_inferencia
    if modalidad is not None:
        etiqueta, tono = _ETIQUETA_MODALIDAD.get(modalidad, (modalidad.value, "gray"))
        badges.append({"etiqueta": etiqueta, "tono": tono})
    escenario = servicio.escenario_de(caso)
    if escenario is not None:
        badges.append({"etiqueta": escenario.tipo_evidencia, "tono": "blue"})
    severidad = severidad_caso(caso)
    if severidad != "sin detección":
        badges.append(
            {"etiqueta": f"señal {severidad}", "tono": _TONO_SEVERIDAD[severidad]}
        )
    return badges


def _tarjeta(
    servicio: ServicioDeCasos,
    caso: Caso,
    columna: DeltaGenerator,
    tarjeta: Any,
) -> None:
    hosts = hosts_del_caso(caso)
    with columna:
        resultado = tarjeta(
            key=f"card-{caso.id}",
            data={
                "id": caso.id,
                "titulo": servicio.titulo_de(caso),
                "badges": _badges(servicio, caso),
                "stats": (
                    f"{len(caso.eventos)} eventos · "
                    f"{len(detecciones(caso))} detecciones · "
                    f"{len(caso.hallazgos)} hallazgos"
                ),
                "host": f"Host: {', '.join(hosts) if hosts else 'no declarado'}",
            },
        )
    if getattr(resultado, "open", None):
        _abrir(str(resultado.open))
        st.rerun()
    if getattr(resultado, "delete", None):
        st.session_state["baja_pendiente"] = str(resultado.delete)


def _filtrar(servicio: ServicioDeCasos) -> tuple[Caso, ...]:
    casos = servicio.casos()
    busqueda = st.session_state.get("busqueda-casos", "").strip().casefold()
    modalidad = _OPCIONES_MODALIDAD.get(
        st.session_state.get("filtro-modalidad", "todas")
    )
    if modalidad is not None:
        casos = tuple(
            caso for caso in casos if caso.modalidad_inferencia == modalidad
        )
    if busqueda:
        casos = tuple(
            caso
            for caso in casos
            if busqueda in servicio.titulo_de(caso).casefold()
            or busqueda in " ".join(hosts_del_caso(caso)).casefold()
            or busqueda in caso.id.casefold()
        )
    return casos


def mostrar(servicio: ServicioDeCasos) -> None:
    st.title("Asistente privado de investigación")
    st.warning(
        "Los hallazgos son hipótesis pendientes de revisión humana. PsExec, "
        "PowerShell, SMB y una técnica ATT&CK candidata no confirman por sí "
        "solos un compromiso."
    )
    if not servicio.puede_importar:
        st.info(
            "Sin ejecutable Hayabusa configurado la interfaz funciona en modo "
            "lectura sobre los casos persistidos."
        )

    encabezado, accion = st.columns([4, 1])
    encabezado.subheader("Casos")
    if accion.button("＋ Nuevo caso", type="primary", width="stretch"):
        dialogo_alta(servicio)

    todos = servicio.casos()
    if not todos:
        st.info(
            "No hay casos persistidos. Importá un EVTX con “Nuevo caso” o por "
            "CLI con `python -m investigacion.importar`."
        )
        return

    busqueda, filtro, _ = st.columns([2, 3, 2])
    busqueda.text_input(
        "Buscar", placeholder="título, host o id…", key="busqueda-casos",
        label_visibility="collapsed",
    )
    filtro.segmented_control(
        "Modalidad",
        options=list(_OPCIONES_MODALIDAD),
        default="todas",
        key="filtro-modalidad",
        label_visibility="collapsed",
    )

    casos = _filtrar(servicio)
    if not casos:
        st.caption("Ningún caso coincide con el filtro.")
        return

    tarjeta = _tarjeta_componente()
    columnas = st.columns(4)
    for indice, caso in enumerate(casos):
        _tarjeta(servicio, caso, columnas[indice % 4], tarjeta)

    pendiente = st.session_state.pop("baja_pendiente", None)
    if pendiente:
        caso_baja = servicio.repositorio.obtener(pendiente)
        if caso_baja is not None:
            dialogo_baja(servicio, caso_baja)
