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
| Catálogo ATT&CK | Enterprise v15.1, subconjunto local de 30 técnicas | copia fijada en `src/investigacion/datos/catalogo_attack.json` desde [attack.mitre.org](https://attack.mitre.org/resources/attack-data-and-tools/) | Términos de uso MITRE ATT&CK |
| Fixture EVTX | sha256 `971915aa…8f2cd4` | [hayabusa-sample-evtx](https://github.com/Yamato-Security/hayabusa-sample-evtx/tree/0845333ecb4afcf64c55c6e10946383f168f308c/DeepBlueCLI) `DeepBlueCLI` @ `0845333` | GPL-3.0 (mismo repositorio) |
| Control legítimo | `eventos_control_legitimo()` | generado en código (`escenarios.py`) | propio |
| Galería EVTX | dataset completo | [EVTX-ATTACK-SAMPLES](https://github.com/sbousseaden/EVTX-ATTACK-SAMPLES) | GPL (`LICENSE.GPL` en el repositorio) |
| Inferencia de la galería | `deepseek-v4-flash` vía opencode Zen | endpoint externo `https://opencode.ai/zen/v1`, requiere `OPENCODE_API_KEY` y opt-in explícito | por proveedor |
| Mapa ATT&CK de display | 334 técnicas desde 4.287 reglas | generado por `scripts/generar_mapa_attack.py` desde las reglas Hayabusa fijadas | derivado de GPL-3.0 |

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

## Galería pre-procesada

Los casos de la galería se importaron con Hayabusa 4.1.0 sobre EVTX del
dataset público EVTX-ATTACK-SAMPLES y se investigaron con `deepseek-v4-flash`
a través del endpoint externo opencode Zen (`scripts/preprocesar_zen.py`).
Cada caso declara la modalidad `modelo_externo` y registra en sus
advertencias que la evidencia salió a un endpoint fuera de la infraestructura
controlada — se presenta como lo que es: pre-procesado externo sobre datos
públicos. El pipeline completo también corre 100% local con Ollama, solo que
más lento (~5-6 min por caso en CPU).

Para regenerar la galería:

```bash
OPENCODE_API_KEY=... python scripts/preprocesar_zen.py \
  --manifiesto <manifiesto.json> \
  --hayabusa ~/tools/hayabusa-4.1.0/hayabusa-4.1.0-lin-x64-musl \
  --datos datos
```

El manifiesto es una lista JSON de `{evtx, procedencia, nombre?, contexto?,
solo_hayabusa?}`; `solo_hayabusa` importa sin inferir (casos de modo
degradado para el beat de fallback).

El arranque en vivo no depende de ningún servicio cloud: la aplicación,
Streamlit, SQLite y Ollama corren localmente, y el respaldo no requiere ni
Ollama. La inferencia externa sólo se usó para preparar la galería.

## Inferencia interactiva de la interfaz

La interfaz infiere contra Ollama exclusivamente; Zen nunca se habilita
desde la UI aunque `OPENCODE_API_KEY` exista. Cadena de respaldo
(ADR-0011): nodo privado declarado, modelo local, modo degradado.

| Variable | Defecto | Uso |
|---|---|---|
| `OLLAMA_MODELO_NODO` + `OLLAMA_BASE_URL_NODO` | sin nodo | Nodo privado primario; requiere ambas |
| `OLLAMA_MODELO` | `qwen2.5:7b-instruct` | Modelo local (o endpoint declarado); `""` desactiva la inferencia |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint del modelo local |
| `INVESTIGACION_HOST_CONTROLADO` | vacío | Hosts propios adicionales, separados por coma |

Si el endpoint declarado es público y no está en
`INVESTIGACION_HOST_CONTROLADO`, la inferencia se rechaza y el caso queda
en modo degradado: la evidencia nunca sale a infraestructura no declarada.

## Respaldo de presentación

`docs/demo/respaldo/` contiene una corrida guardada del caso sospechoso
(importación real por Hayabusa + inferencia real del modelo local + cadena
de custodia), claramente identificada como respaldo (ver su `LEEME.md`).
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
