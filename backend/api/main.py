import asyncio
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from fastapi_pagination import add_pagination
from slowapi import _rate_limit_exceeded_handler

from api.repository.init_db import create_tables, create_schema
from api.routes.heroes import heroes_router
from api.routes.military_ranks import military_ranks_router
from api.routes.wars import wars_router
from api.utilities.exceptions_storage import (
    HeroNotFound,
    WarNotFound,
    MilitaryRankNotFound,
    HeroOnModeration,
    InvalidFileType,
    FIleToBig,
    FileNotFound,
    ImageCorrupted
)
from api.storage.local import FileManager
from api.triggers.triggers import setup_hero_delete_trigger, setup_hero_insert_trigger
from api.triggers.listeners import setup_user_delete_listener, setup_user_insert_listener
from api.utilities.data_importer import DataImporter
from api.limiter.limiter import limiter


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_schema()
    await create_tables()
    await setup_hero_delete_trigger()
    await setup_hero_insert_trigger()
    asyncio.create_task(setup_user_delete_listener())
    asyncio.create_task(setup_user_insert_listener())
    FileManager.create_folders_structure()
    await DataImporter.import_wars()
    await DataImporter.import_military_ranks()
    yield


app = FastAPI(
    title="OpenContent API",
    description="Free API for any informational resources",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def exception_handler(request, exc: Exception) -> JSONResponse:
    match exc:
        case HeroNotFound():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": str(exc)}
            )
        case HeroOnModeration():
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": str(exc)}
            )
        case WarNotFound():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": str(exc)}
            )
        case MilitaryRankNotFound():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": str(exc)}
            )
        case InvalidFileType():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(exc)},
            )
        case FIleToBig():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(exc)},
            )
        case ImageCorrupted():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(exc)},
            )
        case FileNotFound():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": str(exc)}
            )

app.include_router(heroes_router)
app.include_router(military_ranks_router)
app.include_router(wars_router)

add_pagination(app)
