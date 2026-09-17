# Demostración de ambigüedad: PsExec, PowerShell y SMB (#8)

La demostración compara dos secuencias parecidas desde la misma interfaz. No
clasifica automáticamente un equipo como comprometido. Cada hallazgo es una
hipótesis pendiente de revisión humana, aun cuando cite una técnica ATT&CK.

## Escenarios

### A — Actividad a investigar

Usa el EVTX público real del tracer #6, fijado por
`tests/fixtures/publico/manifest.json`. Conserva el archivo original, su
SHA-256, procedencia, versiones de Hayabusa y reglas, eventos detectados y
referencias resolubles. La cronología contiene detecciones de Hayabusa, no
todos los registros del EVTX.

### B — Operación administrativa documentada

Reutiliza `eventos_control_legitimo()`: ticket CHG-4821, cuenta
`svc-patching`, instalación de PSEXESVC, PowerShell y SMB hacia un recurso
interno. Es un **control sintético/documentado**. Su hash se calcula sobre la
serialización canónica de los eventos y su origen declara
`captura: sintetica`. No se presenta como EVTX real.

El `contenido` de los eventos describe sólo lo observable: no incluye
anotaciones como "script firmado" o "recurso conocido en CMDB", porque ese
contexto de autorización revelaría la respuesta esperada al modelo
(ADR-0004). La correlación con el ticket y la cuenta de servicio queda como
trabajo del analista, igual que en el escenario A.

No había una VM Windows apropiada en este entorno para generar una captura
legítima real. Obtenerla sigue pendiente (ADR-0015); no bloquea la
demostración honesta del control actual.

## Verdad de referencia separada

La verdad de referencia vive en
`docs/evaluacion/verdad-referencia-escenarios.json`. Contiene
`escenario_id`, contexto esperado, fundamento, contexto del operador
conocido, evidencia relevante esperada y procedencia. No se carga en `Caso`,
`Evento`, SQLite ni `construir_prompt()`.

El payload de Ollama contiene únicamente:

- eventos citables;
- UID permitidos;
- subconjunto local de técnicas ATT&CK.

`tests/test_ambiguedad.py` carga la verdad de referencia e inspecciona la
solicitud capturada al modelo para
demostrar que no aparecen sus campos, identificadores ni etiquetas esperadas.
Los rótulos descriptivos de la interfaz se guardan aparte en
`datos/escenarios-comparacion.json` y tampoco llegan al modelo.

## Preparar la comparación

Primero importar e investigar el EVTX público con el comando documentado en
`docs/tracer.md`. Con el identificador devuelto:

```bash
uv run python scripts/preparar_comparacion.py \
  --datos datos \
  --caso-sospechoso ID_DEL_CASO_REAL \
  --modelo qwen2.5:7b-instruct
```

El comando verifica que el caso A exista, tenga eventos y hash, rechaza el
sembrado controlado, crea o reemplaza de forma repetible el caso B con el ID
`control-legitimo-documentado`, ejecuta la inferencia y escribe los metadatos
del selector. Si Ollama no está disponible, el caso B queda en modo degradado
sin inventar hallazgos.

Abrir ambos casos en el mismo producto:

```bash
INVESTIGACION_DATOS=datos uv run streamlit run src/investigacion/ui/app.py
```

El selector conserva los mismos componentes para ambos escenarios:
cronología, hipótesis, técnicas candidatas, estado, explicaciones alternativas,
evidencia faltante/incertidumbre, limitaciones y navegación a la evidencia.
Un campo vacío se muestra como “No declarada por el modelo” o “No
especificada”. Una abstención se muestra como ausencia de hipótesis validadas,
sin convertirla en actividad legítima ni en ataque.

## Controles contra lenguaje concluyente

El prompt declara explícitamente que PsExec, PowerShell y SMB son tecnologías
de doble uso. Pide alternativas administrativas compatibles, evidencia
faltante y limitaciones, y permite `hallazgos: []`.

`ValidadorDeReferencias` rechaza las afirmaciones concluyentes
(“comprometido/a”, “ataque confirmado”, “actividad maliciosa confirmada”,
“intrusión confirmada”, “compromiso confirmado”, “malware confirmado”) en
cualquier campo de texto libre de la propuesta, no sólo en la hipótesis. La
UI también oculta esas formulaciones si abre un caso legado que hubiera
evitado la validación. Es una lista corta de afirmaciones prohibidas, no un
clasificador: una reformulación equivalente puede evadirla, así que el estado
permanece `pendiente` y la decisión sigue siendo humana.

## Evaluación con Ollama

```bash
uv run python scripts/evaluar_escenarios.py \
  --modelos qwen2.5:7b-instruct \
  --repeticiones 3 \
  --datos datos \
  --caso-sospechoso ID_DEL_CASO_REAL
```

Por corrida y escenario registra propuestas y hallazgos aceptados, referencias
válidas, presencia/ausencia de explicaciones alternativas, evidencia faltante,
limitaciones y lenguaje concluyente. Conserva el caso D como regresión de
manipulación. Informa numeradores/denominadores, no confianza.

Ollama no estaba instalado ni escuchando en `localhost:11434` durante este
bloque, por lo que no se inventaron resultados posteriores al cambio. La
medición real anterior permanece en
`docs/evaluacion/resultados-escenarios.{json,md}`: con
`qwen2.5:7b-instruct`, el control produjo 3 hallazgos aceptados en 3 corridas
y 3/3 carecieron de explicación alternativa. Ese resultado es la línea base
que motivó el nuevo prompt y la presentación explícita de campos ausentes.

## Qué puede y qué no puede concluir

El sistema puede reconstruir eventos detectados, citar su procedencia, proponer
hipótesis ATT&CK y hacer visibles alternativas y datos faltantes. No determina
intención, autorización ni compromiso sólo por una herramienta, un puerto o
una técnica candidata. Faltan, según el caso, contexto del operador, cambios
autorizados, origen remoto, firmas, inventario, telemetría adicional y revisión
humana.
