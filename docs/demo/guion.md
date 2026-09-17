# Guion de la demo — tres minutos (issue #12)

Recorrido: galería → alta (sin ejecutar) → pestañas del caso → números Sigma →
matriz ATT&CK → hipótesis IA → con/sin contexto → exportación → fallback.
Cada bloque tiene su plan B.

## Antes de empezar (operador, fuera del tiempo)

- `scripts/preparar_demo.sh` en verde.
- Streamlit abierto: `INVESTIGACION_DATOS=datos uv run streamlit run src/investigacion/ui/app.py`.
- La galería ya está poblada: ~20 casos del dataset público
  EVTX-ATTACK-SAMPLES pre-procesados (Hayabusa real + inferencia externa
  declarada como tal), más los casos ancla del proyecto.
- Pestaña de respaldo lista: `docs/demo/respaldo/informe.md` abierto en el
  editor, identificado como corrida guardada.

## 0:00–0:20 — Qué es y qué no es

"Asistente privado de investigación sobre registros Windows: cada afirmación
del modelo queda validada por código antes de persistir, y la evidencia
conserva su cadena de custodia." Mostrar la galería: badges de modalidad de
inferencia (modelo externo / modelo local / modo degradado) y escenario.

## 0:20–0:45 — Alta (se muestra, no se ejecuta)

- Botón "＋ Nuevo caso": se abre el modal con drag & drop de EVTX, campo de
  procedencia y campo de contexto del ambiente.
- "El pipeline corre Hayabusa y después el modelo; la inferencia insume
  minutos en CPU local, así que por tiempo no la ejecutamos en vivo — la
  galería entera se generó con este mismo pipeline esta noche."
- Cerrar el modal sin importar.

## 0:45–1:30 — Caso, cronología y números Sigma

- Abrir un caso rico (p.ej. "PsExec + SMB + Meterpreter").
- Pestaña Resumen: métricas, fuente, SHA-256, custodia.
- Pestaña Cronología: línea de tiempo visual por canal con detecciones
  marcadas + tabla navegable; abrir un evento para mostrar campos
  normalizados y procedencia.
- Pestaña Hallazgos: números Sigma (eventos con detección, reglas que
  activaron, técnicas heredadas) y matriz ATT&CK con chips por táctica,
  distinguiendo azul "heredado de regla" vs violeta "sugerida por el modelo".

## 1:30–2:10 — Hipótesis IA y contexto

- Pestaña "Hipótesis IA": badge persistente "generado por IA", interpretación
  propuesta, razón del vínculo, explicaciones alternativas, evidencia
  faltante, limitaciones. "Todo esto es revisable; nada es veredicto."
- Comparación con/sin contexto: abrir las dos variantes del caso LSASS
  ("sin contexto" / "con contexto") — la misma evidencia, narrativa distinta.
  El contexto declarado viaja al prompt como contexto, no como instrucción.

## 2:10–2:40 — Exportación y custodia

- Botón "Exportar…" en la pestaña Exportar: modal con informe
  (Markdown/HTML/JSON), eventos normalizados y artefactos conservados
  (EVTX original, JSONL de Hayabusa) byte a byte.
- Custodia: `python -m investigacion.informe --verificar
  docs/demo/respaldo/informe.md` → "Informe íntegro".

## 2:40–3:00 — Fallback y cierre

- Abrir un caso "solo Hayabusa": modalidad degradada, cronología y
  detecciones intactas, sin hipótesis del modelo. "Si el motor cae, el caso
  sigue siendo navegable."
- Cierre con los números del #11: LLM directo obedeció la inyección 3/3;
  el pipeline 0/3 con 12/12 técnicas respaldadas.

## Si algo falla

El respaldo `docs/demo/respaldo/` contiene la corrida guardada completa
(casos.sqlite + informe sellado). Señalarla como tal —"esto es una
ejecución anterior guardada, no en vivo"— y continuar el guion sobre el
informe exportado. Procedimiento completo en `operacion.md`.
