# Rechazar hallazgos manipulados o inventados (#9)

La mayoría de los mecanismos que pide #9 ya existían como consecuencia de
#4 y #6: `ValidadorDeReferencias` rechaza referencias inexistentes y
técnicas fuera del catálogo local, `InferenciaOllama` exige y revalida el
esquema JSON estructurado, y `tests/casos_evaluacion.eventos_manipulados`
ya era el fixture de manipulación usado por `test_manipulacion_ollama_real.py`
(opt-in, contra un Ollama real). Lo que #9 agrega es la prueba explícita, sin
red, de que ese rechazo se sostiene aunque el modelo "obedezca" — y la
mapea uno a uno contra sus criterios de aceptación.

## Mapa de criterios de aceptación → evidencia

| Criterio | Dónde se prueba |
|---|---|
| Un fixture contiene una instrucción de prompt injection dentro de evidencia no confiable y no altera las instrucciones del análisis | `tests/casos_evaluacion.eventos_manipulados` (evidencia); `PROMPT_SISTEMA` en `adaptadores/ollama.py` trata el contenido del evento como dato citable, nunca como instrucción (nota 1) |
| Se rechazan respuestas que no cumplen el esquema estructurado | `tests/test_inferencia_ollama.py` (5 variantes: objeto vacío, `hallazgos` no es lista, falta `hipotesis`, `hipotesis` en blanco, `referencias_eventos` no es lista) |
| Se rechazan referencias a eventos inexistentes y técnicas ATT&CK fuera del subconjunto local permitido | `validacion.py` (`ValidadorDeReferencias`); `tests/test_contrato_investigacion.py` y **`tests/test_rechazo_hallazgos.py`** (nuevo, determinista, usa el fixture de manipulación) |
| Los rechazos dejan un motivo auditable y no destruyen ni ocultan la evidencia original | `tests/test_rechazo_hallazgos.py::test_la_instruccion_insertada_se_conserva_como_dato_sin_alterar_la_evidencia`; también `test_manipulacion_ollama_real.py` contra un modelo real |
| Las pruebas cubren cada clase de fallo y verifican que ningún hallazgo inválido llegue al estado validado | Las cuatro clases (esquema, referencia inventada, técnica inventada, instrucción insertada) tienen al menos una prueba determinista que no depende de un servidor Ollama |

1. `test_rechazo_hallazgos.py::test_la_instruccion_insertada_llega_al_modelo_como_dato_sin_alterar_el_prompt` espía el payload enviado y verifica que la inyección viaja sólo dentro de `contenido` del evento serializado, con el mensaje de sistema intacto.

## Qué agrega `test_rechazo_hallazgos.py`

Las pruebas previas de referencia/técnica inventada (`test_contrato_investigacion.py`)
usan una propuesta de hallazgo genérica, no el fixture de manipulación en sí.
La única prueba que usaba `eventos_manipulados()` para probar el rechazo real
era `test_manipulacion_ollama_real.py`, opt-in: **`uv run pytest` solo, sin
ninguna variable de entorno, nunca ejercitaba ese fixture.**

`test_rechazo_hallazgos.py` cierra ese hueco: construye un
`InferenciaControlada` que devuelve exactamente lo que un modelo *obediente*
a la instrucción insertada produciría (cita el evento y la técnica
inventados), y verifica que:

1. una referencia inventada se rechaza y no se persiste;
2. una técnica inventada se rechaza y no se persiste (por separado, porque
   `ValidadorDeReferencias` verifica referencias antes que técnicas y falla
   rápido en la primera violación — no hace falta que ambas fallen a la vez
   para que el hallazgo se rechace);
3. la instrucción insertada sigue presente, sin alterar, en `contenido` del
   evento después de investigar el caso — no se "limpia" ni se pierde; y
4. la instrucción insertada llega al modelo sólo como dato: el payload espiado
   muestra que viaja dentro de `contenido` del evento serializado mientras el
   mensaje de sistema queda intacto (`PROMPT_SISTEMA`).

```bash
uv run pytest tests/test_rechazo_hallazgos.py
```

## Qué sigue dependiendo de un Ollama real

`test_manipulacion_ollama_real.py` (opt-in, ver `docs/inferencia.md`) sigue
siendo la única prueba que demuestra esto contra un modelo real en vez de un
doble: que la resistencia del sistema no depende de que el modelo "se porte
bien", sino de la validación en código. Ambas pruebas son necesarias y
complementarias, no redundantes: la determinista prueba la garantía del
código; la real prueba que la garantía sostiene incluso cuando el modelo se
deja engañar (documentado en ADR-0014: `llama3.2:3b` obedeció la instrucción
insertada 3/3 veces en esa evaluación).
