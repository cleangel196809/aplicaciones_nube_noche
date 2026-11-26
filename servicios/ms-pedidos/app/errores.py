class ExcepcionDominio(Exception):
    def __init__(self, mensaje: str, codigo_estado: int = 400, detalles: dict | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo_estado = codigo_estado
        self.detalles = detalles or {}

class ErrorDependencia(ExcepcionDominio):
    def __init__(self, servicio: str, codigo_estado: int, mensaje: str):
        super().__init__(mensaje, codigo_estado=codigo_estado)
        self.servicio = servicio