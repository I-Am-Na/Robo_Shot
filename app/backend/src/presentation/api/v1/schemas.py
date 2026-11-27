from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.domain.car.value_objects import FuelType


class CarVisitRequest(BaseModel):
    car_num: str = Field(..., min_length=1, max_length=20, examples=["12가3456"])
    is_line: bool
    line_num: Literal[1, 2]
    fuel_type: FuelType | None = Field(
        default=None, description="휘발유 또는 경유. 생략하면 저장된 값을 유지한다."
    )


class CarVisitResponse(BaseModel):
    success: bool
    message: str
    status: str | None = Field(None, description="처리 후 차량 상태(ready | waiting | done | null)")


class CompleteFuelingResponse(BaseModel):
    success: bool
    message: str
    next_car_num: str | None = Field(None, description="이어서 ready가 된 차량. 대기 차량이 없으면 null")


class CarItem(BaseModel):
    car_num: str
    is_line: bool
    line_num: int
    fuel_type: str | None = Field(None, description="휘발유 | 경유 | null")
    status: str | None = Field(None, description="ready(주유 준비) | waiting(대기) | done(완료) | null")
    updated_at: datetime = Field(..., description="마지막 감지 일시")
    status_updated_at: datetime | None = Field(None, description="상태 변경 일시")


class CarListResponse(BaseModel):
    success: bool
    message: str
    cars: list[CarItem] = []


class FuelTypeOrderRequest(BaseModel):
    fuel_type: FuelType = Field(..., description="휘발유 | 경유")


class BaseResponse(BaseModel):
    success: bool
    message: str


class PayRequest(BaseModel):
    fuel_type: FuelType = Field(..., description="휘발유 | 경유")
    amount: int = Field(..., gt=0, le=10_000_000, description="결제 금액(원)")


class RobotTaskResponse(BaseModel):
    success: bool
    message: str
    start: bool = Field(..., description="true면 아래 차량 주유를 시작한다")
    car_num: str | None = None
    line_num: int | None = Field(None, description="주유 라인(1 또는 2)")
    fuel_type: str | None = Field(None, description="휘발유 | 경유")
    amount: int | None = Field(None, description="결제 금액(원)")


class RobotActionCreateRequest(BaseModel):
    car_num: str = Field(..., min_length=1, max_length=20)
    line_num: Literal[1, 2]
    fuel_type: FuelType
    amount: int = Field(..., gt=0)


class RobotActionUpdateRequest(BaseModel):
    status: Literal["running", "succeeded", "failed", "canceled", "rejected"]
    step: str | None = Field(None, max_length=50, description="지금 단계 (feedback)")
    step_index: int | None = Field(None, ge=1)
    step_count: int | None = Field(None, ge=1)
    message: str | None = Field(None, max_length=255, description="결과 메시지·실패 이유")


class RobotActionItem(BaseModel):
    id: int
    car_num: str
    line_num: int
    fuel_type: str
    amount: int
    status: str = Field(..., description="requested | running | succeeded | failed | canceled | rejected")
    step: str | None
    step_index: int | None
    step_count: int | None
    message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RobotActionResponse(BaseModel):
    success: bool
    message: str
    action: RobotActionItem | None = None


class RobotActionListResponse(BaseModel):
    success: bool
    message: str
    actions: list[RobotActionItem] = []
