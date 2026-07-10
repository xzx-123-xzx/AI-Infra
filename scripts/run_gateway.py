import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_DIR = os.path.join(ROOT, "services", "gateway")

sys.path.insert(0, ROOT)
sys.path.insert(0, GATEWAY_DIR)

if __name__ == "__main__":
    import uvicorn

    from common.config import conf

    uvicorn.run(
        "app.main:app",
        host=conf.GATEWAY_HOST,
        port=conf.GATEWAY_PORT,
        reload=True,
        reload_dirs=[os.path.join(ROOT, "common"), GATEWAY_DIR],
    )
