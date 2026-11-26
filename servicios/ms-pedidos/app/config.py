from functools import lru_cache
from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PEDIDOS_", extra="ignore", env_file=".env")

    entorno: Literal["local", "dev", "test", "prod"] = "local"
    nivel_log: str = "INFO"
    docs_habilitada: bool = True
    
    url_catalogo: str = "http://localhost:8001/api/v1"
    url_inventario: str = "http://localhost:8002/api/v1"
    url_pagos: str = "http://localhost:8004/api/v1"
    
    modo_descubrimiento: Literal["estatico", "consul"] = "estatico"
    consul_url: str = "http://consul:8500"
    nombre_servicio: str = "ms-pedidos"
    host_anunciado: str = "ms-pedidos"
    puerto_servicio: int = 8003

    @field_validator("nivel_log")
    @classmethod
    def val_nivel_log(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            raise ValueError("Nivel de log inválido")
        return v_upper

@lru_cache
def get_configuracion() -> Configuracion:
    return Configuracion()