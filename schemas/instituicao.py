
from typing import Optional

from pydantic import BaseModel


class InstituicaoResponse(BaseModel):
    id:     int
    nome:   str
    sigla:  Optional[str]


    class Config:
        from_attributes = True