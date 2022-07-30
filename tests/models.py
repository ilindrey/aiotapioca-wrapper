from dataclasses import dataclass
from typing import List

from pydantic import BaseModel, dataclasses


class Detail(BaseModel):
    key1: str
    key2: int


class CustomModel(BaseModel):
    data: List[Detail]


class RootModel(BaseModel):
    __root__: List[Detail]


@dataclasses.dataclass
class DetailDT:
    key1: str
    key2: int


@dataclasses.dataclass
class CustomModelDT:
    data: List[DetailDT]


@dataclass
class NotPydanticDT:
    data: List[DetailDT]
