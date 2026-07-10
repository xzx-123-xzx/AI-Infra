from common.config import conf
from common.logger import my_logger

_reranker = None


def _resolve_model_path() -> str:
    path = conf.BGE_RERANKER_PATH
    if not path:
        raise ValueError("BGE_RERANKER_PATH is not configured")
    if conf.model_dir_ready(path):
        return conf.resolve_path(path)
    return path


def get_bge_reranker():
    global _reranker
    if _reranker is None:
        from FlagEmbedding import FlagReranker

        model_path = _resolve_model_path()
        my_logger.info("Loading BGE Reranker from %s device=%s", model_path, conf.BGE_DEVICE)
        _reranker = FlagReranker(
            model_path,
            use_fp16=conf.BGE_USE_FP16,
            device=conf.BGE_DEVICE,
        )
    return _reranker


def rerank_pairs(query: str, passages: list[str]) -> list[float]:
    if not passages:
        return []
    reranker = get_bge_reranker()
    pairs = [[query, passage] for passage in passages]
    scores = reranker.compute_score(pairs, batch_size=conf.BGE_RERANK_BATCH_SIZE, normalize=True)
    if isinstance(scores, (int, float)):
        return [float(scores)]
    return [float(score) for score in scores]


def warmup() -> None:
    rerank_pairs("warmup", ["warmup passage"])
