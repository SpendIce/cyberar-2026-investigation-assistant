# Preparación de la demo (issue #12)

Todo componente de la demo está fijado o versionado. `scripts/preparar_demo.sh`
verifica cada pieza; esta tabla es la referencia de versiones y licencias.

## Inventario fijado

| Componente | Versión fijada | Procedencia | Licencia |
|---|---|---|---|
| Dependencias Python | `uv.lock` | `pyproject.toml` | ver lock |
| Hayabusa | 4.1.0 (`lin-x64-musl`) | [release v4.1.0](https://github.com/Yamato-Security/hayabusa/releases/tag/v4.1.0) | GPL-3.0 |
| Reglas Hayabusa | incluidas en la distribución 4.1.0 | mismo paquete | GPL-3.0 |
| Ollama | 0.34.1 (contenedor `ollama-eval`) | [ollama.com](https://ollama.com) | Apache-2.0 |
| Modelo local | `qwen2.5:7b-instruct` digest `845dbda0ea48` | biblioteca Ollama | Apache-2.0 |
| Catálogo ATT&CK | Enterprise v15.1, subconjunto local de 8 técnicas | copia fijada en `src/investigacion/datos/catalogo_attack.json` desde [attack.mitre.org](https://attack.mitre.org/resources/attack-data-and-tools/) | Términos de uso MITRE ATT&CK |
| Fixture EVTX | sha256 `971915aa…8f2cd4` | [hayabusa-sample-evtx](https://github.com/Yamato-Security/hayabusa-sample-evtx/tree/0845333ecb4afcf64c55c6e10946383f168f308c/DeepBlueCLI) `DeepBlueCLI` @ `0845333` | GPL-3.0 (mismo repositorio) |
| Control legítimo | `eventos_control_legitimo()` | generado en código (`escenarios.py`) | propio |

## Instrucciones de preparación

1. `uv sync --locked` — instala las dependencias exactas del lockfile.
2. Ollama con el modelo precargado:
   `docker start ollama-eval` (o `ollama serve`) y
   `docker exec ollama-eval ollama pull qwen2.5:7b-instruct`.
   Precargar en memoria antes de presentar: la carga fría del modelo en CPU
   insume ~5-6 minutos.
3. Hayabusa 4.1.0 descomprimido en `~/tools/hayabusa-4.1.0/` (o exportar
   `HAYABUSA=<ruta>`).
4. Respaldo de presentación en `docs/demo/respaldo/` (ya generado y
   commiteado; regeneración en "Respaldo" más abajo).
5. `scripts/preparar_demo.sh` — debe salir con "Todo listo para la demo.".

El arranque no depende de ningún servicio cloud: la aplicación, Streamlit,
SQLite y Ollama corren localmente, y el respaldo no requiere ni Ollama.

## Respaldo de presentación

`docs/demo/respaldo/` contiene una corrida guardada del caso sospechoso —
importación real por Hayabusa + inferencia real del modelo local + cadena
de custodia— claramente identificada como respaldo (ver su `LEEME.md`).
Para regenerarla:

```bash
python -m investigacion.importar \
  --evtx tests/fixtures/publico/eventos.evtx \
  --procedencia "<procedencia del fixture>" \
  --hayabusa <ruta>/hayabusa-4.1.0-lin-x64-musl \
  --datos docs/demo/respaldo/datos \
  --modelo qwen2.5:7b-instruct --timeout 600
python -m investigacion.informe \
  --datos docs/demo/respaldo/datos --salida docs/demo/respaldo/informe.md
```

## Prueba de humo sin red

```bash
scripts/prueba_humo_offline.sh
```

Corre dentro de una network namespace sin salida (`unshare --net`) y
confirma: el recorrido sembrado completo, la exportación del respaldo con
verificación de integridad, y el modo degradado con la evidencia intacta.
Si `unshare` no existe en la máquina de exposición, deshabilitar la red y
correr `DEMO_SIN_RED=1 scripts/prueba_humo_offline.sh`.
