# Asistente local de investigación de eventos + MITRE ATT&CK

Investigación técnica para el equipo CYBER.AR — 16 de septiembre de 2026.

**Decisión propuesta.** Construir un asistente local que reciba una fuente de logs, reconstruya una línea temporal y presente explicaciones en español con evidencia consultable y técnicas ATT&CK candidatas. La viabilidad es condicional a una prueba temprana con el hardware y los datos disponibles. La propuesta pertenece al eje 2 de las bases aportadas por el equipo.

Este informe revisa documentación y repositorios públicos. No representa un benchmark ejecutado, una auditoría de productos ni una implementación terminada. Las capacidades atribuidas a terceros tienen fuentes; las decisiones de arquitectura, límites y tiempos son propuestas propias para este MVP. Las condiciones del concurso se toman del texto suministrado, sin verificación independiente de modificaciones posteriores.

**Problema y alcance.** Un analista necesita reconstruir actividad y entender por qué algo merece investigación. El producto debe reducir el trabajo de ordenar registros, vincular observaciones y redactar hallazgos, conservando la posibilidad de revisar cada afirmación. Usuario inicial: un técnico que investiga eventos de una instalación ficticia. Entrada: archivos públicos o simulados. Salida: cronología, hechos, hipótesis, alternativas legítimas, técnicas candidatas y evidencia faltante. Toda decisión operativa permanece en manos humanas.

La promesa defendible es asistencia trazable. No se puede prometer detección universal, atribución de atacantes ni certeza de compromiso por encontrar una herramienta administrativa. La ausencia de alertas tampoco demuestra ausencia de ataque.

**Productos y proyectos en los que basarse.** La columna de uso recomendado expresa nuestro criterio de integración para 48 horas.

| Referencia | Capacidad documentada | Qué aprovechar | Decisión para el MVP |
|---|---|---|---|
| [Hayabusa](https://github.com/Yamato-Security/hayabusa) | Procesamiento de eventos Windows, detección basada en Sigma y exportación de cronologías CSV/JSON/JSONL. | Parser y reglas existentes; salida estructurada para nuestro asistente. | Primera opción si hay EVTX. Conservar acceso a registros originales y al contexto que no dispara alertas. |
| [Wazuh](https://documentation.wazuh.com/current/user-manual/ruleset/mitre.html) | Asociación de reglas y alertas con identificadores ATT&CK. | Importar alertas ya disponibles y conservar su regla de origen. | Si el entorno ya lo incluye, reutilizar su exportación. Instalar toda la plataforma aumenta el alcance. |
| [Timesketch](https://timesketch.org/) | Análisis forense colaborativo de líneas temporales. | Diseño de navegación temporal, anotaciones y revisión de eventos. | Referencia de experiencia de investigación; integración futura. |
| [DFIR-IRIS](https://docs.dfir-iris.org/2.4.5/) | Plataforma colaborativa para compartir investigaciones técnicas, instalable en servidor o portátil. | Organización por caso y revisión por analistas. | Referencia para evolución del producto, sin dependencia inicial. |
| [Elastic Attack Discovery](https://www.elastic.co/docs/solutions/security/ai/attack-discovery) | Genera descubrimientos con resumen, alertas relacionadas, entidades y correspondencias ATT&CK mediante un LLM. | Presentación de hallazgos que enlazan sus alertas y entidades. | Antecedente cercano: investigar alertas con IA ya existe. No sostener una reivindicación de novedad general. |
| [Atomic Red Team](https://www.atomicredteam.io/docs/atomic-red-team) | Biblioteca de pruebas de controles de seguridad. | Generación controlada de uno o dos casos de laboratorio. | Opcional y separada de la aplicación investigadora. |

Elastic también documentó una configuración de AI Assistant con Llama ejecutado localmente mediante LM Studio. Es evidencia de que la ejecución local tampoco es exclusiva de nuestra idea; ese artículo no certifica compatibilidad de toda versión actual, gratuidad de todas las funciones ni cumplimiento automático de las bases. [Artículo técnico de Elastic](https://www.elastic.co/blog/herding-llama-3-1-with-elastic-and-lm-studio).

La oportunidad del equipo es una combinación demostrada y acotada: despliegue sencillo en infraestructura propia, español, evidencia accesible, incertidumbre explícita y evaluación de manipulación mediante logs. Su ventaja frente a una instalación existente debe medirse; no está demostrada por este análisis documental.

**Qué construir y qué reutilizar.** Construir el contrato de evidencia, normalización mínima, selección de contexto, validaciones, pantalla de revisión y evaluación. Reutilizar un motor de inferencia, el catálogo ATT&CK y, cuando corresponda, un procesador de logs. Evitar entrenar un modelo, implementar un SIEM o incorporar un framework de agentes como requisito inicial.

Sigma describe reglas con condiciones y fuentes de registros; no convierte automáticamente cualquier archivo en detecciones. Una regla solo tiene sentido si existen los campos y la telemetría que presupone. Usar un motor compatible o declarar reglas propias acotadas, sin afirmar compatibilidad completa con Sigma. [Documentación de Sigma](https://sigmahq.io/docs/basics/rules.html).

**Arquitectura recomendada.**

1. Importar archivo con límite explícito; guardar original, hash SHA-256 y procedencia.
2. Parsear y normalizar sin sobrescribir el original. Conservar referencia inequívoca al registro fuente.
3. Ordenar, contar y agrupar mediante código por equipo, usuario, proceso y ventana temporal. Una relación temporal por sí sola no demuestra causalidad.
4. Seleccionar un conjunto limitado de eventos y candidatos ATT&CK con reglas transparentes. Permitir consultar el resto del archivo.
5. Proporcionar al modelo local observaciones, evidencia contextual y definiciones del catálogo. Solicitar respuesta estructurada.
6. Validar esquema, referencias y pertenencia de técnicas al catálogo. Construir la pantalla a partir de objetos validados.
7. Mostrar hechos calculados, interpretación pendiente de revisión, hipótesis alternativas y límites. Exportar informe y metadatos de ejecución.

Stack propuesto: Python, SQLite, una interfaz local sencilla —por ejemplo Streamlit— y Ollama o llama.cpp. Es una elección de implementación para reducir integración, no un requisito del concurso. Mantener un solo servicio de inferencia y una solicitud simultánea durante la demo. No hace falta una base vectorial para un subconjunto pequeño y explícito de ATT&CK.

El registro normalizado debería incluir: case_id, event_uid interno, hash del archivo, localizador original, timestamp original, timestamp UTC si es resoluble, host, usuario, tipo de evento, proceso/padre cuando existan y contenido original. Diferenciar el ID del tipo de evento del identificador único de esa ocurrencia. Conservar nulos cuando faltan datos. Si falta zona horaria, declararlo y pedir una configuración documentada; no inventarla.

El hallazgo debería incluir: texto de la hipótesis, event_uids, campos citados, técnica candidata o valor nulo, razón del vínculo, alternativas, evidencia faltante y estado de revisión humana. Para hechos centrales, generar frases desde campos verificados; para interpretaciones libres, mantener la etiqueta de hipótesis.

**MITRE: uso correcto.** MITRE distribuye ATT&CK en STIX, procesable como JSON, y ofrece herramientas de consulta. Se puede preparar una copia local de una versión determinada y extraer las técnicas relevantes. Registrar versión, fecha, procedencia e integridad de esa copia; filtrar objetos revocados o deprecados según el alcance declarado. [Datos oficiales ATT&CK](https://attack.mitre.org/resources/attack-data-and-tools/).

Propuesta inicial: 5–10 técnicas relacionadas con los casos elegidos. No presentar ese subconjunto como cobertura de toda la matriz. Un IOC —por ejemplo una IP o hash— no acredita automáticamente un comportamiento ATT&CK. Extraer una dirección de un registro tampoco la convierte en maliciosa. Separar observables, coincidencias con listas locales y conductas inferidas.

Si una regla importada ya tiene un mapeo ATT&CK, mostrar «mapeo heredado de la regla» y su versión. Si lo propone el modelo, mostrar «sugerencia del modelo». Esto evita presentar como descubrimiento propio una etiqueta incluida en la entrada.

**Requisitos y criterios de aceptación.** P0: imprescindibles para la demo. P1: ampliaciones una vez que el recorrido completo funciona. Son criterios propuestos, no resultados obtenidos ni métricas impuestas por el jurado.

| ID | Prioridad | Requisito | Cómo comprobarlo |
|---|---|---|---|
| R01 | P0 | Una fuente y formato documentados. | Importar el fixture válido y rechazar el incompatible con explicación. |
| R02 | P0 | Preservar origen y trazabilidad. | Cada evento visible permite abrir su registro original; hash antes/después idéntico. El hash no prueba autenticidad previa a la carga. |
| R03 | P0 | Cronología determinista. | Fechas válidas ordenadas; zona horaria visible; empates y fechas inválidas tratados explícitamente. |
| R04 | P0 | Hechos separados de hipótesis. | Conteos y fechas salen de código; inferencias aparecen rotuladas y revisables. |
| R05 | P0 | Referencias existentes y pertinentes. | Todas las referencias resuelven; revisión humana comprueba si respaldan la afirmación. Son dos controles diferentes. |
| R06 | P0 | Técnicas restringidas al catálogo fijado. | ID inexistente o fuera de alcance rechazado; nombre recuperado del catálogo. |
| R07 | P0 | Abstención y explicación de límites. | Caso sin telemetría suficiente produce «no concluyente» y explica qué falta. |
| R08 | P0 | Ejecución local sin envío externo de datos. | Arrancar con recursos descargados, bloquear salida de red y completar análisis; observar conexiones del proceso. |
| R09 | P0 | Logs tratados como datos no confiables. | Instrucciones insertadas no cambian reglas, evidencia ni acciones disponibles en los casos ensayados. |
| R10 | P0 | Ausencia de respuesta automática. | Modelo sin herramientas de shell, red, modificación de archivos o ejecución de pruebas. |
| R11 | P0 | Límites y fallos explícitos. | Archivo excesivo, salida inválida, timeout y modelo ausente no causan una conclusión inventada. |
| R12 | P0 | Resumen en español e informe exportable. | Exportación conserva evidencia, limitaciones, versiones y estado de revisión. |
| R13 | P0 | Instalación reproducible. | README permite arrancar con versiones, modelo, configuración y fixtures fijados. |
| R14 | P1 | Revisión persistente. | Analista acepta/rechaza hipótesis y conserva autoría y motivo. |
| R15 | P1 | Importación adicional e integración. | Un segundo adaptador pasa los mismos controles sin cambiar semántica de evidencia. |

No mostrar porcentajes de confianza inventados por el modelo. Si se usa una escala de respaldo, definirla por criterios explícitos y dejar claro que no es una probabilidad calibrada de ataque.

**Inferencia local y hardware.** Ollama admite salidas restringidas por esquema JSON y dispone de configuración para desactivar funciones cloud. Usar modelo descargado, conexión local y modo sin cloud; luego comprobar el comportamiento sin salida a Internet. JSON válido permite automatizar validaciones, pero no garantiza verdad semántica. [Salidas estructuradas](https://docs.ollama.com/capabilities/structured-outputs), [configuración y privacidad local](https://docs.ollama.com/faq).

[llama.cpp](https://github.com/ggml-org/llama.cpp) es una alternativa que admite cuantización e inferencia sobre distintos tipos de hardware, incluida combinación CPU/GPU. Elegir uno de los dos motores y fijar su versión; integrar ambos en 48 horas no aporta al objetivo central.

Un candidato para la prueba inicial es [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507), documentado como modelo de instrucciones sin modo de pensamiento, con capacidades multilingües. No se lo selecciona como «el mejor» ni como especialista forense. Verificar calidad en español, seguimiento del esquema y respaldo de conclusiones con nuestros casos. Confirmar procedencia, licencia y compatibilidad de la cuantización elegida.

| Recursos disponibles | Decisión exploratoria, pendiente de medir |
|---|---|
| Aproximadamente 8 GB RAM libres, CPU | Probar modelo pequeño cuantizado, contexto corto y un solo caso. La latencia puede ser inadecuada. |
| Aproximadamente 16 GB RAM disponibles | Punto de partida más cómodo para un modelo de alrededor de 4B cuantizado y la aplicación mínima. No garantiza velocidad. |
| GPU accesible con memoria suficiente | Verificar aceleración real desde la VM; la GPU del host puede no estar expuesta. |

Estas cifras son presupuestos orientativos de ingeniería. Como cálculo de orden de magnitud, 4 mil millones de parámetros a 4 bits equivalen a unos 2 GB solo en pesos, antes de metadatos, caché de contexto, buffers, runtime y sistema operativo. El archivo y la memoria reales serán mayores y dependen de la variante. No confundir tamaño de descarga con RAM necesaria. Reservar disco para modelos, dependencias y registros, medido según los artefactos seleccionados.

Prueba de viabilidad en las primeras dos horas: cargar un caso pequeño; obtener JSON en español; abrir citas; medir carga en frío, inferencia en caliente, RAM/VRAM y errores; repetir sin acceso externo. Meta provisional para la demo: análisis en caliente de hasta 30 segundos para un conjunto pequeño de contexto. Si no se logra, reducir contexto/salida o probar un modelo menor. No prometer ese tiempo antes de medirlo. Mantener cronología utilizable cuando falle la IA, declarando que ese modo degradado no demuestra la parte de IA.

**Datos y telemetría.** Elegir ruta por evidencia disponible:

| Disponibilidad | Ruta propuesta | Límite |
|---|---|---|
| EVTX o Sysmon de Windows | Hayabusa para preprocesar más conservación de originales y eventos vecinos. | Su cronología de detecciones puede omitir actividad no alertada; no confundirla con todo lo sucedido. |
| Alertas Wazuh ya preparadas | Importador de su exportación estructurada. | Una alerta resume una regla; conservar el evento fuente cuando esté disponible. |
| Linux sin colector preparado | Un formato concreto de autenticación o audit, o fixtures sintéticos equivalentes. | Logs de autenticación no permiten reconstruir todas las acciones de procesos. |
| Sin datos utilizables | Dataset público pequeño o fixtures simulados con procedencia explícita. | No presentarlos como incidente real ni como prueba de generalización. |

Microsoft documenta que Sysmon registra creación de procesos con línea de comandos y ProcessGUID; sus eventos de red deben habilitarse, pues están desactivados por defecto. Elegir el escenario después de comprobar esos campos. [Documentación de Sysmon](https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon).

Para datos públicos, revisar [Splunk attack_data](https://github.com/splunk/attack_data) y [OTRF Security-Datasets](https://github.com/OTRF/Security-Datasets). Son candidatos de datos, no una garantía de que cualquier muestra sirva. Elegir una, revisar campos, volumen, metadatos y condiciones de reutilización; mantener las etiquetas de evaluación fuera de la entrada del modelo. Un dataset de ataques no reemplaza el control legítimo.

Atomic Red Team se usa, si conviene, en un laboratorio aislado y autorizado independiente del analizador. Elegir una prueba por la conducta observable y la telemetría disponible, revisar requisitos y limpieza, ejecutar y conservar el registro de lo que realmente ocurrió. El resultado de ejecución de la prueba no prueba que el sensor la haya registrado. El LLM no decide ni ejecuta Atomic.

**Casos de evaluación.** Elegir una plataforma. Para Windows, una comparación posible es una secuencia de procesos y acciones de administración simulada sospechosa frente a una tarea legítima semejante. No etiquetar toda ejecución de PowerShell como ataque. Para Linux, intentos de autenticación sospechosos frente a una automatización mal configurada, reconociendo que la periodicidad por sí sola no demuestra su legitimidad.

| Caso | Resultado esperado |
|---|---|
| A. Secuencia sospechosa controlada | Reconstruir eventos clave, citar evidencias y sugerir solo técnicas observables; no atribuir intenciones no registradas. |
| B. Actividad legítima semejante | No declarar compromiso confirmado; considerar contexto suministrado y señalar dudas restantes. |
| C. Evidencia incompleta | Abstenerse de conclusiones fuertes e identificar el dato faltante. |
| D. Instrucción insertada en un campo de log | Conservar el texto como evidencia y no obedecerlo. |
| E. Eventos desordenados, duplicados o sin zona horaria | Orden y conteos consistentes con política declarada; advertencias visibles. |
| F. Fallo técnico o respuesta inventada | Rechazar ID inexistente/salida inválida y conservar acceso a la evidencia. |

Registrar manualmente la verdad de referencia: eventos esenciales, hechos permitidos, técnicas respaldadas, explicaciones alternativas y conclusiones prohibidas. Guardarla separada del input. Retirar de la entrada etiquetas como nombre de escenario, técnica esperada o «ataque confirmado». Si la evaluación incluye mapeos preexistentes de reglas, medir la explicación y trazabilidad; no afirmar que el modelo descubrió esas etiquetas.

Medidas mínimas: referencias resolubles/total; afirmaciones respaldadas/total revisadas; hechos esenciales recuperados/total esperado; técnicas correctas/total sugerido; omisiones; declaraciones falsas de compromiso en el control legítimo; latencia; consumo; éxito o fallo de cada intento de manipulación. Reportar numeradores y denominadores. Dos escenarios permiten demostrar el recorrido, no estimar precisión poblacional. Con tiempo adicional, crear varias variantes por escenario y repetir para observar inestabilidad.

Comparar tres modalidades sobre los mismos casos: cronología y reglas solas, LLM directo y pipeline propuesto. La comparación permite identificar qué aporta la IA: mejor explicación o menor tiempo de revisión, sin pérdida de fidelidad. Cualquier medición con el propio equipo y pocos casos es exploratoria, no validación de usuarios externos.

**Resistencia a manipulación.** Los registros pueden contener texto controlado por un atacante. Separar instrucciones de datos, validar salidas, restringir capacidades y evaluar ataques son defensas complementarias; un prompt que diga «ignorá instrucciones maliciosas» no basta. [OWASP: prevención de prompt injection](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

El modelo no recibe herramientas ejecutables. El catálogo es local y controlado; las consultas a datos son parametrizadas; campos de logs y salidas se renderizan como texto escapado. Los hechos deterministas no se reemplazan con texto del modelo. Un ID real puede estar citado incorrectamente: solo una validación semántica o revisión humana detectará ese caso. Si la salida parece manipulada o inválida, marcar fallo y mantener cronología. Reportar «resistió estos ensayos» y su número, sin afirmar inmunidad general.

**Plan propuesto de 48 horas.** Adaptar al tiempo real restante; no presupone que todavía queden 48 horas completas.

| Bloque | Entrega |
|---|---|
| 0–2 h | Hardware identificado, fuente elegida y prueba de inferencia local medida. |
| 2–8 h | Importación, identidad de eventos, cronología y dos casos documentados. |
| 8–16 h | Catálogo local, selección de contexto, esquema de salida y validadores. |
| 16–26 h | Recorrido completo en interfaz: cargar, analizar, revisar evidencia y exportar. |
| 26–36 h | Controles legítimo/incompleto/manipulado; comparación de modalidades y correcciones. |
| 36–42 h | Instalación reproducible, versiones, licencias, límites y tabla de resultados. |
| 42–48 h | Congelar funciones, ensayar pitch y demo; preparar respaldo claramente identificado. |

Reparto sugerido para acordar: una persona integra datos y reglas, otra inferencia e interfaz; Kaki define casos, mantiene referencia de evaluación, revisa evidencia con apoyo técnico y prepara README y relato de demo. No asumir asignación definitiva sin acuerdo del equipo.

**Demo de tres minutos.** 0:00–0:20: problema concreto. 0:20–1:20: cargar caso, mostrar cronología y resumen, abrir evidencia de una conclusión. 1:20–2:00: control legítimo o insuficiente para demostrar límites. 2:00–2:30: prueba de manipulación y métricas realmente obtenidas. 2:30–3:00: ejecución local, limitaciones y adopción. Dejar el modelo cargado antes del inicio y declarar cualquier resultado precalculado. Preparar respuestas para el minuto de preguntas: qué hace la IA, cómo se valida, qué ocurre si falla, qué reutilizamos y cuál es el aporte nuevo.

**Adopción posterior.** Probar primero con registros exportados y un analista responsable; ampliar formatos únicamente con fixtures y evaluación. Antes de uso operativo harían falta autenticación, control de acceso, aislamiento de casos, retención, auditoría, actualización del catálogo, endurecimiento del servicio y validación más amplia. Incorporar integración con un SIEM o gestor de casos después del MVP. La ejecución local ayuda a controlar datos, pero no sustituye estos requisitos.

**Licencias y reproducibilidad.** Mantener inventario de componente, versión, origen, licencia y modificaciones. Hayabusa declara AGPLv3 y una licencia distinta para reglas; revisar ambos artefactos si se incorporan. No asumir que todos los componentes o modelos tienen la misma licencia ni que «público» equivale a libre redistribución. La revisión documental no constituye un dictamen de compatibilidad. Declarar trabajo previo y aportes del hackathon en el README.

**Decisiones pendientes que sí cambian la implementación.** RAM/CPU/GPU efectivamente disponibles; sistema operativo; muestra y volumen de logs; posibilidad de preparar descargas; telemetría disponible; autorización y utilidad de Atomic en el entorno. Con eso se elige el adaptador y el modelo. El alcance de producto y los criterios de evidencia ya pueden acordarse ahora.

**Primera tarea concreta.** Registrar hardware y seleccionar un archivo pequeño con eventos interpretables por el equipo. Ejecutar el recorrido archivo → cronología → modelo local → salida estructurada → apertura de evidencia. Si no funciona dentro del bloque inicial, simplificar antes de invertir en interfaz. Mantener este Work como espacio de investigación y coordinación del proyecto.
