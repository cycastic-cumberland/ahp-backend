from typing import Optional, Any
from pydantic import BaseModel
import pandas as pd

class Matrix(BaseModel):
    data: list[list[float]]
    criteria_name: Optional[str] = None

class ProcessMatrixRequest(BaseModel):
    criteria_matrix: Matrix
    selection_matrices: list[Matrix]
    criteria_ri: Optional[float] = None
    selection_ri: Optional[float] = None

class Table(BaseModel):
    column_headers: list[str]
    row_headers: list[str]
    data: list[list[float]]

class ProcessResult(BaseModel):
    average: Table
    completed: Table
    lambda_max: float
    ci: float
    ri: float
    cr: float

class ScoreboardData(BaseModel):
    rating_table: Table
    criteria_weight_table: Table
    composited: Table
    highest_score: str

class SelectionKeyPair(BaseModel):
    name: str
    result: ProcessResult

class ProcessMatrixResponse(BaseModel):
    criteria: ProcessResult
    selections: list[SelectionKeyPair]
    scoreboard: ScoreboardData

def create_table(df: pd.DataFrame) -> Table:
    return Table(
        column_headers=list(df.columns),
        row_headers=list(df.index.astype(str)),
        data=df.astype(float).values.tolist()
    )
