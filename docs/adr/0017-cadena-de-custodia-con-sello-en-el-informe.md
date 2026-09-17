---
status: accepted
---

# Registrar una cadena de custodia con sello publicado en el informe

Cada escritura del repositorio agrega una entrada append-only cuyo sello encadena el sello anterior con el hash SHA-256 del estado persistido. El informe exportado publica el sello de la cabeza; `verificar_caso` contrasta la cadena persistida contra el estado leído y contra el sello publicado, y el CLI de informe verifica además el artefacto contra su archivo `.sha256`. La cadena vive en la misma base que custodia: la garantía se ancla en el sello publicado fuera del almacén, comparable a un registro de hash forense y no a una firma criptográfica.

## Consequences

La edición directa del estado persistido, la eliminación de una entrada o la reescritura de la cadena se detectan al verificar contra el sello publicado. Un atacante con acceso de escritura a la base podría reexportar un sello autoconsistente; la firma del manifiesto con clave del equipo queda como evolución prevista. La confidencialidad de la evidencia en reposo se delega al disco y al sistema operativo, fuera del alcance de esta cadena.
