# Tracer real EVTX → hallazgo → evidencia (#6)

Este documento describe el único flujo que crea un caso real de punta a punta
sin adaptadores controlados: importación Hayabusa, persistencia SQLite,
inferencia estructurada contra Ollama, validación de referencias y navegación
en Streamlit del hallazgo hasta la evidencia citada.

## Preparación

1. `uv sync`.
2. Distribución [Hayabusa 4.1.0](https://github.com/Yamato-Security/hayabusa/releases/tag/v4.1.0)
   con `rules/` y `config/` junto al ejecutable (ver `docs/evidencia.md`).
   En esta máquina Linux la variante `lin-x64-musl` funciona donde la `gnu`
   requiere una glibc más nueva.
3. Servidor Ollama corriendo con el modelo del ADR-0014:
   `ollama pull qwen2.5:7b-instruct`.
4. Fixture público verificado: `uv run python scripts/descargar_fixture.py`.
   El manifiesto `tests/fixtures/publico/manifest.json` fija URL, revisión,
   tamaño y SHA-256.

## Un único comando crea e investiga el caso real

```bash
uv run python -m investigacion.importar \
  --evtx tests/fixtures/publico/eventos.evtx \
  --procedencia https://github.com/Yamato-Security/hayabusa-sample-evtx/tree/0845333ecb4afcf64c55c6e10946383f168f308c/DeepBlueCLI \
  --sha256 971915aa6e7a508c4f0a2cb0e76882fd43234fa61c906dc33adf431efc8f2cd4 \
  --hayabusa /ruta/hayabusa-4.1.0 \
  --datos datos \
  --modelo qwen2.5:7b-instruct
```

`--modelo` activa la inferencia estructurada contra el endpoint Ollama
(`--ollama-url` apunta a otro endpoint y `--modalidad nodo_privado` declara la
modalidad de un nodo privado, mismo contrato ADR-0011). Sin `--modelo` la CLI
conserva su comportamiento anterior: sólo importación.

`--modelo-respaldo` compone el fallback del ADR-0011: si el motor primario
declara inferencia no disponible (nodo privado caído, timeout o respuesta
malformada), `InferenciaConRespaldo` reintenta contra el modelo local del
endpoint `--ollama-url-respaldo` (por defecto `http://localhost:11434`). La
modalidad persistida es la del motor que efectivamente respondió; sólo si
ambos fallan el caso queda en modo degradado con ambos motivos en `errores`.

La salida JSON informa `caso_id`, eventos, hallazgos, modalidad de inferencia,
errores de validación, SHA-256 del original conservado y la ruta de SQLite.
Quedan registrados en el caso los hashes del binario, reglas, configuración y
salida (`origen.versiones`), la procedencia y la modalidad de inferencia.

Si el nodo Ollama no responde, el caso queda persistido en modo degradado con
el motivo en `errores` (ADR-0009); si el modelo propone referencias o técnicas
inaceptables, `ValidadorDeReferencias` las rechaza y el motivo queda
registrado igualmente.

## Recorrer el hallazgo hasta la evidencia en Streamlit

```bash
INVESTIGACION_DATOS=datos uv run streamlit run src/investigacion/ui/app.py
```

`INVESTIGACION_DATOS` apunta al directorio de datos de la importación: la
interfaz lista los casos persistidos en `casos.sqlite`, muestra el hallazgo
validado y permite abrir cada evento citado junto con su procedencia (SHA-256,
localizador original, reglas Hayabusa y versiones). La interfaz sólo consulta
el caso ya investigado: no repite la inferencia. Sin la variable, abre el caso
sembrado de demostración como antes.

## Prueba de integración repetible

```bash
HAYABUSA_BIN=/ruta/hayabusa-4.1.0 OLLAMA_MODELO_PRUEBA=qwen2.5:7b-instruct \
  uv run pytest tests/test_tracer_real.py
```

`tests/test_tracer_real.py` es opt-in como las demás pruebas con herramientas
reales: ejecuta el comando completo, reabre el caso desde SQLite verificando
hashes, versiones, modalidad y que cada referencia del hallazgo apunta a un
evento existente, y recorre la navegación hallazgo → evidencia en Streamlit
con `INVESTIGACION_DATOS` apuntando al directorio temporal.

## Límites

- El resultado del modelo es inherentemente variable entre endpoints y
  versiones de modelo: el contrato verificado es que todo hallazgo persistido
  cita sólo evidencia existente y técnicas del catálogo local. Un hallazgo
  inválido no se descarta en silencio: su rechazo queda en `errores`.
- La cronología contiene sólo registros detectados por Hayabusa; no es todo
  el EVTX (ver `docs/evidencia.md`).
