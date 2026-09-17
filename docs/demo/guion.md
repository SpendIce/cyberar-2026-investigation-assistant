# Guion de la demo — tres minutos (issue #12)

Recorrido: importación → hallazgo → evidencia → ambigüedad → ATT&CK →
exportación → fallback. Cada bloque tiene su comando y su plan B.

## Antes de empezar (operador, fuera del tiempo)

- `scripts/preparar_demo.sh` en verde; modelo precargado (`ollama ps`
  muestra `qwen2.5:7b-instruct` residente).
- Streamlit abierto: `INVESTIGACION_DATOS=datos uv run streamlit run src/investigacion/ui/app.py`.
- Pestaña de respaldo lista: `docs/demo/respaldo/informe.md` abierto en el
  editor, identificado como corrida guardada.

## 0:00–0:20 — Qué es y qué no es

"Asistente privado de investigación: la evidencia no sale de infraestructura
propia, y cada afirmación del modelo queda validada antes de persistir."

## 0:20–0:50 — Importación y cronología

- Mostrar el caso importado en Streamlit: procedencia, SHA-256 del EVTX
  original conservado, cronología ordenada con `uid` estables.
- Plan B (importación en vivo si sobra tiempo): `python -m investigacion.importar
  --evtx tests/fixtures/publico/eventos.evtx --procedencia <fixture>
  --hayabusa <binario> --datos datos`.

## 0:50–1:30 — Hallazgo, evidencia y ambigüedad

- Abrir el hallazgo: hipótesis + referencias navegables a los eventos
  (`ev-*`) + procedencia del mapeo ATT&CK (regla vs modelo).
- Ambigüedad: mostrar el control legítimo — PsExec/PowerShell/SMB también
  aparecen en administración legítima; el hallazgo incluye explicaciones
  alternativas y evidencia faltante, no un veredicto.
- "El modelo propone hipótesis; el código valida referencias, técnicas del
  catálogo y lenguaje concluyente."

## 1:30–2:10 — Fallback y custodia

- Fallback: "si el nodo de inferencia cae, el caso persiste en modo
  degradado con cronología y evidencia intactas" — mostrar la modalidad y
  las advertencias registradas en el caso (o correr
  `scripts/prueba_humo_offline.sh` si se quiere mostrar en vivo).
- Custodia: `python -m investigacion.informe --verificar docs/demo/respaldo/informe.md`
  → "Informe íntegro". Mencionar que el estado del caso también está
  encadenado: una edición directa de la base se detecta al verificar.

## 2:10–2:45 — Exportación y valor medido

- `python -m investigacion.informe --datos datos --caso <id> --salida informe.md`
  → informe + `informe.md.sha256` + sección Integridad con el sello del caso.
- Cierre con el resultado del #11: ante la instrucción insertada, el LLM
  directo obedeció 3/3 y persistió datos inventados 3/3; el pipeline 0/3
  con 12/12 técnicas respaldadas. Números en `docs/evaluacion/resultados-enfoques.md`.

## 2:45–3:00 — Reserva

Preguntas, o mostrar el adaptador MCP (`investigacion-mcp --datos datos`)
si el jurado pregunta por integración con asistentes institucionales.

## Si algo falla

El respaldo `docs/demo/respaldo/` contiene la corrida guardada completa
(casos.sqlite + informe sellado). Señalarla como tal —"esto es una
ejecución anterior guardada, no en vivo"— y continuar el guion sobre el
informe exportado. Procedimiento completo en `operacion.md`.
