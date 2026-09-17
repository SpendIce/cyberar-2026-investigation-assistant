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

La interfaz Streamlit abre el caso sembrado sin servicios externos o los casos
persistidos por Hayabusa y Ollama cuando se define `INVESTIGACION_DATOS`.
Muestra estado, cronología e hipótesis con referencias navegables, y permite
exportar el caso a Markdown o JSON.

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

## Sobrevivir a fallas de inferencia remota (#7)

`--modelo-respaldo` compone `InferenciaConRespaldo` (ADR-0011): si el nodo
privado declara inferencia no disponible (caído, timeout, respuesta
inválida), el caso se reintenta contra el modelo local sin intervención
manual. La transición queda registrada en `errores` con el motivo de la
caída — visible en Streamlit junto a la modalidad que produjo el resultado
— y, si ambos motores fallan, el caso persiste en modo degradado con la
cronología y la evidencia intactas. Ver [docs/respaldo.md](docs/respaldo.md).

## Rechazar hallazgos manipulados o inventados (#9)

El validador rechaza referencias a eventos inexistentes y técnicas fuera del
catálogo local, y el adaptador Ollama exige y revalida el esquema JSON
estructurado — sostenido incluso cuando un modelo obedece una instrucción
insertada en un campo de evidencia. Ver [docs/rechazo.md](docs/rechazo.md)
para el mapa completo de criterios de aceptación y evidencia.

## Informe reproducible (#10)

`python -m investigacion.informe --datos datos --caso <id> --formato markdown`
exporta el estado validado y persistido de un caso a Markdown o JSON (`--formato
json`), hacia `--salida <archivo>` o stdout. Lee únicamente `casos.sqlite`:
nunca vuelve a ejecutar la inferencia durante la exportación.

## Comparar actividad ambigua (#8)

La interfaz compara el EVTX público del tracer con un control administrativo
sintético/documentado usando los mismos componentes, sin convertir la
presencia de PsExec, PowerShell, SMB o ATT&CK en una conclusión de
compromiso. Ver
[escenarios, verdad de referencia separada y reproducción](docs/ambiguedad.md).

## Endpoints externos con decisión explícita

`InferenciaOllama` clasifica el endpoint antes de enviar evidencia
(ADR-0016): la infraestructura controlada —loopback, redes privadas,
overlays Tailscale y los hosts declarados con `--host-controlado`— no
requiere opt-in; un endpoint externo se rechaza como nodo no disponible
salvo `--permitir-externo`, y aun permitido la advertencia queda persistida
en el caso y visible en el informe. Ver [docs/inferencia.md](docs/inferencia.md).

## Cadena de custodia e integridad del informe

Cada escritura del repositorio encadena un sello nuevo al anterior
(append-only, ADR-0017); el informe publica el sello de la cabeza y el CLI
deja un `.sha256` junto al artefacto exportado. `verificar_caso` detecta
ediciones del estado persistido y reescrituras de la cadena;
`python -m investigacion.informe --verificar <informe>` detecta un archivo
alterado. Ver [docs/custodia.md](docs/custodia.md).

## Adaptador MCP (P1, ADR-0013)

`uv run investigacion-mcp --datos datos [--modelo ...]` expone las
operaciones del módulo como herramientas MCP por stdio: `listar_casos`,
`consultar_caso`, `investigar_caso`, `exportar_caso` y `verificar_caso`.
Sin `crear_caso`: la superficie no acepta rutas de archivo arbitrarias.

## Empaquetado de la demo (#12)

Guion de tres minutos, inventario fijado con licencias, respaldo de
presentación identificado, prueba de humo sin red y matriz de recuperación
con responsables: [docs/demo/](docs/demo/preparacion.md). Verificación
rápida: `scripts/preparar_demo.sh`; humo offline:
`scripts/prueba_humo_offline.sh`.

## Medir valor frente a Hayabusa y un LLM directo (#11)

`scripts/evaluar_enfoques.py` corre tres enfoques (Hayabusa solo, la
evidencia enviada directamente al modelo sin esquema ni validación y el
pipeline completo) sobre los mismos casos y contra la misma verdad de
referencia separada. Reporta aciertos, omisiones, referencias inválidas y falsas
afirmaciones como numeradores/denominadores, la obediencia a la instrucción
insertada por enfoque y la latencia/memoria de los recorridos local, remoto
y degradado que correspondan. Ver
[enfoques, casos, criterios y reproducción](docs/evaluacion/enfoques.md).
