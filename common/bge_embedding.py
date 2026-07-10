from common.config import conf
from common.logger import my_logger

_model = None


def _resolve_model_path() -> str:
    path = conf.BGE_M3_PATH
    if not path:
        raise ValueError("BGE_M3_PATH is not configured")
    if conf.model_dir_ready(path):
        return conf.resolve_path(path)
    return path


def get_bge_embedding_model():
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel

        model_path = _resolve_model_path()
        my_logger.info("Loading BGE-M3 from %s device=%s", model_path, conf.BGE_DEVICE)
        _model = BGEM3FlagModel(
            model_path,
            use_fp16=conf.BGE_USE_FP16,
            device=conf.BGE_DEVICE,
        )
    return _model


def encode_dense(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_bge_embedding_model()
    output = model.encode(
        texts,
        batch_size=conf.BGE_BATCH_SIZE,
        max_length=8192,
    )
    vectors = output["dense_vecs"]
    my_logger.info("BGE-M3 embedded %s texts", len(texts))
    return [vec.tolist() if hasattr(vec, "tolist") else list(vec) for vec in vectors]


def warmup() -> None:
    encode_dense(["warmup"])
