import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAG_DIR = os.path.join(ROOT, "services", "rag")

sys.path.insert(0, ROOT)
sys.path.insert(0, RAG_DIR)

if __name__ == "__main__":
    import uvicorn

    from common.config import conf

    uvicorn.run(
        "app.main:app",
        host=conf.RAG_HOST,
        port=conf.RAG_PORT,
        reload=True,
        reload_dirs=[os.path.join(ROOT, "common"), RAG_DIR],
    )
