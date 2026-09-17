#!/usr/bin/env bash
# Prueba de humo sin red (issue #12): corre el recorrido completo dentro de
# una network namespace vacía (unshare --net). Si `unshare` no está
# disponible, deshabilitar la red manualmente y ejecutar
# `DEMO_SIN_RED=1 scripts/prueba_humo_offline.sh`.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${DEMO_SIN_RED:-0}" != "1" ]; then
    if ! unshare --user --map-root-user --net true 2>/dev/null; then
        echo "unshare --net no está disponible: deshabilitar la red y reintentar con DEMO_SIN_RED=1" >&2
        exit 1
    fi
    echo "== Ejecutando la prueba dentro de una network namespace sin salida =="
    exec unshare --user --map-root-user --net env DEMO_SIN_RED=1 "$0" "$@"
fi

echo "== Sin red: recorrido con adaptadores controlados =="
.venv/bin/python -m investigacion | grep -E "Caso |Modalidad|Hallazgos"

echo
echo "== Sin red: exportación del respaldo persistido =="
SALIDA="$(mktemp -d)/informe.md"
.venv/bin/python -m investigacion.informe \
    --datos docs/demo/respaldo/datos \
    --salida "$SALIDA"
.venv/bin/python -m investigacion.informe --verificar "$SALIDA"

echo
echo "== Sin red: modo degradado (inferencia inalcanzable) =="
.venv/bin/python - <<'PY'
from investigacion.adaptadores.controlados import EvidenciaControlada
from investigacion.adaptadores.ollama import InferenciaOllama
from investigacion.adaptadores.memoria import RepositorioEnMemoria
from investigacion.modelos import ModalidadInferencia, Origen
from investigacion.modulo import ModuloDeInvestigacion
from investigacion.sembrado import (
    PROCEDENCIA_SEMBRADA, RUTA_SEMBRADA, eventos_sembrados,
)

modulo = ModuloDeInvestigacion(
    EvidenciaControlada(eventos=eventos_sembrados()),
    # Endpoint inalcanzable: el caso debe persistir en modo degradado.
    InferenciaOllama("sin-modelo", base_url="http://127.0.0.1:1", timeout=2),
    RepositorioEnMemoria(),
)
caso = modulo.crear_caso(Origen(ruta=RUTA_SEMBRADA, procedencia=PROCEDENCIA_SEMBRADA))
caso = modulo.investigar_caso(caso.id)
assert caso.modalidad_inferencia is ModalidadInferencia.DEGRADADO
assert caso.eventos and caso.errores
verificacion = modulo.verificar_caso(caso.id)
assert verificacion.integro
print(f"modo degradado confirmado: {len(caso.eventos)} eventos, "
      f"custodia íntegra ({verificacion.sello[:12]}…)")
PY

echo
echo "== Prueba de humo sin red: OK =="
