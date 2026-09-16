# Pruebas realizadas

Este documento explica qué prueba cada archivo de `tests/`, cómo correrlas y
qué garantiza (y qué no) la suite actual. Sigue la política de pruebas del
spec (#1): cruzan la interfaz del módulo de investigación, no funciones
privadas ni prompts literales, y el primer patrón TDD del repositorio se
mantiene en los tickets posteriores.

## Cómo correrlas

```bash
uv sync
uv run pytest         # suite ordinaria, sin red ni binarios externos
uv run mypy src        # tipado estricto
```

La suite ordinaria (`uv run pytest`) usa siempre dobles deterministas —
`EvidenciaControlada`, `InferenciaControlada`, transporte HTTP sustituido,
`RepositorioEnMemoria` — nunca Hayabusa ni un modelo Ollama real. Corrió
**64 pruebas pasadas y 2 omitidas** al cerrar el issue #4 (ver
"Pruebas opt-in" más abajo para activar las que faltan).

## Composición de la suite

| Archivo | Qué cubre |
|---|---|
| `test_aplicacion_minima.py` | Que existe un comando ejecutable mínimo de la aplicación (#2). |
| `test_caso_sembrado.py` | Que el caso de demostración (`sembrado.py`) se crea e investiga con adaptadores controlados, sin servicios externos. |
| `test_catalogo_attack.py` | Carga del catálogo ATT&CK local: versión/fecha/procedencia presentes, técnica conocida reconocida, técnica desconocida rechazada, carga desde ruta explícita y error explícito si el archivo no existe. |
| `test_contrato_investigacion.py` | El contrato completo del módulo (`crear_caso`, `investigar_caso`, `consultar_caso`, `exportar_caso`): referencias estables, fuente incompatible, caso inexistente, hallazgo válido persistido y consultable, referencia inexistente rechazada, **técnica fuera del catálogo rechazada**, un hallazgo inválido no descarta los válidos, modo degradado sin inferencia, exportación a JSON/Markdown, recorrido completo extremo a extremo. |
| `test_evtx_real.py` | Prueba de contrato opt-in: Hayabusa real + SQLite sobre un EVTX público, verificado contra un lector XML independiente (#3). |
| `test_importacion_evtx.py` | Normalización determinista de la salida de Hayabusa: timestamps, campos ausentes, agrupamiento por regla, errores de importación explícitos (#3). |
| `test_inferencia_ollama.py` | **Nuevo (#4).** Adaptador `InferenciaOllama` con transporte HTTP sustituido: sin red. |
| `test_inferencia_ollama_real.py` | **Nuevo (#4).** Prueba de contrato end-to-end opt-in contra un Ollama real. |
| `test_interfaz_streamlit.py` / `test_presentacion.py` | Smoke test del recorrido principal en Streamlit y del adaptador de presentación; la lógica de dominio no se revalida aquí. |

## Detalle de lo nuevo en el issue #4

### `test_catalogo_attack.py`

Prueba `investigacion.catalogo_attack.cargar_catalogo`, no un archivo de
datos suelto: que el catálogo por defecto (`docs/attack/catalogo.json`)
carga con versión, fecha y procedencia; que reconoce técnicas presentes
(`T1021.002`, `T1569.002`) y rechaza una inventada (`T9999`); que puede
cargarse desde una ruta arbitraria para pruebas aisladas; y que una ruta
inexistente falla con `FileNotFoundError` en vez de devolver un catálogo
vacío silencioso.

### `test_contrato_investigacion.py` — técnica fuera de catálogo

Se agregó `test_una_tecnica_fuera_del_catalogo_rechaza_el_hallazgo_y_no_lo_persiste`,
en el mismo estilo que la prueba ya existente para una referencia de evento
inexistente: una propuesta con `tecnicas_candidatas=("T9999",)` debe
rechazarse, dejar constancia del motivo en `errores` y no aparecer en
`consultar_caso`. Confirma que `ValidadorDeReferencias` ahora valida
referencias de eventos **y** técnicas ATT&CK antes de aceptar un hallazgo
(antes del issue #4 sólo validaba referencias).

Esta prueba se escribió primero, se vio fallar (el hallazgo se aceptaba sin
validar la técnica) y sólo después se implementó el chequeo en
`validacion.py` — TDD estricto, como exige el spec.

### `test_inferencia_ollama.py` (12 pruebas, sin red)

Todas inyectan un `transporte` falso — una función `(url, cuerpo, timeout) ->
dict` — en `InferenciaOllama`, en vez de abrir una conexión real. Cubren:

- una respuesta válida se convierte correctamente en `PropuestaHallazgo`;
- el modelo puede abstenerse devolviendo `"hallazgos": []`;
- un fallo de transporte (`OSError`, timeout) se traduce a
  `InferenciaNoDisponible`, el mismo error que activa el modo degradado;
- contenido que no es JSON se rechaza igual, sin intentar interpretarlo;
- cinco variantes de salida que no cumple el esquema (objeto vacío,
  `hallazgos` no es lista, falta `hipotesis`, `hipotesis` en blanco,
  `referencias_eventos` no es lista) se rechazan explícitamente — cubre el
  criterio de aceptación "la respuesta se valida contra un esquema
  estructurado antes de incorporarse al caso";
- un mensaje ausente en la respuesta del servidor también es
  `InferenciaNoDisponible`;
- la `modalidad` configurada (`NODO_PRIVADO` o `MODELO_LOCAL`) se expone tal
  cual en el puerto;
- el prompt enviado sólo contiene los `uid` de los eventos realmente
  entregados y las técnicas del catálogo inyectado — nada más — verificado
  capturando el cuerpo de la petición con un transporte espía.

Son pruebas unitarias del adaptador, no del contrato del módulo, porque
verifican una responsabilidad específica del puerto `MotorDeInferencia`
(traducir HTTP/JSON a `PropuestaHallazgo` o fallar explícitamente) que el
contrato de `ModuloDeInvestigacion` ya ejercita con dobles.

### `test_inferencia_ollama_real.py` (opt-in, 1 prueba)

Es la prueba de contrato exigida por el último criterio de aceptación del
issue #4: **con inferencia determinista, el hallazgo validado debe quedar
consultable mediante el contrato del módulo.** Construye un
`ModuloDeInvestigacion` real con `EvidenciaControlada` (el caso sembrado) y
`InferenciaOllama` apuntando a un Ollama real, temperatura 0 y semilla fija,
y ejecuta `crear_caso` → `investigar_caso` → `consultar_caso`. Comprueba que:

- la modalidad de inferencia registrada es la configurada;
- lo que devuelve `consultar_caso` es exactamente lo que devolvió
  `investigar_caso` (persistencia correcta);
- cada hallazgo aceptado cita al menos un evento existente y ninguna
  referencia inventada;
- la procedencia del mapeo y el estado de revisión son los que exige el
  dominio (`ProcedenciaMapeo.MODELO`, `EstadoRevision.PENDIENTE`);
- si el modelo se abstiene, queda un error explícito en el caso en vez de
  silencio.

Se omite automáticamente si no hay servidor Ollama disponible (variable
`OLLAMA_MODELO_PRUEBA` sin definir), para no acoplar la suite ordinaria a
infraestructura externa.

```bash
OLLAMA_MODELO_PRUEBA=qwen2.5:7b-instruct uv run pytest tests/test_inferencia_ollama_real.py
# OLLAMA_BASE_URL para apuntar a otro endpoint que no sea localhost:11434
```

Se corrió realmente contra `ollama serve` local con los dos modelos
candidatos (`llama3.2:3b` y `qwen2.5:7b-instruct`): ambos pasaron.

## Pruebas opt-in y por qué no corren siempre

| Prueba | Requiere | Por qué es opt-in |
|---|---|---|
| `test_evtx_real.py` | `HAYABUSA_BIN` + fixture público descargado | Depende de un binario externo (Hayabusa 4.1.0) y de un archivo que no se distribuye en el repo. |
| `test_inferencia_ollama_real.py` | `OLLAMA_MODELO_PRUEBA` + `ollama serve` corriendo | Depende de un modelo cargado en memoria; su latencia y disponibilidad no deben condicionar `uv run pytest` en cualquier máquina o CI sin GPU/modelo. |

Ambas siguen el mismo patrón: `@pytest.mark.skipif` sobre una variable de
entorno, documentado en `docs/evidencia.md` y `docs/inferencia.md`
respectivamente.

## Lo que NO son pruebas de pytest: el benchmark de modelos

`scripts/benchmark_modelos.py` **no es parte de la suite** (spec #1: "Los
benchmarks... se ejecutarán como evaluación reproducible separada"; "una
medición inestable" no debe convertirse "en una prueba unitaria"). Corre
cada modelo candidato varias veces sobre el caso sembrado y mide latencia,
cumplimiento de esquema, referencias resolubles y técnicas dentro del
catálogo, guardando el resultado en `docs/benchmarks/resultados-modelos.{json,md}`.
Esa medición es la que sustenta la elección de modelo documentada en
`docs/adr/0014-eleccion-modelo-local-ollama.md`, no una aserción de test.

```bash
uv run python scripts/benchmark_modelos.py --modelos llama3.2:3b qwen2.5:7b-instruct --repeticiones 3
```

## Qué queda sin probar

- **Manipulación de contenido** (texto insertado en un campo tratado como
  dato no confiable) y **evidencia insuficiente** (retirar un evento
  relevante) — escenarios C y D del spec #1 — todavía no tienen una prueba
  automatizada contra `InferenciaOllama`; el prompt lo instruye
  explícitamente, pero eso no está verificado con un caso de prueba.
- El benchmark corrió con aceleración GPU disponible; el piso de aceptación
  en CPU pura (la notebook de presentación) sigue sin medirse — documentado
  como limitación abierta en ADR-0014.
- No hay prueba que confirme el comportamiento cuando el nodo privado
  (`ModalidadInferencia.NODO_PRIVADO`) falla y debería recaer en el modelo
  local reducido; hoy `InferenciaOllama` es un único motor por instancia, y
  la composición de fallback entre dos instancias es responsabilidad de
  quien construya `ModuloDeInvestigacion`, sin cobertura propia todavía.
