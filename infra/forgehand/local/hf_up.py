import sys
from huggingface_hub import HfApi
api = HfApi(token=open("/scratch/hf/token").read().strip())
repo, path = sys.argv[1], sys.argv[2]
api.create_repo(repo, private=True, exist_ok=True)
api.upload_folder(repo_id=repo, folder_path=path, ignore_patterns=["checkpoints/*", "*.bin"])
print("UPLOADED", repo)
