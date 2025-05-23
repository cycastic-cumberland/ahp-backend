import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
import pandas as pd
import numpy as np
from sqlmodel import select
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from db import SessionDep
from db.result import ResultModel
from sqlalchemy import func
from process import *

router = APIRouter()


CRITERIA = ["Chi phí đầu tư", "Tiêu thụ năng lượng", "Xuất khẩu năng lượng", "Công suất lắp đặt", "Phát thải CO2"]
SELECTIONS = ["Điện mặt trời", "Điện gió", "Thủy điện", "Điện nhiệt"]

NORMALIZED_CRITERIA = [x.upper() for x in CRITERIA]
NORMALIZED_SELECTIONS = [x.upper() for x in SELECTIONS]

CRITERIA_COUNT = len(CRITERIA)
SELECTION_COUNT = len(SELECTIONS)

def validate_request(request: ProcessMatrixRequest):
    errors: list[str] = []
    if len(request.selection_matrices) != CRITERIA_COUNT:
        errors.append(f"Cần có {CRITERIA_COUNT} sự lựa chọn")
    if len(request.criteria_matrix.data) != CRITERIA_COUNT:
        errors.append(f"Ma trận tiêu chí cần có {CRITERIA_COUNT} hàng")

    for row in request.criteria_matrix.data:
        if len(row) != CRITERIA_COUNT:
            errors.append(f"Ma trận tiêu chí cần có {CRITERIA_COUNT} cột")

    normalized_criteria: dict[str, None] = {}
    for matrix in request.selection_matrices:
        nn = matrix.criteria_name.upper()
        normalized_criteria[nn] = None
        if nn not in NORMALIZED_CRITERIA:
            errors.append("Tên lựa chọn không tồn tại")

        if len(matrix.data) != SELECTION_COUNT:
            errors.append(f"Ma trận của tiêu chí {matrix.criteria_name} cần có {CRITERIA_COUNT} hàng")
        for row in matrix.data:
            if len(row) != SELECTION_COUNT:
                errors.append(f"Ma trận của tiêu chí {matrix.criteria_name} cần có {CRITERIA_COUNT} cột")
    if len(normalized_criteria) != CRITERIA_COUNT:
        errors.append("Có lựa chọn bị trùng lặp")
    if len(errors) > 0:
        raise HTTPException(status_code=400, detail=ValidationErrors(validation_errors=errors))

def make_df(matrix: Matrix, headers: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(matrix.data, columns=headers).rename(index={i: header for i, header in enumerate(headers)})
    return df

def process_criteria(criteria: pd.DataFrame, request_ri: Optional[float]) -> (ProcessResult, pd.DataFrame):
    column_sums = np.sum(criteria, axis=0)
    sum_row = pd.DataFrame([column_sums], columns=criteria.columns, index=['Sum'])
    normalized_criteria: pd.DataFrame = criteria.div(np.sum(criteria, axis=0), axis=1)
    sum_criteria = pd.concat([normalized_criteria, sum_row])
    criteria_avg = sum_criteria.iloc()[:].assign(Average=sum_criteria.mean(axis=1))
    criteria_weight = normalized_criteria.mean(axis=1).transpose()
    criteria_unified_vector = criteria.mul(criteria_weight, axis=1)
    completed_criteria = criteria_unified_vector.iloc()[:]
    a1 = completed_criteria.sum(axis=1)
    a2 = normalized_criteria.mean(axis=1)
    a3 = a1.div(a2)
    completed_criteria['weighted sum value'] = a1
    completed_criteria['criteria weight'] = a2
    completed_criteria['consistency vector'] = a3
    lambda_max = a3.mean()
    ci = (lambda_max - 5) / (5 - 1)
    ri = 1.12
    if request_ri is not None:
        ri = request_ri
    return ProcessResult(
        average=create_table(criteria_avg),
        completed=create_table(completed_criteria),
        lambda_max=lambda_max,
        ci=ci,
        ri=ri,
        cr=(ci / ri)
    ), completed_criteria

def process_selection(selection: pd.DataFrame, request_ri: Optional[float]) -> (ProcessResult, pd.DataFrame):
    column_sums = np.sum(selection, axis=0)
    sum_row = pd.DataFrame([column_sums], columns=selection.columns, index=['Sum'])
    normalized_selection = selection.div(np.sum(selection, axis=0), axis=1)
    sum_selection = pd.concat([normalized_selection, sum_row])
    selection_avg = sum_selection.iloc()[:]
    selection_avg['Trọng số P.A'] = selection_avg.mean(axis=1)
    selection_weight = normalized_selection.mean(axis=1).transpose()
    completed_selection = selection.mul(selection_weight, axis=1)
    a1 = completed_selection.sum(axis=1)
    a2 = selection_avg['Trọng số P.A']
    a3 = a1.div(a2, axis=0)
    completed_selection['weighted sum value'] = a1
    completed_selection['criteria weight'] = a2
    completed_selection['consistency vector'] = a3
    lambda_max = a3.mean()
    ci = (lambda_max - 4) / 3
    ri = 0.9
    if request_ri is not None:
        ri = request_ri
    return ProcessResult(
        average=create_table(selection_avg),
        completed=create_table(completed_selection),
        lambda_max=lambda_max,
        ci=ci,
        ri=ri,
        cr=(ci / ri)
    ), completed_selection

def create_scoreboard(complete_criteria: pd.DataFrame, data: dict[str, pd.DataFrame]) -> ScoreboardData:
    rating_table = pd.DataFrame()
    for criteria, df in data.items():
        column_raw = []
        indices = []
        curr_dataframe: pd.DataFrame = df
        for col_name in curr_dataframe.index:
            cell = curr_dataframe.at[col_name, col_name]
            column_raw.append(cell)
            indices = curr_dataframe.index
        series = pd.Series(data=column_raw, index=indices, name=criteria)
        rating_table[criteria] = series

    criteria_weights = []
    for index in complete_criteria.index:
        stuff = complete_criteria.at[index, 'criteria weight']
        criteria_weights.append(stuff)
        pass
    criteria_weight_series = pd.Series(data=criteria_weights, index=complete_criteria.index, name='Trọng số')
    criteria_weight_table = pd.DataFrame(criteria_weight_series, columns=['Trọng số'])

    composited: pd.DataFrame = (rating_table @ criteria_weight_table).rename(columns={'Trọng số': 'Điểm tổng hợp'})
    id_max = composited['Điểm tổng hợp'].idxmax()

    return ScoreboardData(
        rating_table=create_table(rating_table),
        criteria_weight_table=create_table(criteria_weight_table),
        composited=create_table(composited),
        highest_score=str(id_max)
    )

def process_matrix_internal(request: ProcessMatrixRequest) -> ProcessMatrixResponse:
    validate_request(request)

    criteria = make_df(request.criteria_matrix, CRITERIA)
    reified_criteria, criteria_df = process_criteria(criteria, request.criteria_ri)
    selections: dict[str, pd.DataFrame] = {}
    for selection in request.selection_matrices:
        selections[selection.criteria_name] = make_df(selection, SELECTIONS)

    reified_selections: dict[str, ProcessResult] = {}
    selection_df: dict[str, pd.DataFrame] = {}
    for key, value in selections.items():
        reified, df = process_selection(value, request.selection_ri)
        reified_selections[key] = reified
        selection_df[key] = df

    scoreboard = create_scoreboard(criteria_df, selection_df)
    return ProcessMatrixResponse(
        criteria=reified_criteria,
        selections=[SelectionKeyPair(name=x, result=y) for x, y in reified_selections.items()],
        scoreboard=scoreboard
    )

@router.options("/process-matrix")
def process_matrix_options():
    return Response(status_code=204)

@router.post("/process-matrix",
             response_model=ProcessMatrixResponse,
             summary="Tính ma trận với Tiêu chí và Lựa chọn được đặt sẵn",
             description="Tham số optional: criteria_ri, selection_ri. Tham số không dùng đến: criteria_matrix.criteria_name",
             response_description="Điểm tiêu chí, điểm lựa chọn, lựa chọn xếp hạn cao nhất",
             responses={
                 400: {
                     "model": ValidationErrors,
                     "description": "Request không chính xác"
                 }
             })
def process_matrix(request: ProcessMatrixRequest) -> ProcessMatrixResponse:
    return process_matrix_internal(request)

@router.options("/process-and-save-matrix")
def process_matrix_and_save_options():
    return Response(status_code=204)

@router.post("/process-and-save-matrix",
             response_model=IdResponse,
             summary="Tính ma trận với Tiêu chí và Lựa chọn được đặt sẵn",
             description="Tham số optional: criteria_ri, selection_ri. Tham số không dùng đến: criteria_matrix.criteria_name",
             response_description="ID dẫn đến kết quả",
             responses={
                 400: {
                     "model": ValidationErrors,
                     "description": "Request không chính xác"
                 }
             })
async def process_matrix_and_save(request: ProcessMatrixRequest, session: SessionDep) -> IdResponse:
    response = process_matrix_internal(request)
    result_model = ResultModel(id=None,
                               criteria=response.criteria.model_dump(),
                               selections=[x.model_dump() for x in response.selections],
                               scoreboard=response.scoreboard.model_dump())
    session.add(result_model)
    await session.commit()
    await session.refresh(result_model)
    return IdResponse(id=result_model.id)

@router.options("/results")
def read_result_options():
    return Response(status_code=204)

@router.get("/results",
             response_model=ResultPage,
             summary="Truy vấn kết quả",
             response_description="Danh sách kết quả")
async def read_results(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(le=100)] = 10,
) -> ResultPage:
    if page_size <= 0:
        page_size = 1
    statement = select(ResultModel).order_by(ResultModel.id.desc()).offset((page - 1) * page_size).limit(page_size)
    coroutine_result = await session.execute(statement)
    total_item = (await session.execute(select(func.count()).select_from(select(ResultModel).subquery()))).scalar_one()
    models: list[ResultModel] = coroutine_result.scalars().all()
    return ResultPage(
        items=models,
        page=page,
        page_size=page_size,
        total_item=total_item,
        total_page=(total_item // page_size) + 1
    )

@router.options("/result/{result_id}")
def read_result_options():
    return Response(status_code=204)

@router.get("/result/{result_id}",
             response_model=ResultModel,
             summary="Truy vấn kết quả",
             response_description="Kết quả",
             responses={
                 404: {
                     "model": GeneralError,
                     "description": "Kết quả không được tìm thấy"
                 }
             })
async def read_result(
    result_id: int,
    session: SessionDep
) -> ResultModel:
    model: ResultModel = await session.get(ResultModel, result_id)
    if not model:
        raise HTTPException(status_code=404, detail=GeneralError())
    return model

