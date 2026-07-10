from fastapi import FastAPI


def setup_metrics(app: FastAPI) -> None:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
