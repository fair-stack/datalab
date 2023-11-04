# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:main
@time:2022/06/27
"""
import sys
import aioredis
sys.path.append('..')


import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.middlewares import BearerTokenAuthBackend, on_token_auth_error, PermissionAuthMiddleware
from app.api.api import api_router
from app.core.config import settings
from app.db.mongo_util import connect_mongodb, disconnect_mongodb


app = FastAPI(title=settings.PROJECT_NAME)


# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# global db connection
# app.add_event_handler("startup", connect_mongodb)
# app.add_event_handler("shutdown", disconnect_mongodb)

@app.on_event("startup")
async def startup():
    connect_mongodb()
    app.state.use_storage_cumulative = await aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                                                            db=settings.USED_STORAGE_CUMULATIVE_DB,
                                                            encoding="utf-8")
    app.state.file_cache = await aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                                                db=settings.FILE_CACHE_DB,
                                                encoding="utf-8", decode_responses=True)
    app.state.task_publisher = await aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                                                    db=settings.TASK_PUBLISHER_DB,
                                                    encoding="utf-8", decode_responses=True)
    app.state.file_upload = await aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                                                    db=7,
                                                    encoding="utf-8", decode_responses=True)
    app.state.objects_storage = await aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                                                 db=2 )


@app.on_event('shutdown')
async def shutdown():
    disconnect_mongodb()
    await app.state.use_storage_cumulative.wait_closed()
    await app.state.file_cache.wait_closed()
    await app.state.task_publisher.wait_closed()
    await app.state.objects_storage.wait_closed()


# permit middleware
# Middleware execution order：Reverse order，Therefore, the PermissionAuthMiddleware In front of
# app.add_middleware(PermissionAuthMiddleware)


# auth login middleware
app.add_middleware(AuthenticationMiddleware,
                   backend=BearerTokenAuthBackend(),
                   on_error=on_token_auth_error)


# include all relevant routers
# app.mount('/static', StaticFiles(directory='/home/datalab/static/swagger-ui'), name='static')
app.include_router(api_router, prefix=settings.API_STR)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
