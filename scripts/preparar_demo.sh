#!/usr/bin/env bash
# Verificación previa a la demo (issue #12): cada componente fijado se
# comprueba antes de la exposición. Uso: scripts/preparar_demo.sh
set -u
cd "$(dirname "$0")/.."

HAYABUSA="${HAYABUSA:-$HOME/tools/hayabusa-4.1.0/hayabusa-4.1.0-lin-x64-musl}"
EVTX_FIXTURE="tests/fixtures/publico/eventos.evtx"
EVTX_SHA="971915aa6e7a508c4f0a2cb0e76882fd43234fa61c906dc33adf431efc8f2cd4"
MODELO="${OLLAMA_MODELO:-qwen2.5:7b-instruct}"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
RESPALDO="docs/demo/respaldo"

ok() { printf '  OK   %s\n' "$1"; }
mal() { printf '  FALTA %s\n' "$1"; fallas=$((fallas + 1)); }
fallas=0

echo "== Dependencias (uv.lock) =="
if uv sync --locked --quiet 2>/dev/null; then ok "uv sync --locked"; else mal "uv sync --locked"; fi

echo "== Motor de evidencia =="
if [ -x "$HAYABUSA" ] && "$HAYABUSA" help 2>/dev/null | grep -q "v4\.1\.0"; then
    ok "Hayabusa 4.1.0 ejecutable ($HAYABUSA)"
else
    mal "Hayabusa 4.1.0 ejecutable ($HAYABUSA)"
fi

echo "== Evidencia fijada =="
if [ -f "$EVTX_FIXTURE" ] && echo "$EVTX_SHA  $EVTX_FIXTURE" | sha256sum -c - >/dev/null 2>&1; then
    ok "fixture EVTX sha256 ${EVTX_SHA:0:16}…"
else
    mal "fixture EVTX sha256 $EVTX_SHA"
fi

echo "== Catálogo ATT&CK fijado =="
if .venv/bin/python -c "
from investigacion.catalogo_attack import cargar_catalogo
c = cargar_catalogo()
assert 'v15.1' in c.version and len(c.tecnicas) == 8
" 2>/dev/null; then
    ok "catálogo ATT&CK v15.1 (subconjunto de 8 técnicas)"
else
    mal "catálogo ATT&CK v15.1"
fi

echo "== Modelo local precargado =="
if curl -sf -m 5 "$OLLAMA_URL/api/version" >/dev/null 2>&1; then
    ok "endpoint Ollama accesible ($OLLAMA_URL)"
    if curl -sf -m 10 "$OLLAMA_URL/api/generate" -d "{\"model\":\"$MODELO\",\"keep_alive\":\"15m\",\"prompt\":\"\",\"stream\":false}" >/dev/null 2>&1 \
       || docker exec ollama-eval ollama list 2>/dev/null | grep -q "$MODELO"; then
        ok "modelo $MODELO descargado/precargado"
    else
        mal "modelo $MODELO descargado"
    fi
else
    mal "endpoint Ollama accesible ($OLLAMA_URL)"
fi

echo "== Respaldo de presentación =="
if [ -f "$RESPALDO/datos/casos.sqlite" ] && [ -f "$RESPALDO/informe.md" ]; then
    ok "corrida guardada en $RESPALDO/"
else
    mal "corrida guardada en $RESPALDO/ (ver docs/demo/preparacion.md)"
fi
if [ -f "$RESPALDO/informe.md" ]; then
    if .venv/bin/python -m investigacion.informe --verificar "$RESPALDO/informe.md" >/dev/null 2>&1; then
        ok "informe de respaldo íntegro"
    else
        mal "informe de respaldo íntegro"
    fi
fi

echo
if [ "$fallas" -eq 0 ]; then
    echo "Todo listo para la demo."
else
    echo "$fallas verificación(es) pendiente(s) — ver docs/demo/preparacion.md"
    exit 1
fi
