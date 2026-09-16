"""Errores explícitos del módulo de investigación."""


class ErrorDeImportacion(Exception):
    """La fuente de evidencia no puede importarse."""


class CasoNoEncontrado(Exception):
    """No existe un caso con el identificador solicitado."""


class InferenciaNoDisponible(Exception):
    """Ningún motor de inferencia pudo producir una respuesta."""


class HallazgoInvalido(Exception):
    """La respuesta de inferencia no supera la validación."""
