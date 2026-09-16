# Asistente local de investigación de eventos

Documento de alineación del equipo para el Hackathon Nacional de Ciberdefensa CYBER.AR 2026.

## Estado del documento

Esta propuesta consolida las decisiones tomadas durante el refinamiento inicial. Su objetivo es que las tres personas del equipo compartan el mismo problema, alcance y criterio de éxito antes de implementar.

Las decisiones están aceptadas como base de trabajo, pero el equipo completo debe ratificarlas. Los resultados que dependen de ejecución —modelo, latencia, consumo y fixture definitivo— siguen pendientes del prototipo de viabilidad.

Documentos de origen:

- [Bases técnicas del hackathon](./Hackathon_CyberAr_2026_Desafios.pdf)
- [Investigación técnica inicial](./Investigacion_Asistente_Local_MITRE.md)
- [Glosario del dominio](./CONTEXT.md)
- [Registro de decisiones](./docs/adr/)

## Resumen ejecutivo

Construiremos un asistente para investigadores de incidentes que analice registros Windows exportados sin delegar datos o inferencia a proveedores externos. El sistema utilizará Hayabusa para procesar archivos EVTX y aplicar reglas Sigma. Sobre esa base, reconstruirá una cronología, seleccionará evidencia mediante código y utilizará un LLM privado para formular hipótesis ATT&CK estructuradas, trazables y revisables.

La propuesta no busca reemplazar al analista, construir otro SIEM ni declarar automáticamente que ocurrió un ataque. Su aporte es transformar eventos y detecciones dispersas en una investigación comprensible en español, manteniendo visible la evidencia, la incertidumbre y la procedencia de cada mapeo.

El escenario principal comparará dos actividades semejantes:

1. ejecución remota sospechosa mediante PsExec y PowerShell;
2. administración legítima realizada con herramientas similares.

Esta comparación demostrará que reconocer una herramienta o disparar una regla no basta para confirmar un compromiso.

## El problema

Un investigador recibe registros exportados y debe responder rápidamente:

- ¿Qué ocurrió y en qué orden?
- ¿Qué eventos respaldan cada conclusión?
- ¿Qué comportamientos son compatibles con técnicas ATT&CK?
- ¿Qué explicaciones legítimas siguen siendo posibles?
- ¿Qué evidencia falta para sostener una conclusión más fuerte?

Las herramientas defensivas existentes pueden detectar patrones y producir alertas, pero todavía queda trabajo humano para relacionarlas, revisar eventos vecinos, explicar la secuencia y redactar un hallazgo defendible.

La necesidad es especialmente relevante cuando la organización:

- no puede enviar evidencia sensible a servicios externos;
- opera infraestructura propia o aislada;
- tiene capacidad analítica limitada;
- necesita explicar decisiones a perfiles técnicos y no técnicos;
- requiere conservar una cadena clara entre afirmaciones y registros originales.

## Precisión conceptual

Un indicador de compromiso no es una técnica ATT&CK.

- Un **observable** es un dato registrado, como una IP, dominio o hash.
- Un **indicador de compromiso** es un observable cuyo contexto permite asociarlo razonablemente con una intrusión.
- Una **técnica ATT&CK** describe un comportamiento, no un archivo o dirección aislada.
- Una **hipótesis ATT&CK** vincula evidencia con una técnica candidata y permanece sujeta a revisión.

Por eso no presentaremos el producto como «un LLM que cataloga IOC según MITRE». La formulación acordada es:

> Un asistente privado que reconstruye actividad a partir de logs, presenta evidencia consultable y propone hipótesis ATT&CK revisables.

## Usuario primario

El usuario primario será un investigador de incidentes que recibe registros exportados y decide qué merece investigación adicional.

No construiremos inicialmente:

- una cola de triaje para un SOC completo;
- una plataforma educativa;
- un operador autónomo de respuesta;
- un reemplazo de Wazuh u otro SIEM.

Esos usos pueden aparecer como evolución, pero no compiten por el foco del MVP.

## Propuesta de valor

> Convertir evidencia Windows exportada en una investigación trazable y comprensible, ejecutando la IA en infraestructura administrada por la organización y manteniendo la decisión final en manos humanas.

La promesa defendible es **asistencia trazable**, no detección universal, atribución de atacantes ni certeza automática de compromiso.

## Decisiones principales

| Decisión | Elección | Justificación | Alternativa descartada |
|---|---|---|---|
| Usuario | Investigador de incidentes | Encaja con archivos exportados y evita depender de un SIEM en vivo | SOC L1 o alumno como usuario primario |
| Forma del producto | Caso de investigación | Hace visibles cronología, evidencia, incertidumbre y revisión | Chat libre como interfaz principal |
| Motor defensivo | Hayabusa | Procesa EVTX, aplica reglas y produce cronologías estructuradas sin desplegar un SIEM completo | Wazuh como dependencia obligatoria del MVP |
| Responsabilidad del LLM | Explicar y proponer hipótesis sobre evidencia seleccionada | Conserva hechos y referencias verificables fuera de la inferencia | Entregar logs crudos al modelo |
| Escenario | PsExec/PowerShell sospechoso frente a administración legítima | Obliga a considerar el uso dual y evita una clasificación trivial | Muestra inequívoca de malware sin control comparable |
| Interfaz | Cronología, hallazgos y evidencia navegable | Demuestra el valor mejor que una conversación genérica | Grafo o dashboard SOC como centro del producto |
| Stack | Python, Streamlit y SQLite | Reduce integración y despliegue sin impedir módulos testeables | Frontend React y backend separado |
| Inferencia | Ollama privado con remoto preferido, fallback local y modo degradado | Aprovecha GPU institucional sin convertir Internet en fallo fatal | API pública o dependencia exclusiva del nodo remoto |
| Evaluación | Comparar Hayabusa, LLM directo y pipeline propuesto | Aísla el aporte real del sistema | Declarar precisión con pocos casos |
| Adopción inicial | Estación forense portátil | Requiere pocos cambios en infraestructura existente | Reemplazar el SIEM o desplegar agentes masivamente |
| Integración MCP | Adaptador P1 sobre el módulo de investigación | Permite integración futura sin entregar el producto a un host externo | MCP como reemplazo de Streamlit o núcleo del MVP |

## Arquitectura propuesta

```text
Archivo EVTX
    │
    ▼
Importación
- conserva original
- calcula hash
- registra procedencia
    │
    ▼
Hayabusa + reglas Sigma
- parsea eventos Windows
- genera cronología JSONL
- aporta detecciones y mapeos heredados
    │
    ▼
Normalización determinista
- asigna event_uid
- ordena timestamps
- conserva RecordID y archivo fuente
- agrupa por host, usuario, proceso y ventana temporal
    │
    ▼
Selección de evidencia
- elige eventos relevantes y contexto vecino
- limita tamaño y contenido del prompt
    │
    ▼
Ollama privado
- nodo remoto administrado por la institución, o
- modelo local reducido
- salida restringida por esquema JSON
    │
    ▼
Validación
- referencias existentes
- técnicas presentes en el catálogo fijado
- procedencia del mapeo
- campos y estados permitidos
    │
    ▼
Caso de investigación
- cronología
- hallazgos
- alternativas
- evidencia faltante
- revisión humana
- exportación
```

## Frontera entre código e IA

El código será responsable de:

- identidad, hash y procedencia de archivos;
- parsing y normalización;
- orden temporal;
- conteos y agrupamientos;
- selección inicial de evidencia;
- consulta del catálogo ATT&CK;
- validación de referencias y esquema;
- persistencia y exportación.

El LLM será responsable de:

- explicar una secuencia en español;
- formular hipótesis limitadas por la evidencia;
- proponer técnicas ATT&CK candidatas;
- presentar explicaciones alternativas;
- señalar evidencia faltante;
- abstenerse cuando el contexto no alcance.

El LLM no tendrá herramientas de shell, red, modificación de archivos ni respuesta automática sobre endpoints.

## Procedencia de los mapeos ATT&CK

La interfaz diferenciará, como mínimo:

- **mapeo heredado de regla:** viene de Hayabusa/Sigma;
- **sugerencia del modelo:** fue propuesta por el LLM;
- **técnica validada:** el identificador existe en la versión local del catálogo;
- **estado de revisión:** aceptada, rechazada o pendiente por un humano.

Validar que `Txxxx` existe no demuestra que la técnica esté correctamente aplicada. Esa pertinencia debe comprobarse mediante evidencia y revisión.

## Escenarios de evaluación

### Caso A — Actividad sospechosa controlada

Usaremos evidencia pública de una ejecución remota con PsExec y PowerShell. El fixture definitivo se elegirá después de comprobar que timestamps, hosts, usuarios y eventos permiten reconstruir una secuencia coherente.

### Caso B — Control legítimo

Generaremos en una VM aislada una operación administrativa autorizada que produzca telemetría semejante. El resultado esperado no es «sin alertas», sino una investigación que reconozca la actividad y evite declarar compromiso sin evidencia suficiente.

### Caso C — Evidencia insuficiente

Retiraremos un evento o campo relevante. El sistema deberá reducir la fuerza de su conclusión e indicar qué información falta.

### Caso D — Manipulación

Incluiremos una instrucción dentro de un campo tratado como dato no confiable. El sistema deberá conservarla como evidencia sin obedecerla ni alterar sus reglas.

### Caso E — Fallo técnico

Probaremos una salida inválida, referencia inexistente o técnica fuera del catálogo. El validador deberá rechazar el hallazgo y conservar accesible la cronología.

La verdad de referencia permanecerá separada del input. Los nombres de archivo, prompts y metadatos entregados al modelo no revelarán la técnica o resultado esperado.

## Qué se mostrará en la demo

La presentación dispondrá de tres minutos para pitch y demostración. El recorrido propuesto es:

1. explicar el problema concreto;
2. abrir un caso previamente procesado por Hayabusa;
3. iniciar una inferencia real con el modelo ya cargado;
4. navegar la cronología mientras se genera el resultado;
5. mostrar una hipótesis y abrir los eventos que la respaldan;
6. contrastar brevemente el control legítimo o evidencia insuficiente;
7. cerrar con ejecución privada, límites y evolución.

Se conservará una ejecución anterior como contingencia, claramente identificada como respaldo y no como resultado generado en vivo.

## Modos de inferencia

### 1. Nodo privado preferido

Un servidor administrado por el equipo o la institución ejecutará un modelo de mayor capacidad. La conexión será cifrada y Ollama no se expondrá directamente a Internet.

Solo se enviará evidencia seleccionada, no el archivo EVTX completo. Cada ejecución registrará modelo, modalidad, versión, latencia y hash del contexto.

La interpretación de «infraestructura propia» debe confirmarse con la organización antes de usar este modo como argumento de cumplimiento.

### 2. Fallback local

La notebook de presentación conservará un modelo cuantizado reducido capaz de producir inferencia real. Su calidad y latencia deben medirse durante el prototipo; no se fijará un modelo por reputación o tamaño nominal.

### 3. Modo degradado

Si no hay inferencia disponible, la aplicación continuará ofreciendo:

- importación y consulta de casos;
- cronología;
- detecciones Hayabusa;
- evidencia navegable;
- resultados anteriores identificados correctamente.

No presentará este modo como una inferencia nueva ni esconderá la ausencia del modelo.

## Criterio de éxito

No afirmaremos «alta precisión» a partir de dos escenarios. El objetivo es demostrar que el pipeline produce una investigación más trazable y segura que entregar eventos directamente a un LLM.

Compararemos:

1. Hayabusa sin LLM;
2. LLM directo sobre eventos;
3. pipeline propuesto.

Medidas mínimas:

- eventos esenciales recuperados / esperados;
- referencias resolubles / referencias generadas;
- afirmaciones respaldadas / afirmaciones revisadas;
- técnicas respaldadas / técnicas sugeridas;
- falsos veredictos de compromiso en el control legítimo;
- resultado de cada ensayo de manipulación;
- latencia de inferencia;
- memoria utilizada;
- éxito o rechazo del esquema.

Los resultados se informarán como numeradores y denominadores, no como porcentajes de confianza inventados.

## Alcance P0

El MVP debe:

- importar un caso EVTX y conservar original, hash y procedencia;
- ejecutar Hayabusa o reproducir su JSONL de manera documentada;
- normalizar eventos con referencias estables;
- mostrar una cronología navegable;
- seleccionar evidencia mediante código;
- ejecutar un LLM privado con salida estructurada;
- validar referencias y técnicas;
- presentar hallazgos, alternativas y evidencia faltante;
- abrir el evento que respalda cada afirmación;
- analizar el escenario sospechoso y el control legítimo;
- ensayar salida inválida y manipulación;
- exportar un informe Markdown o JSON;
- conservar utilidad cuando la inferencia falla.

## Fuera del camino crítico

No se implementará antes de completar y verificar el P0:

- integración en vivo con Wazuh;
- ejecución de Atomic Red Team;
- chat de seguimiento;
- grafos interactivos;
- búsqueda vectorial;
- múltiples modelos o agentes;
- múltiples formatos de logs;
- usuarios, roles y autenticación;
- actualización automática de reglas o ATT&CK;
- dashboard general de SOC;
- adaptador MCP.

## Extensiones posteriores

### Integración con Wazuh

Wazuh puede aportar recolección continua, reglas, alertas e indexación. Una integración futura convertiría señales operativas en casos investigables sin instalar toda la plataforma como parte del producto.

### Validación purple-team

Atomic Red Team podría ejecutar comportamientos controlados en un laboratorio aislado. Sysmon produciría telemetría, Hayabusa evaluaría reglas y el asistente explicaría cobertura y brechas.

El motor Sigma no es una capacidad ofensiva. La formulación correcta es «integración con emulación adversaria controlada para validar cobertura defensiva».

### Capacitación

Los mismos casos y verdades de referencia podrían utilizarse para entrenar investigadores. La educación es una posibilidad de adopción, no el objetivo primario del MVP.

### Adaptador MCP

Una vez verificado el P0, un servidor MCP podrá publicar casos y capacidades del módulo de investigación para asistentes institucionales autorizados. MCP no reemplazará Streamlit, el modelo ni la visualización: será otro adaptador sobre las mismas interfaces internas.

La superficie inicial se limitará a consultar resúmenes, cronologías, eventos y hallazgos, además de solicitar análisis o exportación por `case_id`. No aceptará rutas arbitrarias, shell, SQL, ejecución ofensiva ni lectura irrestricta de archivos. Para uso local se preferirá `stdio`; un despliegue HTTP requerirá transporte cifrado y autorización.

## Reparto sugerido

### Evidencia

- fixture y procedencia;
- Hayabusa;
- parsing y normalización;
- identidad de eventos;
- cronología.

### Inferencia confiable

- benchmark de modelos;
- esquema de salida;
- selección de contexto;
- prompts;
- validación ATT&CK;
- manipulación y fallos.

### Producto y evaluación

- interfaz Streamlit;
- navegación de evidencia;
- verdad de referencia;
- comparación de modalidades;
- exportación, README y pitch.

El ownership no crea silos: las tres personas deben integrar el recorrido completo durante el primer día.

## Plan de 48 horas

| Tiempo | Resultado obligatorio |
|---|---|
| 0–2 h | Hayabusa procesa un fixture y se miden al menos dos modelos locales |
| 2–8 h | Primer recorrido completo: EVTX → hallazgo → evidencia |
| 8–18 h | Casos, cronología, validadores e interfaz principal |
| 18–28 h | Caso sospechoso, control legítimo e informe |
| 28–34 h | Comparación de modalidades y ensayo de manipulación |
| 34–36 h | Correcciones y mediciones finales |
| 36 h | Congelamiento de funciones |
| 36–42 h | Instalación reproducible, README y resultados |
| 42–48 h | Ensayo, contingencias y descanso por turnos |

La primera integración completa debe existir antes de la hora 8, aunque todavía sea visualmente pobre.

## Criterios de recorte y pivot

- Si ningún modelo local cumple el esquema con latencia útil, se reduce contexto, salida y cantidad de hallazgos.
- Si el fixture público no contiene una secuencia coherente, se cambia o genera uno controlado; no se inventan relaciones.
- Si Hayabusa ya aporta un mapeo, se muestra como heredado.
- Si la interfaz se atrasa, se elimina personalización visual antes que trazabilidad.
- Si el pipeline no mejora al LLM directo, se reduce la promesa a aquello que sí demuestran los resultados.
- Si el control legítimo recibe un veredicto fuerte, se corrige el pipeline o se declara el límite.
- Si una función P1 amenaza el recorrido principal, se elimina.

## Riesgos principales

| Riesgo | Impacto | Mitigación |
|---|---|---|
| EVTX públicos sin una secuencia coherente | La correlación sería artificial | Verificar fixture en las primeras dos horas |
| Inferencia local lenta | Demo detenida o dependencia remota | Modelo reducido, contexto corto y precarga |
| Caída de Internet | Nodo remoto inaccesible | Fallback local y modo degradado |
| Hallazgos inventados | Pérdida de confianza | Esquema, referencias, catálogo y rechazo explícito |
| Prompt injection en logs | Manipulación de la interpretación | Delimitación de datos, capacidades restringidas y ensayo específico |
| Alcance creciente | MVP incompleto | P0/P1 y congelamiento en la hora 36 |
| Wazuh/Hayabusa opacan el aporte | Jurado no identifica innovación | Comparación de modalidades y procedencia visible |
| Interpretación de infraestructura propia | Objeción de cumplimiento | Confirmación previa con la organización |

## Preguntas que resolverá el prototipo

Estas preguntas requieren ejecución y no deben decidirse por intuición:

1. ¿Qué fixture ofrece una secuencia PsExec/PowerShell coherente?
2. ¿Qué modelo local cumple mejor esquema, citas y abstención?
3. ¿Cuál es la latencia con modelo frío y caliente?
4. ¿Cuánta memoria consume junto con Streamlit y Hayabusa?
5. ¿Qué mejora realmente el nodo remoto?
6. ¿Qué cantidad de evidencia cabe sin degradar latencia ni precisión?
7. ¿El caso legítimo evita una conclusión fuerte de compromiso?
8. ¿El pipeline rechaza referencias o técnicas inventadas?

## Fuentes técnicas principales

- [Hayabusa](https://github.com/Yamato-Security/hayabusa)
- [Muestras EVTX de Hayabusa](https://github.com/Yamato-Security/hayabusa-sample-evtx)
- [Reglas de Hayabusa](https://github.com/Yamato-Security/hayabusa-rules)
- [Sigma](https://sigmahq.io/docs/guide/about)
- [Datos oficiales de MITRE ATT&CK](https://attack.mitre.org/resources/attack-data-and-tools/)
- [Arquitectura de Wazuh](https://documentation.wazuh.com/current/getting-started/architecture.html)
- [Salidas estructuradas de Ollama](https://docs.ollama.com/capabilities/structured-outputs)
- [Configuración local de Ollama](https://docs.ollama.com/faq)
- [Caché de Streamlit](https://docs.streamlit.io/develop/concepts/architecture/caching)
- [Atomic Red Team](https://www.atomicredteam.io/docs/atomic-red-team/faq)

## Acuerdo del equipo

Antes de iniciar la implementación, cada integrante debería poder responder afirmativamente:

- Entiendo quién es el usuario primario.
- Entiendo qué hace Hayabusa y qué aporta nuestro producto.
- Entiendo qué decisiones corresponden al código y cuáles al LLM.
- Entiendo que una técnica ATT&CK candidata no es un veredicto.
- Entiendo qué pertenece al P0 y qué queda fuera.
- Acepto el recorrido completo antes de la hora 8 y el congelamiento en la hora 36.
- Acepto que los resultados medidos pueden obligarnos a recortar o reformular la promesa.

Si alguna respuesta es negativa, esa diferencia debe resolverse antes de comenzar el desarrollo.
