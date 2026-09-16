# Investigación local de eventos

Este contexto define el lenguaje del asistente que investiga eventos de seguridad sin enviar datos fuera de la infraestructura propia.

## Language

**Investigador de incidentes**:
El usuario primario que examina registros exportados para reconstruir actividad y decidir qué merece investigación adicional.
_Avoid_: Alumno, operador autónomo

**Evidencia**:
Un evento o campo de origen que respalda una afirmación y que el analista puede consultar directamente.
_Avoid_: Prueba concluyente

**Observable**:
Un dato registrado, como una dirección IP, un dominio o un hash, cuya presencia no implica por sí sola actividad maliciosa.
_Avoid_: Amenaza, ataque

**Indicador de compromiso**:
Un observable cuyo contexto o procedencia aporta razones para asociarlo con una intrusión; no es una técnica ATT&CK.
_Avoid_: Técnica, comportamiento

**Hipótesis ATT&CK**:
Una interpretación revisable que vincula evidencia con una técnica ATT&CK candidata y explicita sus límites o evidencia faltante.
_Avoid_: Clasificación definitiva, ataque confirmado

**Investigación asistida**:
La reconstrucción de una cronología y la formulación de hipótesis trazables, manteniendo la decisión operativa en manos humanas.
_Avoid_: Detección autónoma, reemplazo del analista

**Emulación adversaria controlada**:
La ejecución autorizada y aislada de comportamientos ATT&CK para producir telemetría y validar controles defensivos.
_Avoid_: Ataque real, capacidad ofensiva del asistente

**Control legítimo**:
Un caso autorizado que produce telemetría semejante al escenario sospechoso y permite comprobar que el asistente no declara compromiso solo por reconocer una herramienta de doble uso.
_Avoid_: Caso negativo trivial, ausencia de actividad

**Verdad de referencia**:
El registro separado de los hechos esperados, técnicas respaldadas y conclusiones prohibidas con el que se evalúa una investigación.
_Avoid_: Etiqueta incluida en la entrada del modelo

**Caso de investigación**:
El conjunto de evidencia, cronología, hipótesis y revisión humana correspondiente a una actividad examinada por el investigador.
_Avoid_: Conversación, alerta individual

**Hallazgo**:
Una hipótesis revisable que reúne evidencia citada, técnicas candidatas, explicaciones alternativas y datos faltantes.
_Avoid_: Veredicto, respuesta del modelo

**Nodo privado de inferencia**:
Infraestructura de cómputo administrada por el equipo o la institución que ejecuta el modelo sin delegar datos ni inferencia a un proveedor externo.
_Avoid_: Servicio cloud, API pública

**Modo degradado**:
El funcionamiento sin nuevas hipótesis del modelo que conserva importación, cronología, detecciones Hayabusa y navegación de evidencia.
_Avoid_: Inferencia offline, análisis completo
