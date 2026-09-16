# Importación EVTX verificable (#3)

La implementación usa los contratos existentes `MotorDeEvidencia` y
`RepositorioDeCasos`. `EvidenciaHayabusa` procesa el archivo y
`RepositorioSQLite` conserva el caso y permite consultarlo ordenado por tiempo.
No requiere un modelo. La conexión con la interfaz y los hallazgos es trabajo de #6.

## Preparación

1. Ejecutar `uv sync` con los requisitos del README.
2. Descargar la distribución completa de [Hayabusa 4.1.0](https://github.com/Yamato-Security/hayabusa/releases/tag/v4.1.0)
   correspondiente al sistema operativo y extraerla fuera del repositorio.
   Mantener `rules/` y `config/` junto al ejecutable. En Linux darle permiso de ejecución.
3. Descargar explícitamente el fixture público:

```bash
uv run python scripts/descargar_fixture.py
```

El manifiesto `tests/fixtures/publico/manifest.json` fija URL, revisión, tamaño y
SHA-256. El script verifica esos valores incluso si el archivo ya existe. El
binario EVTX no se distribuye en este repositorio. Consultar los enlaces de
procedencia y licencia del manifiesto antes de redistribuirlo.

## Importar y consultar

Sustituir la ruta de Hayabusa por la del ejecutable extraído:

```bash
uv run python -m investigacion.importar \
  --evtx tests/fixtures/publico/eventos.evtx \
  --procedencia https://github.com/Yamato-Security/hayabusa-sample-evtx/tree/0845333ecb4afcf64c55c6e10946383f168f308c/DeepBlueCLI \
  --sha256 971915aa6e7a508c4f0a2cb0e76882fd43234fa61c906dc33adf431efc8f2cd4 \
  --hayabusa /ruta/hayabusa-4.1.0-lin-x64-gnu \
  --datos datos
```

En PowerShell se puede escribir el comando en una sola línea. La salida informa
el identificador del caso, número de eventos, hash y rutas de evidencia y SQLite.
Para integrar desde Python:

```python
from pathlib import Path
from investigacion.adaptadores.controlados import InferenciaNoDisponibleControlada
from investigacion.adaptadores.hayabusa import EvidenciaHayabusa
from investigacion.adaptadores.sqlite import RepositorioSQLite
from investigacion.modelos import Origen
from investigacion.modulo import ModuloDeInvestigacion

modulo = ModuloDeInvestigacion(
    EvidenciaHayabusa(Path('/ruta/hayabusa'), Path('datos/evidencia')),
    InferenciaNoDisponibleControlada(),
    RepositorioSQLite(Path('datos/casos.sqlite')),
)
caso = modulo.crear_caso(Origen('tests/fixtures/publico/eventos.evtx', 'URL pública documentada'))
recuperado = modulo.consultar_caso(caso.id)
```

## Qué se conserva

Cada importación crea una carpeta propia con `original.evtx`, `hayabusa.jsonl` y
`manifest.json`. El manifiesto registra procedencia, SHA-256, comando, fecha de
importación y huellas del ejecutable, reglas, configuración y salida. Se verifica
que la copia coincida con la fuente y que el original no cambie al procesarlo.
No se actualizan reglas ni se descargan datos durante la importación.

Cada evento tiene un UID derivado del hash del EVTX, canal y `EventRecordID`.
Reimportar el mismo registro mantiene el UID, aunque el caso tenga otro ID.
Las detecciones de varias reglas sobre un registro se agrupan en un evento;
`contenido` conserva sus filas originales y marca el mapeo como heredado de reglas.
`regla_hayabusa` contiene los identificadores separados por punto y coma.
El localizador y la referencia apuntan al original conservado; el fragmento de
la URI es un localizador para la aplicación, no un visor EVTX del navegador.

Los tiempos se normalizan a UTC con siete posiciones decimales para ordenar
consistentemente. `timestamp_original` conserva el texto emitido por Hayabusa;
el valor original de Windows sigue en el EVTX. No se promete una precisión mayor
que la del lector. Tiempos ausentes van al final; formatos inválidos o sin zona
horaria se rechazan. SQLite conserva también hallazgos, errores y modalidad de
inferencia al guardar un caso actualizado.

## Verificación

```bash
uv run pytest
uv run mypy src
```

La suite ordinaria usa dobles del proceso externo y un encabezado sintético,
claramente separado del fixture público. Para la prueba con herramientas reales:

```bash
HAYABUSA_BIN=/ruta/hayabusa-4.1.0-lin-x64-gnu uv run --with python-evtx==0.8.1 pytest tests/test_evtx_real.py
```

En PowerShell definir antes `$env:HAYABUSA_BIN = 'C:\ruta\hayabusa.exe'` y ejecutar
`uv run --with python-evtx==0.8.1 pytest tests/test_evtx_real.py`.
La prueba reabre SQLite, verifica el hash, comprueba los registros contra XML
extraído por un lector independiente y verifica UIDs estables al reimportar.
Compara identificador, canal, equipo y tipo; no compara precisión temporal entre lectores.

El fixture de 69.632 bytes produjo 12 detecciones agrupadas en tres registros
(8423, 8424 y 8426), de cinco registros originales, con la distribución probada.
Esta cronología contiene registros detectados por Hayabusa: **no representa todos
los eventos del EVTX**, y una salida vacía no prueba ausencia de actividad.

## Límites e integración

- Se fija Hayabusa 4.1.0 porque su comando `dfir-timeline` y formato son parte del
  adaptador verificado. Otras versiones se rechazan explícitamente.
- El límite de entrada es 100 MiB y el timeout por proceso es 120 segundos.
  La salida se limita a 64 MiB después de generarse; esto no es un aislamiento
  completo de CPU, memoria o disco. El encabezado no valida toda la integridad EVTX.
- Las rutas persistidas son absolutas. Copiar solamente SQLite a otro equipo no
  transporta la evidencia: conservar el almacén y sus rutas, o reimportar.
- El manifiesto de procedencia y los nombres del escenario son material de
  evaluación; no deben enviarse al modelo como respuesta esperada.
- El fixture verifica importación y trazabilidad. No completa la comparación
  sospechoso/legítimo ni el ground truth separado requeridos por #8.
