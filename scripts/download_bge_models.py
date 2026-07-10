"""Download BGE-M3 and BGE-Reranker to local models/ directory."""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from common.path_utils import get_file_path


def download(repo_id: str, target: str) -> None:
    from huggingface_hub import snapshot_download

    os.makedirs(target, exist_ok=True)
    print(f"Downloading {repo_id} -> {target}")
    snapshot_download(repo_id=repo_id, local_dir=target, local_dir_use_symlinks=False)
    print(f"Done: {target}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download local BGE models")
    parser.add_argument("--embed", default="BAAI/bge-m3", help="BGE-M3 repo id")
    parser.add_argument("--rerank", default="BAAI/bge-reranker-base", help="Reranker repo id")
    parser.add_argument("--embed-dir", default=get_file_path("models/bge-m3"))
    parser.add_argument("--rerank-dir", default=get_file_path("models/bge-reranker-base"))
    args = parser.parse_args()

    download(args.embed, args.embed_dir)
    download(args.rerank, args.rerank_dir)
    print("\nSet in .env:")
    print("EMBEDDING_BACKEND=bge")
    print("RERANK_BACKEND=bge")
    print("BGE_M3_PATH=models/bge-m3")
    print("BGE_RERANKER_PATH=models/bge-reranker-base")
    print("BGE_EMBEDDING_DIMENSION=1024")
    print("MILVUS_COLLECTION_NAME=aiinfra_kb_bge")


if __name__ == "__main__":
    main()
