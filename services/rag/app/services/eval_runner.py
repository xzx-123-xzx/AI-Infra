"""评测集批量运行与指标对比。"""

from __future__ import annotations

import json
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models import EvalDataset, EvalRun
from app.services.rag_chain import chat_with_kb
from common.logger import my_logger


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip(), b.strip()).ratio()


async def run_eval(db: Session, run: EvalRun) -> EvalRun:
    dataset = db.query(EvalDataset).filter(EvalDataset.id == run.dataset_id).first()
    if dataset is None:
        raise ValueError("Dataset not found")

    items = json.loads(dataset.items) if isinstance(dataset.items, str) else dataset.items
    config = json.loads(run.config) if isinstance(run.config, str) else run.config
    kb_id = config.get("kb_id")
    if not kb_id:
        raise ValueError("config.kb_id required")

    run.status = "running"
    db.commit()

    results = []
    scores = []
    try:
        for i, item in enumerate(items):
            query = item.get("query") or item.get("question", "")
            expected = item.get("expected") or item.get("answer", "")
            resp = await chat_with_kb(
                int(kb_id),
                query,
                top_k=config.get("top_k"),
                db=db,
                prompt_template_id=config.get("prompt_template_id"),
                tenant_id=config.get("tenant_id", "default"),
            )
            answer = resp.get("answer", "")
            score = _similarity(answer, expected) if expected else 1.0
            scores.append(score)
            results.append(
                {
                    "index": i,
                    "query": query,
                    "expected": expected,
                    "answer": answer,
                    "score": round(score, 4),
                    "source_count": len(resp.get("sources") or []),
                }
            )

        metrics = {
            "count": len(results),
            "avg_similarity": round(sum(scores) / max(len(scores), 1), 4),
            "pass_rate": round(sum(1 for s in scores if s >= 0.6) / max(len(scores), 1), 4),
        }
        run.results = json.dumps(results, ensure_ascii=False)
        run.metrics = json.dumps(metrics)
        run.status = "completed"
        my_logger.info("Eval run completed: id=%s avg=%s", run.id, metrics["avg_similarity"])
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)[:1000]
        my_logger.exception("Eval run failed: id=%s", run.id)
    finally:
        db.commit()
        db.refresh(run)
    return run


def compare_runs(run_a: EvalRun, run_b: EvalRun) -> dict:
    ma = json.loads(run_a.metrics or "{}")
    mb = json.loads(run_b.metrics or "{}")
    return {
        "run_a": {"id": run_a.id, "name": run_a.name, "metrics": ma},
        "run_b": {"id": run_b.id, "name": run_b.name, "metrics": mb},
        "delta": {
            "avg_similarity": round(float(mb.get("avg_similarity", 0)) - float(ma.get("avg_similarity", 0)), 4),
            "pass_rate": round(float(mb.get("pass_rate", 0)) - float(ma.get("pass_rate", 0)), 4),
        },
    }
