from dataclasses import dataclass

from pydantic import BaseModel, dataclasses


class Detail(BaseModel):
    key1: str
    key2: int


class CustomModel(BaseModel):
    data: list[Detail]


class RootModel(BaseModel):
    __root__: list[Detail]


@dataclasses.dataclass
class DetailDT:
    key1: str
    key2: int


@dataclasses.dataclass
class CustomModelDT:
    data: list[DetailDT]


@dataclass
class NotPydanticDT:
    data: list[DetailDT]
