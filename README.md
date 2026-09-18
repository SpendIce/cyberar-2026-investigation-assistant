# Investigación local de eventos

Asistente privado que reconstruye actividad a partir de registros Windows exportados (EVTX), presenta evidencia consultable y propone hipótesis ATT&CK revisables — nunca veredictos.

## Requisitos

- Python 3.12 o superior
- [uv](https://docs.astral.sh/uv/)
- Para importar EVTX reales: Hayabusa 4.1.0 (`lin-x64-musl`)
- Para inferencia local: Ollama con `qwen2.5:7b-instruct`

## Comandos

```bash
uv sync                 # instala dependencias y el paquete local
uv run investigacion    # ejecuta la aplicación mínima (recorrido de demostración)
uv run streamlit run src/investigacion/ui/app.py   # abre la interfaz local
uv run pytest           # ejecuta la suite de pruebas
uv run mypy src         # verifica los tipos
```

La aplicación mínima recorre crear → investigar → consultar → exportar con adaptadores controlados.

## Interfaz

La interfaz Streamlit abre una **galería de casos**: el caso sembrado (sin
servicios externos) o los persistidos cuando se define `INVESTIGACION_DATOS`.
Desde la galería se dan de alta casos por arrastre de EVTX —con procedencia y
contexto del ambiente—, se renombran y se eliminan.

Cada caso se explora por pestañas:

- **Resumen**: métricas, fuente, SHA-256, contexto declarado, topología de
  hosts observada y verificación de custodia.
- **Cronología**: línea de tiempo visual por canal y tabla navegable; cada
  evento muestra campos normalizados y procedencia.
- **Hallazgos**: números Sigma (detecciones, reglas que activaron), matriz
  ATT&CK que distingue técnicas heredadas de regla vs sugeridas por el
  modelo, evidencia citada y revisión humana (aceptar/rechazar).
- **Hipótesis IA**: la interpretación del modelo, marcada de forma
  persistente como generada por IA, con explicaciones alternativas,
  evidencia faltante y limitaciones.
- **Exportar**: modal con el informe (Markdown, HTML o JSON), los eventos
  normalizados y los artefactos conservados de la importación (EVTX
  original, salida Hayabusa JSONL, manifiesto).

## Pipeline de evidencia

El adaptador Hayabusa y el repositorio SQLite importan un EVTX mediante
`ModuloDeInvestigacion`: conservan el original con SHA-256 y manifiesto de
importación, normalizan cada evento con `uid` estable y guardan la salida de
reglas completa dentro de cada evento. Ver
[preparación, comandos y pruebas](docs/evidencia.md) y
[docs/tracer.md](docs/tracer.md) para el recorrido EVTX → hallazgo →
evidencia con un único comando (`python -m investigacion.importar`).

## Motores de inferencia

- **Local/privado**: `InferenciaOllama` contra un nodo propio.
- **Externo declarado**: `InferenciaZen` (endpoint OpenAI-compatible de
  opencode Zen) para pre-procesado offline; la evidencia externa requiere
  opt-in explícito y la advertencia queda persistida en el caso.
- **Respaldo**: `InferenciaConRespaldo` (ADR-0011) reintenta contra el
  siguiente motor si el primero declara no disponible.
- **Degradado**: si todo motor falla, el caso persiste con cronología,
  detecciones y evidencia intactas, sin hipótesis nuevas.

La clasificación del endpoint es código (ADR-0016): loopback, redes privadas,
overlays Tailscale y `--host-controlado` no requieren opt-in; cualquier otro
destino se rechaza salvo `--permitir-externo`. Ver
[docs/inferencia.md](docs/inferencia.md) y [docs/respaldo.md](docs/respaldo.md).

## Contexto del operador

Cada caso admite un **contexto declarado** (rol del host, ventanas de
mantenimiento, herramientas autorizadas) que se almacena con el caso, viaja
al prompt como contexto —no como instrucción— y puede editarse y
re-inferirse. El mismo EVTX con y sin contexto produce narrativas distintas:
la comparación es visible en la galería. Ver
[escenarios y verdad de referencia separada](docs/ambiguedad.md).

## Validación y custodia

El validador rechaza referencias a eventos inexistentes, técnicas fuera del
catálogo local y lenguaje concluyente — sostenido incluso cuando un modelo
obedece una instrucción insertada en un campo de evidencia. Ver
[docs/rechazo.md](docs/rechazo.md).

Cada escritura del repositorio encadena un sello nuevo al anterior
(append-only, ADR-0017); el informe publica el sello de la cabeza y el CLI
deja un `.sha256` junto al artefacto. `verificar_caso` detecta ediciones del
estado persistido; `python -m investigacion.informe --verificar <informe>`
detecta un archivo alterado. Ver [docs/custodia.md](docs/custodia.md).

## Galería pre-procesada y demo

La galería se pobló con ~19 EVTX del dataset público
[EVTX-ATTACK-SAMPLES](https://github.com/sbousseaden/EVTX-ATTACK-SAMPLES)
procesados con `scripts/preprocesar_zen.py` (Hayabusa + `deepseek-v4-flash`,
modalidad `modelo_externo` declarada en cada caso). Guion de tres minutos,
inventario fijado con licencias, respaldo identificado y matriz de
recuperación en [docs/demo/](docs/demo/preparacion.md). Verificación rápida:
`scripts/preparar_demo.sh`; humo offline: `scripts/prueba_humo_offline.sh`.

## Evaluación

`scripts/evaluar_enfoques.py` corre tres enfoques (Hayabusa solo, evidencia
enviada directamente al modelo sin esquema ni validación, y el pipeline
completo) contra la misma verdad de referencia separada. Reporta aciertos,
omisiones, referencias inválidas y obediencia a instrucciones insertadas como
numeradores/denominadores. Ver
[enfoques, casos, criterios y reproducción](docs/evaluacion/enfoques.md).

## Adaptador MCP (ADR-0013)

`uv run investigacion-mcp --datos datos [--modelo ...]` expone las
operaciones del módulo como herramientas MCP por stdio: `listar_casos`,
`consultar_caso`, `investigar_caso`, `exportar_caso` y `verificar_caso`.
Sin `crear_caso`: la superficie no acepta rutas de archivo arbitrarias.
