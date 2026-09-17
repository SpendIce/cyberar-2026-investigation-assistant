# Sobrevivir a fallas de inferencia remota (#7)

`InferenciaConRespaldo` (ADR-0011) ya implementaba la secuencia nodo privado
→ modelo local → modo degradado: prueba cada motor en orden y usa el primero
que responda. `investigacion.importar --modelo-respaldo` ya lo compone desde
la CLI (ver `docs/tracer.md`). Lo que faltaba para #7 era que la transición
fuera **observable**, no sólo funcional: si el nodo privado fallaba y el
modelo local respondía, el caso quedaba en modalidad `modelo_local` sin
ningún rastro de *por qué* — la interfaz no podía explicar el fallback,
sólo mostrar el resultado final.

## Qué cambia

`MotorDeInferencia` (el puerto en `puertos.py`) ahora exige una propiedad
`advertencias: tuple[str, ...]` además de `modalidad` y `proponer`: los
motivos por los que un motor anterior no se usó en la última llamada a
`proponer`. Vacía si no hizo falta ningún respaldo. Todos los adaptadores la
implementan (`InferenciaControlada`, `InferenciaOllama` devuelven `()`
siempre; `InferenciaConRespaldo` la puebla con un mensaje por cada motor que
falló en la última llamada — antes de encontrar uno disponible, o todos si
ninguno respondió — con el formato `"{modalidad} no disponible: {motivo}"`).

`ModuloDeInvestigacion.investigar_caso` vuelca `advertencias` en
`caso.errores` junto con los rechazos de validación — el mismo campo que la
interfaz Streamlit ya mostraba como advertencia (`_mostrar_estado` en
`ui/app.py`). No hizo falta ningún cambio de interfaz: mostrar *qué* modalidad
produjo el resultado (métrica ya existente) y *por qué* hubo un fallback
(ahora en `errores`) ya estaba resuelto una vez que el dato existe.

## Configuración sin secretos

`investigacion.importar` recibe `--ollama-url`, `--modalidad`,
`--modelo-respaldo` y `--ollama-url-respaldo` como argumentos de línea de
comandos: nada queda hardcodeado en el repositorio. Un endpoint con
autenticación (túnel cifrado, ADR-0011) se pasa en `--ollama-url` por quien
invoca el comando (variable de entorno del shell, gestor de secretos), nunca
committeado. Los timeouts son explícitos y configurables por instancia
(`InferenciaOllama(..., timeout=...)`, 120s por defecto).

## Pruebas

`tests/test_respaldo_inferencia_contrato.py` cruza el contrato del módulo
(no la implementación interna de `InferenciaConRespaldo`, que ya tenía sus
propias pruebas unitarias en `tests/test_inferencia_respaldo.py`) para las
tres transiciones que pide el criterio de aceptación:

- **Éxito remoto**: el motor primario responde, `advertencias` queda vacío.
- **Caída remota con éxito local**: el primario falla, el respaldo responde;
  `modalidad_inferencia` es `modelo_local` y el motivo de la caída del
  primario queda en `errores`, consultable después de persistir.
- **Ausencia de ambos**: los dos motores fallan; el caso queda en
  `degradado`, sin hallazgos, con los dos motivos en `errores`, y la
  cronología permanece intacta y consultable (evidencia y detecciones de
  Hayabusa siguen disponibles, como ya garantizaba el modo degradado desde
  #4).

Una cuarta prueba, opt-in (`OLLAMA_MODELO_PRUEBA`), repite el escenario de
caída con `InferenciaOllama` real en ambos puestos — el "nodo privado" apunta
a un puerto sin servidor (falla rápido por conexión rechazada) y el
"modelo local" es un modelo real cargado.

```bash
uv run pytest tests/test_respaldo_inferencia_contrato.py
OLLAMA_MODELO_PRUEBA=llama3.2:3b uv run pytest tests/test_respaldo_inferencia_contrato.py
```
