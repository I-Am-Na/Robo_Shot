from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.infrastructure.db.models import Base
from src.infrastructure.db.session import engine
from src.presentation.api.v1.routers import car, robot


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Robo Shot API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    message = "; ".join(
        f"{'.'.join(str(p) for p in err['loc'] if p != 'body')}: {err['msg']}" for err in exc.errors()
    )
    return JSONResponse(status_code=422, content={"success": False, "message": message})


app.include_router(car.router)
app.include_router(robot.router)
