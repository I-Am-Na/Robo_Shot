import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.application.car.dto import VisitCarInput
from src.application.car.use_cases import VisitCarUseCase
from src.core.dependencies import get_visit_car_use_case
from src.presentation.api.v1.schemas import CarVisitRequest, CarVisitResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["car"])


@router.put("/car", response_model=CarVisitResponse)
async def upsert_car(
    body: CarVisitRequest,
    use_case: VisitCarUseCase = Depends(get_visit_car_use_case),
):
    try:
        result = await use_case.execute(VisitCarInput(**body.model_dump()))
    except Exception as exc:
        logger.exception("PUT /car failed")
        return JSONResponse(
            status_code=500,
            content=CarVisitResponse(success=False, message=str(exc)).model_dump(),
        )
    return CarVisitResponse(**result.model_dump())
