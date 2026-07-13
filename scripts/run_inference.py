import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INF_DIR = os.path.join(ROOT, "services", "inference")
sys.path.insert(0, ROOT)
sys.path.insert(0, INF_DIR)

if __name__ == "__main__":
    import uvicorn
    from common.config import conf

    uvicorn.run("app.main:app", host=conf.INFERENCE_HOST, port=conf.INFERENCE_PORT, reload=True,
                reload_dirs=[os.path.join(ROOT, "common"), INF_DIR])
