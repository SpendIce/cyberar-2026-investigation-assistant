# Investigación local de eventos

Asistente privado que reconstruye actividad a partir de registros Windows exportados, presenta evidencia consultable y propone hipótesis ATT&CK revisables.

## Requisitos

- Python 3.12 o superior
- [uv](https://docs.astral.sh/uv/)

## Comandos

```bash
uv sync                 # instala dependencias y el paquete local
uv run investigacion    # ejecuta la aplicación mínima (recorrido de demostración)
uv run streamlit run src/investigacion/ui/app.py   # abre la interfaz local
uv run pytest           # ejecuta la suite de pruebas
uv run mypy src         # verifica los tipos
```

La aplicación mínima recorre crear → investigar → consultar → exportar con adaptadores controlados.

La interfaz Streamlit abre el mismo caso sembrado sin servicios externos: muestra el estado del caso, su cronología y un hallazgo con referencias de evidencia. Cada referencia abre el evento citado junto con su procedencia, y el caso puede exportarse a Markdown o JSON. Streamlit es sólo un adaptador de presentación; las integraciones reales con Hayabusa y Ollama se incorporan en tickets posteriores.

## Importación de evidencia real (#3)

El adaptador Hayabusa y el repositorio SQLite permiten importar un EVTX mediante
`ModuloDeInvestigacion`, conservar su original y consultar una cronología verificable.
Ver [preparación, comandos y pruebas](docs/evidencia.md).

## Tracer real EVTX → hallazgo → evidencia (#6)

Un único comando (`python -m investigacion.importar` con `--modelo`) crea un caso
real desde el fixture EVTX acordado: Hayabusa, normalización, persistencia SQLite,
inferencia estructurada contra Ollama y validación. La interfaz Streamlit abre los
casos persistidos con `INVESTIGACION_DATOS` y permite navegar cada hallazgo hasta
la evidencia citada. Ver [docs/tracer.md](docs/tracer.md).

## Informe reproducible (#10)

`python -m investigacion.informe --datos datos --caso <id> --formato markdown`
exporta el estado validado y persistido de un caso a Markdown o JSON (`--formato
json`), hacia `--salida <archivo>` o stdout. Lee únicamente `casos.sqlite`:
nunca vuelve a ejecutar la inferencia durante la exportación.
