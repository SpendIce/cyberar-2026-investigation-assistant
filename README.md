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
La CLI de importación funciona sin inferencia; la conexión con la interfaz corresponde
a la integración del tracer (#6). Ver [preparación, comandos y pruebas](docs/evidencia.md).
