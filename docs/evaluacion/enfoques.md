# Medir valor frente a Hayabusa y un LLM directo (#11)

La evaluación corre tres enfoques sobre los mismos casos y contra la misma
verdad de referencia para sostener o refutar con evidencia que el pipeline
completo agrega valor respecto de sus baselines. No mide un porcentaje de
confianza: cuenta aciertos, omisiones, referencias inválidas y falsas
afirmaciones como numeradores y denominadores (ADR-0006).

## Los tres enfoques

- **Hayabusa solo**: las detecciones de reglas y sus mapeos ATT&CK
  heredados, sin inferencia. Es lo que el motor de detección pone sobre la
  mesa antes de cualquier análisis. Determinista por construcción: una sola
  corrida lo representa.
- **LLM directo**: la misma evidencia serializada (los mismos campos
  citables que recibe el pipeline) enviada al mismo endpoint con un pedido
  naive: sin esquema de salida, sin catálogo permitido, sin instrucción
  contra instrucciones insertadas y sin validación posterior. Lo que el
  modelo escriba es la salida final; no hay capa de rechazo.
- **Pipeline completo**: `InferenciaOllama` con prompt restringido y
  esquema JSON, más `ValidadorDeReferencias` (referencias existentes,
  técnicas del catálogo local fijado, lenguaje no concluyente). Una
  afirmación que no supera la validación queda contada como bloqueada, no
  como salida visible.

## Los casos

- **A, `actividad-psexec-publica`**: el caso real persistido por el tracer
  de #6 desde el EVTX público fijado en `tests/fixtures/publico/manifest.json`.
- **B, `administracion-autorizada-sintetica`**: el control legítimo
  sintético/documentado de `eventos_control_legitimo()` (ADR-0015). Nunca
  fue procesado por Hayabusa real, así que el enfoque "Hayabusa solo" no
  tiene detecciones ahí: su superficie es vacía por construcción, no por
  falla del motor.
- **D, `manipulacion-campo-evidencia`**: el fixture de `tests/casos_evaluacion.py`
  con la instrucción insertada que pide citar `ev-inventado-99` y
  `T9999-NO-EXISTE`. Se documenta para cada enfoque si el modelo obedeció
  la instrucción y si la salida final persistió lo inventado.

## La verdad de referencia

Vive en `docs/evaluacion/verdad-referencia-escenarios.json`, separada del
material que recibe el modelo: no entra en `Caso`, `Evento`, SQLite ni en
la solicitud (hay una prueba que inspecciona la solicitud capturada). Cada
escenario declara `evidencia_esperada` con criterios mecánicos
(`campo`+`contiene` contra los eventos que el enfoque pone sobre la mesa;
`en_texto` contra su prosa), `tecnicas_respaldadas` dentro del catálogo
local fijado y `conclusiones_prohibidas` con la misma guarda de negación
que `contiene_lenguaje_concluyente`.

El scoring mecánico vive en `src/investigacion/evaluacion.py` y está
cubierto por `tests/test_evaluacion_enfoques.py` con casos deterministas;
las mediciones en vivo quedan en el reporte generado, no en pruebas.

## Reproducir

Requiere el caso A ya importado (ver `docs/tracer.md`) y un endpoint
Ollama con el modelo descargado:

```bash
uv run python scripts/evaluar_enfoques.py \
  --modelos qwen2.5:7b-instruct \
  --repeticiones 3 \
  --datos datos --caso-sospechoso ID_DEL_CASO_REAL \
  --evtx datos/evidencia/<importacion>/original.evtx \
  --hayabusa /ruta/hayabusa-4.1.0/hayabusa \
  --memoria-comando "ollama ps"
```

Con Ollama en Docker, `--memoria-comando "docker exec ollama-eval ollama ps"`.
Sin `--datos`/`--caso-sospechoso` el caso A se reporta como no ejecutado.
Para el recorrido del nodo privado: `--ollama-url-remoto` y
`--modelo-remoto`; si no se configuran, el reporte lo declara no
configurado en esta máquina. El recorrido degradado se mide siempre:
agota el fallback contra endpoints inalcanzables y reporta la latencia del
recorrido completo.

Escribe `docs/evaluacion/resultados-enfoques.json` (salidas y puntuaciones
por corrida) y `docs/evaluacion/resultados-enfoques.md` (tablas agregadas
por caso y enfoque, costo operativo y lectura mecánica que permite sostener
o refutar el valor agregado).

## Qué reporta

- Aciertos y omisiones sobre la evidencia esperada, por caso y enfoque.
- Referencias inválidas sobre las generadas (uids o identificadores
  etiquetados que no resuelven a evidencia del caso).
- Falsas afirmaciones sobre las revisadas (veredictos prohibidos, lenguaje
  concluyente, referencias o técnicas inventadas), y cuántas el pipeline
  bloqueó antes de mostrarlas.
- Obediencia a la instrucción insertada y persistencia de lo inventado en
  el caso D, por enfoque.
- Latencia por corrida y memoria reportada por el runtime, para los
  recorridos local, remoto y degradado que correspondan.
