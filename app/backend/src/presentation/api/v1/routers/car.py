import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.application.car.dto import VisitCarInput
from src.application.car.use_cases import (
    CompleteFuelingUseCase,
    ListCarsUseCase,
    OrderFuelTypeUseCase,
    PayUseCase,
    VisitCarUseCase,
)
from src.core.dependencies import (
    get_complete_fueling_use_case,
    get_list_cars_use_case,
    get_order_fuel_type_use_case,
    get_pay_use_case,
    get_visit_car_use_case,
)
from src.domain.car.exceptions import CarNotFoundError, CarNotReadyError
from src.presentation.api.v1.schemas import (
    BaseResponse,
    CarItem,
    CarListResponse,
    CarVisitRequest,
    CarVisitResponse,
    CompleteFuelingResponse,
    FuelTypeOrderRequest,
    PayRequest,
)

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


@router.put("/car/{car_num}/fuel-type", response_model=BaseResponse)
async def order_fuel_type(
    car_num: str,
    body: FuelTypeOrderRequest,
    use_case: OrderFuelTypeUseCase = Depends(get_order_fuel_type_use_case),
):
    """음성 주문에서 인식한 유종 저장. 주유 준비(ready) 차량만 가능. 금액은 저장하지 않는다."""
    try:
        await use_case.execute(car_num, body.fuel_type)
    except CarNotFoundError as exc:
        return JSONResponse(status_code=404, content={"success": False, "message": str(exc)})
    except CarNotReadyError as exc:
        return JSONResponse(status_code=409, content={"success": False, "message": str(exc)})
    except Exception as exc:
        logger.exception("PUT /car/{car_num}/fuel-type failed")
        return JSONResponse(status_code=500, content={"success": False, "message": str(exc)})
    logger.info("fuel_type ordered car_num=%s fuel_type=%s", car_num, body.fuel_type.value)
    return BaseResponse(success=True, message="fuel_type saved")


@router.put("/car/{car_num}/pay", response_model=BaseResponse)
async def pay(
    car_num: str,
    body: PayRequest,
    use_case: PayUseCase = Depends(get_pay_use_case),
):
    """QR 결제 완료. 성공하면 success=true, 차량은 paid가 되어 로봇 polling(GET /robot/task)에 잡힌다."""
    try:
        await use_case.execute(car_num, body.fuel_type, body.amount)
    except CarNotFoundError as exc:
        return JSONResponse(status_code=404, content={"success": False, "message": str(exc)})
    except CarNotReadyError as exc:
        return JSONResponse(status_code=409, content={"success": False, "message": str(exc)})
    except Exception as exc:
        logger.exception("PUT /car/{car_num}/pay failed")
        return JSONResponse(status_code=500, content={"success": False, "message": str(exc)})
    logger.info("paid car_num=%s fuel_type=%s amount=%s", car_num, body.fuel_type.value, body.amount)
    return BaseResponse(success=True, message="paid")


@router.put("/car/{car_num}/complete", response_model=CompleteFuelingResponse)
async def complete_fueling(
    car_num: str,
    use_case: CompleteFuelingUseCase = Depends(get_complete_fueling_use_case),
):
    """주유 완료. 이 차량은 done, 가장 먼저 기다린 waiting 차량은 ready가 된다."""
    try:
        result = await use_case.execute(car_num)
    except CarNotFoundError as exc:
        return JSONResponse(status_code=404, content={"success": False, "message": str(exc)})
    except CarNotReadyError as exc:
        return JSONResponse(status_code=409, content={"success": False, "message": str(exc)})
    except Exception as exc:
        logger.exception("PUT /car/{car_num}/complete failed")
        return JSONResponse(status_code=500, content={"success": False, "message": str(exc)})
    logger.info("fueling completed car_num=%s next=%s", car_num, result.next_car_num)
    return CompleteFuelingResponse(**result.model_dump())


@router.get("/car", response_model=CarListResponse)
async def list_cars(
    limit: int = Query(50, ge=1, le=200, description="최대 개수"),
    use_case: ListCarsUseCase = Depends(get_list_cars_use_case),
):
    """차량 목록과 status. 최근 감지된 차량부터. 프론트 대시보드가 polling으로 호출한다."""
    try:
        cars = await use_case.execute(limit)
    except Exception as exc:
        logger.exception("GET /car failed")
        return JSONResponse(status_code=500, content={"success": False, "message": str(exc), "cars": []})
    return CarListResponse(
        success=True,
        message="ok",
        cars=[
            CarItem(**c.model_dump(exclude={"fuel_type"}), fuel_type=c.fuel_type.value if c.fuel_type else None)
            for c in cars
        ],
    )
