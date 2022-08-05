from typing import Optional, TypeVar, Generic

from bson import ObjectId
from pydantic import BaseModel

ID = TypeVar("ID")


class IdModel(BaseModel):
    id: Optional[ID]
