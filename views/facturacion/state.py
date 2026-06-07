"""
state.py
Estado interno de la vista de facturación.
Contenedor puro de datos — sin referencias a controles de UI.
"""
from __future__ import annotations


class FacturacionState:
    """
    Agrupa todo el estado mutable de la vista de facturación en un único objeto.
    No importa nada de flet ni de la DB; es un dataclass liviano con mutación
    directa (sin @dataclass para mantener compatibilidad con Flet 0.23).
    """

    def __init__(self) -> None:
        self.current_numero: str | None = None
        self.is_saved: bool = False
        self.last_generated_image: str | None = None
        self.suppress_dirty: bool = False
        self.history_filter: str = ""
        self.items_controls: list[dict] = []
        self.original_total: float = 0.0