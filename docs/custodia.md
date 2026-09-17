# Cadena de custodia e integridad del informe

El repositorio registra una cadena append-only por caso (ADR-0017): cada
`guardar` agrega una entrada `custodia` cuyo sello encadena el sello anterior
con el SHA-256 del estado persistido. El informe exportado publica el sello
de la cabeza, de modo que una edición posterior del estado —o una cadena
reescrita— se detecta al verificar.

## Qué detecta

- Una edición directa del estado persistido (tablas `casos` o `eventos`):
  el sello del estado leído difiere del último sello registrado.
- Una entrada eliminada o reordenada: la cadena queda discontinua o un
  eslabón deja de encadenar con el anterior.
- Una cadena reescrita por completo: el sello de la cabeza difiere del
  sello publicado en el informe.
- Un informe modificado en disco: `python -m investigacion.informe
  --verificar <informe>` compara el SHA-256 del archivo con el declarado
  en su `.sha256` (escrito junto a cada `--salida`).

## Qué no cubre

La cadena vive en la misma base que custodia: quien tenga escritura total
podría reexportar un sello autoconsistente. La garantía se ancla en el
sello publicado fuera del almacén (un registro de hash, no una firma); el
manifiesto prevé un campo `firma` como evolución. La confidencialidad de la
evidencia en reposo se delega al disco y al sistema operativo.

## Uso

```python
verificacion = modulo.verificar_caso(caso_id, sello_publicado=sello_del_informe)
verificacion.integro        # True si no hubo discrepancias
verificacion.discrepancias  # motivos concretos cuando es False
```

```bash
# Exportar el informe y su sello de artefacto
python -m investigacion.informe --datos datos --caso <id> --salida informe.md
# Verificar que el archivo no cambió desde la exportación
python -m investigacion.informe --verificar informe.md
```
