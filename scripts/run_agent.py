import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(ROOT, "services", "agent")
sys.path.insert(0, ROOT)
sys.path.insert(0, AGENT_DIR)

if __name__ == "__main__":
    import uvicorn
    from common.config import conf

    uvicorn.run("app.main:app", host=conf.AGENT_HOST, port=conf.AGENT_PORT, reload=True,
                reload_dirs=[os.path.join(ROOT, "common"), AGENT_DIR])
