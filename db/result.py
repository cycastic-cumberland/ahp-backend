from typing import Dict, Optional
from sqlmodel import SQLModel, Field, Column, JSON


class ResultModel(SQLModel, table=True):
    __tablename__ = "results"

    id: Optional[int] = Field(default=None, primary_key=True)
    criteria: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    selections: list[Dict] = Field(default_factory=dict, sa_column=Column(JSON))
    scoreboard: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    class Config:
        arbitrary_types_allowed = True
