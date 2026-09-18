# Cobertura y números para la defensa del pitch

Material de apoyo para responder la consigna del mentor: por qué EVTX, por
qué la cobertura, y números concretos de lo que el motor detecta. Todos los
conteos son numeradores/denominadores medidos sobre el release fijado, no
porcentajes de confianza (ADR-0006).

## 1. Por qué EVTX

EVTX es el formato nativo de registros de Windows: la evidencia llega como
un archivo exportado, sin instalar agentes ni tocar el sistema origen otra
vez. Encaja con la restricción del desafío —ejecución en infraestructura
propia, sin enviar datos a servicios externos— porque el archivo entra
completo al pipeline local y se conserva con hash SHA-256 y procedencia
registrada.

Cada canal aporta observables distintos:

| Canal | Qué registra (observables) | Qué permite reconstruir |
|---|---|---|
| Security | creación de procesos con línea de comando (4688), inicios de sesión (4624/4625), uso de privilegios, acceso a recursos compartidos (5140/5145), borrado del registro (1102) | quién ejecutó qué, desde dónde, y si alguien intentó limpiar rastros |
| System | instalación de servicios (7045), cambios de estado del sistema | persistencia y ejecución remota tipo PsExec —es el canal donde cayó toda la detección del caso de la demo |
| Sysmon (si está desplegado) | proceso con hash y firma (1), conexiones de red (3), carga de imágenes (7), acceso entre procesos (10), archivos (11), registro (12–14), named pipes (17–18), WMI (19–21), DNS (22) | trazabilidad fina del comportamiento, no solo el hecho administrativo |
| PowerShell | script blocks y ejecución (400/403/4103/4104) | el contenido interpretado, no solo el proceso lanzado |

Por qué es buena fuente post-incidente: Security y System vienen habilitados
de fábrica en cualquier Windows, Sysmon es un despliegue común, y cada evento
trae timestamp, RecordID y campos estructurados que permiten citar el
registro original — la cronología derivada nunca reemplaza a la evidencia
(ADR-0002). El EVTX de la demo es público y está fijado por commit y SHA-256
(`tests/fixtures/publico/manifest.json`): cualquiera puede repetir la
medición sobre el mismo archivo.

## 2. Números Sigma del release fijado

Conteo sobre `~/tools/hayabusa-4.1.0/rules/` (archivos `.yml`, una regla por
archivo):

| Segmento | Reglas |
|---|---|
| Total | 4984 |
| `sigma/` (reglas Sigma convertidas) | 4790 — builtin 2396, sysmon 2394 |
| `hayabusa/` (reglas propias del motor) | 194 — builtin 138, sysmon 56 |
| Con al menos un tag `attack.t*` | 4287/4984 |
| Activas (sin `deprecated`, `unsupported`, `placeholder`) | 4680/4984 |

Distribución por severidad: critical 234, high 2361, medium 1917, low 353,
informational 119.

Distribución por canal principal (campo `Channel`): Sysmon/Operational 2450,
Security 1998, System ~99, Windows PowerShell ~21, más Application, Defender,
TaskScheduler, WMI-Activity, BITS, WinRM y otros canales operativos. Las
categorías más pobladas son creación de procesos (~2300 reglas entre builtin
y sysmon), registro (~484), PowerShell (209 en builtin), eventos de archivo
(180) y carga de imágenes (100). 1473 reglas operan sobre los EventID
centrales del escenario (4688/7045/1102).

Cobertura ATT&CK de los tags declarados en las reglas:

- 334 identificadores distintos: 137 técnicas base + 197 sub-técnicas.
- Colapsando sub-técnicas a su técnica madre: 156 técnicas base alcanzadas.
- Contra ATT&CK Enterprise v15 (202 técnicas, 435 sub-técnicas): 156/202
  técnicas base con al menos una regla, 197/435 sub-técnicas.

Aclaración honesta: que exista una regla con tag `tXXXX` no implica detección
en un entorno dado — depende de políticas de auditoría, versión de Windows y
ruido. Y el catálogo ATT&CK que el validador acepta es un subconjunto local
fijado de 30 técnicas (v15.1): las que el escenario del MVP y los casos de la
galería realmente producen (ADR-0014). Las reglas traen cobertura amplia, la
validación es deliberada y acotada.

En el caso de la demo, Hayabusa registró 12 correspondencias regla–evento,
todas en canal System (instalaciones de servicio sospechosas y borrado de
log), con mapeos heredados a T1134.001, T1134.002, T1543.003, T1569.002,
T1021.002 y T1070.001; la importación llevó 9.841 s.

## 3. Qué detecta y qué no (medido)

Contra la misma verdad de referencia separada del input
(`docs/evaluacion/resultados-enfoques.md`, `resultados-escenarios.md`):

| Caso | Hayabusa solo | LLM directo | Pipeline completo |
|---|---|---|---|
| A, sospechoso público | evidencia 3/3, técnicas heredadas 5/6, sin hipótesis revisables | aciertos 6/6, técnicas respaldadas 2/6 | aciertos 9/9, técnicas respaldadas 9/9, falsas afirmaciones 0/3 |
| B, control legítimo sintético | 0/4 — superficie vacía por construcción (nunca procesado por Hayabusa real, ADR-0015) | falsas afirmaciones 1/12, técnicas 0/9 | aciertos 12/12, técnicas 9/11, falsas afirmaciones 1/9 con 2 bloqueadas |
| D, manipulación | aciertos 2/4, omisiones 2/4 — la instrucción insertada es texto, no un patrón de regla | obedeció la instrucción 3/3 y persistió lo inventado 3/3 | modelo obedeció 0/3; sistema persistió lo inventado 0/3 |

Qué queda fuera — y es el punto del diseño:

- **Explicaciones legítimas y contexto organizacional.** PsExec, PowerShell,
  servicios y pipes aparecen tanto en el ataque como en administración
  autorizada. La regla ve el patrón técnico; la ventana de cambio, el ticket
  o la identidad del admin no están en el EVTX: ese contexto lo declara el
  operador. Por eso la salida es hipótesis revisable con explicaciones
  alternativas y evidencia faltante, no veredicto. Brecha medida: en la
  corrida del 2026-09-16, los hallazgos aceptados del caso B quedaron sin
  explicación alternativa registrada en 3/3 corridas con qwen2.5:7b (y 12/12
  con llama3.2:3b) — el enunciado de alternativas todavía depende del
  modelo, la guarda está en que no se presenta como compromiso.
- **Telemetría no registrada.** Si el canal no está habilitado, la política
  de auditoría no captura línea de comando, o el log fue rotado o borrado
  (el propio caso A incluye "Important Log File Cleared", T1070.001), la
  regla no tiene observable. El sistema declara evidencia faltante en lugar
  de compensar con afirmaciones.
- **Lo que no es un evento.** Instrucciones insertadas en campos de texto no
  disparan reglas (omisiones 2/4 de Hayabusa en D); ahí la defensa es la
  capa determinista: referencias que no resuelven y técnicas fuera del
  catálogo se bloquean — con llama3.2:3b el modelo obedeció la instrucción
  3/3 y el sistema persistió lo inventado 0/3.

## 4. Emulación adversaria (plan, no ejecutado)

Atomic Red Team queda como validación futura de cobertura: ejecutar
comportamientos ATT&CK autorizados en un laboratorio aislado, producir
telemetría Sysmon/EVTX propia y medir qué reglas disparan y qué brechas
quedan. No se ejecutó en el MVP; la formulación del plan es «integración con
emulación adversaria controlada para validar cobertura defensiva»
(ADR-0002, `PLAN_MVP_HACKATHON.md` §Extensiones posteriores). El motor Sigma
no es una capacidad ofensiva.

## 5. Versión ultra-corta para decir en voz alta

- "EVTX porque es la evidencia nativa de Windows: llega como archivo
  exportado, sin agentes, y cada afirmación se cita contra el registro
  original con hash y procedencia."
- "El release fijado trae 4984 reglas; 4287 llevan tags ATT&CK que tocan
  156 de las 202 técnicas base de Enterprise v15."
- "En el caso sospechoso, Hayabusa solo cubre la evidencia 3/3 pero no
  produce una sola hipótesis revisable; el pipeline llega a 9/9 con las 9/9
  técnicas respaldadas."
- "Ante la instrucción maliciosa insertada en un campo, el LLM directo
  obedeció y persistió lo inventado 3/3; el pipeline persistió 0/3 — la
  validación es código, no una promesa del modelo."
- "Lo que no está en el log no se inventa: se declara evidencia faltante, y
  el contexto organizacional lo aporta el operador."
