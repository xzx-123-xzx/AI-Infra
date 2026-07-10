from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import conf


def setup_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=conf.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
