import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MLOPS_DIR = os.path.join(ROOT, "services", "mlops")
sys.path.insert(0, ROOT)
sys.path.insert(0, MLOPS_DIR)

if __name__ == "__main__":
    import uvicorn
    from common.config import conf

    uvicorn.run("app.main:app", host=conf.MLOPS_HOST, port=conf.MLOPS_PORT, reload=True,
                reload_dirs=[os.path.join(ROOT, "common"), MLOPS_DIR])
