# Operación de la demo — responsabilidades y recuperación (issue #12)

## Roles

| Integrante | Rol | Responsabilidad |
|---|---|---|
| 1 | Presentador | Narrativa y guion (`guion.md`); decide cuándo cortar al respaldo. |
| 2 | Operador | Ejecuta los comandos, monitorea `ollama ps` y el terminal; corre `preparar_demo.sh` antes de la exposición. |
| 3 | Respaldo | Mantiene `docs/demo/respaldo/` visible y ejecuta el procedimiento de recuperación si algo falla. |

Regla de oro: **el respaldo se presenta como respaldo** — nunca se sugiere
que una corrida guardada es una ejecución en vivo.

## Matriz de recuperación

| Falla | Señal | Acción |
|---|---|---|
| Ollama cae o el modelo no responde | el caso persiste en modalidad `degradado` con el motivo en Advertencias | Es el comportamiento diseñado: mostrarlo como feature, no como falla. Continuar con cronología y evidencia. |
| El endpoint remoto es externo sin opt-in | `InferenciaNoDisponible` "fuera de la infraestructura controlada" | Declarar `--permitir-externo` o caer al modelo local; la advertencia queda en el caso. |
| Pregunta sobre la inferencia de la galería | "¿quién generó estas hipótesis?" | Casos marcados `modelo_externo`: pre-procesados con `deepseek-v4-flash` vía opencode Zen sobre EVTX públicos; la advertencia de soberanía está persistida en cada caso y el pipeline corre igual en local con Ollama. |
| Streamlit no abre | puerto ocupado / crash | Operador relanza `streamlit run`; el presentador sigue sobre `respaldo/informe.md` mientras tanto. |
| Sin red en la sala | curl/DNS fallan | Nada que hacer: el recorrido no usa cloud. Correr `prueba_humo_offline.sh` si se quiere demostrar. |
| La base de casos no abre | sqlite error / archivo ausente | Respaldo: apuntar `INVESTIGACION_DATOS=docs/demo/respaldo/datos` o usar el informe exportado directamente. |
| Duda sobre el informe mostrado | "¿esto es en vivo?" | `--verificar docs/demo/respaldo/informe.md` prueba integridad del artefacto; el sello del caso está en la sección Integridad. |

## Procedimiento de recuperación ante falla total

1. Respaldo abre `docs/demo/respaldo/informe.md` (corrida guardada,
   identificada como tal) y continúa el guion sobre el documento:
   cronología, hallazgo, ambigüedad, integridad.
2. Operador intenta restablecer lo vivo en paralelo (ollama, streamlit);
   si vuelve, se retoma el recorrido en vivo aclarando la transición.
3. Si nada vuelve, el guion se completa íntegro sobre el informe: todos
   los beats tienen su equivalente en el documento sellado.
