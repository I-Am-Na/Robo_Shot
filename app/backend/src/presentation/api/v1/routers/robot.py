import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.application.car.use_cases import GetRobotTaskUseCase
from src.application.robot_action.dto import CreateRobotActionInput, UpdateRobotActionInput
from src.application.robot_action.use_cases import (
    CreateRobotActionUseCase,
    ListRobotActionsUseCase,
    UpdateRobotActionUseCase,
)
from src.core.dependencies import (
    get_create_robot_action_use_case,
    get_list_robot_actions_use_case,
    get_robot_task_use_case,
    get_update_robot_action_use_case,
)
from src.domain.car.exceptions import CarNotFoundError
from src.domain.robot_action.exceptions import InvalidRobotActionTransition, RobotActionNotFoundError
from src.presentation.api.v1.schemas import (
    RobotActionCreateRequest,
    RobotActionItem,
    RobotActionListResponse,
    RobotActionResponse,
    RobotActionUpdateRequest,
    RobotTaskResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["robot"])


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "message": message})


@router.get("/robot/task", response_model=RobotTaskResponse)
async def get_robot_task(use_case: GetRobotTaskUseCase = Depends(get_robot_task_use_case)):
    """주유 로봇 polling용.

    결제가 끝난(paid) 차량이 있으면 start=true와 차량 정보를 준다.
    로봇은 주유를 마치면 PUT /car/{car_num}/complete 를 호출한다.
    완료 전까지는 같은 차량이 계속 내려오므로, 로봇은 이미 주유 중인 car_num이면 무시한다.
    """
    try:
        task = await use_case.execute()
    except Exception as exc:
        logger.exception("GET /robot/task failed")
        return JSONResponse(status_code=500, content={"success": False, "message": str(exc), "start": False})
    return RobotTaskResponse(
        success=True,
        message="start" if task.start else "no task",
        start=task.start,
        car_num=task.car_num,
        line_num=task.line_num,
        fuel_type=task.fuel_type.value if task.fuel_type else None,
        amount=task.amount,
    )


# --- 로봇 실행 기록 (robot_action) : 중간 연결 노드가 호출 ---

@router.post("/robot/actions", response_model=RobotActionResponse, status_code=201)
async def create_robot_action(
    body: RobotActionCreateRequest,
    use_case: CreateRobotActionUseCase = Depends(get_create_robot_action_use_case),
):
    """로봇에 주유 goal을 보낼 때 기록 생성 (status=requested). 응답의 action.id로 이후 갱신한다."""
    try:
        action = await use_case.execute(
            CreateRobotActionInput(
                car_num=body.car_num, line_num=body.line_num, fuel_type=body.fuel_type.value, amount=body.amount
            )
        )
    except CarNotFoundError as exc:
        return _error(404, str(exc))
    except Exception as exc:
        logger.exception("POST /robot/actions failed")
        return _error(500, str(exc))
    return RobotActionResponse(success=True, message="created", action=RobotActionItem(**action.model_dump()))


@router.put("/robot/actions/{action_id}", response_model=RobotActionResponse)
async def update_robot_action(
    action_id: int,
    body: RobotActionUpdateRequest,
    use_case: UpdateRobotActionUseCase = Depends(get_update_robot_action_use_case),
):
    """수락(running)·단계 진행(running + step)·결과(succeeded/failed/canceled/rejected) 기록."""
    try:
        action = await use_case.execute(action_id, UpdateRobotActionInput(**body.model_dump()))
    except RobotActionNotFoundError as exc:
        return _error(404, str(exc))
    except InvalidRobotActionTransition as exc:
        return _error(409, str(exc))
    except Exception as exc:
        logger.exception("PUT /robot/actions/%s failed", action_id)
        return _error(500, str(exc))
    return RobotActionResponse(success=True, message="updated", action=RobotActionItem(**action.model_dump()))


@router.get("/robot/actions", response_model=RobotActionListResponse)
async def list_robot_actions(
    limit: int = Query(50, ge=1, le=200),
    car_num: str | None = Query(None, description="특정 차량만"),
    use_case: ListRobotActionsUseCase = Depends(get_list_robot_actions_use_case),
):
    """로봇 실행 기록. 최근 것부터."""
    try:
        actions = await use_case.execute(limit, car_num)
    except Exception as exc:
        logger.exception("GET /robot/actions failed")
        return _error(500, str(exc))
    return RobotActionListResponse(
        success=True, message="ok", actions=[RobotActionItem(**a.model_dump()) for a in actions]
    )
