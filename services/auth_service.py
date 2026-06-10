"""Singleton AuthService — maneja login/logout y usuario actual."""

from db.database import (
    verificar_pin, crear_usuario, get_usuario_by_nombre,
    registrar_sesion, cerrar_sesion,
    get_usuarios_conectados, registrar_actividad,
)


class AuthService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._user = None
            cls._instance._session_id = None
        return cls._instance

    @property
    def usuario_id(self) -> int | None:
        return self._user["id"] if self._user else None

    @property
    def usuario_nombre(self) -> str:
        return self._user["nombre"] if self._user else ""

    @property
    def iniciales(self) -> str:
        if not self._user:
            return "?"
        parts = self._user["nombre"].strip().split()
        return "".join(p[0].upper() for p in parts[:2]) if parts else "?"

    @property
    def is_authenticated(self) -> bool:
        return self._user is not None

    # ── Auth actions ──────────────────────────────────────────────────────────

    def login(self, nombre: str, pin: str) -> dict | None:
        """Verifica credenciales y crea sesión. Retorna usuario dict o None."""
        u = verificar_pin(nombre, pin)
        if not u:
            return None
        self._user = u
        self._session_id = registrar_sesion(u["id"])
        return u

    def register(self, nombre: str, pin: str) -> tuple[bool, str]:
        """Crea usuario. Retorna (ok, mensaje)."""
        nombre = nombre.strip()
        if len(nombre) < 2:
            return False, "El nombre debe tener al menos 2 caracteres."
        if not pin.isdigit() or len(pin) != 4:
            return False, "El PIN debe tener exactamente 4 números."
        if get_usuario_by_nombre(nombre):
            return False, f"Ya existe un usuario con el nombre '{nombre}'."
        crear_usuario(nombre, pin)
        return True, "Usuario creado correctamente."

    def logout(self):
        if self._session_id:
            cerrar_sesion(self._session_id)
        self._user = None
        self._session_id = None

    def connected_users(self) -> list:
        return get_usuarios_conectados()

    def track(self, tipo: str, referencia: str = "", descripcion: str = ""):
        if self.usuario_id:
            registrar_actividad(self.usuario_id, tipo, referencia, descripcion)
