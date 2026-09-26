#!/bin/bash
# Local-disk setup on the Forgehand box while /workspace and /team NFS refuse access.
set -x
export HOME=/scratch/home; mkdir -p $HOME /scratch/work /scratch/hf
cd /scratch && rm -rf repo && mkdir repo && tar -xzf repo.tgz -C repo
export PATH=/opt/forgehand/bin:$PATH UV_CACHE_DIR=/scratch/uvcache
VENV=/scratch/work/venv-py312
[ -x $VENV/bin/python ] || uv venv -q -p 3.12 --seed $VENV
VIRTUAL_ENV=$VENV uv pip install -q "vllm==0.27.1" bitsandbytes hf_transfer pyyaml matplotlib pymupdf trl peft datasets accelerate huggingface_hub
VIRTUAL_ENV=$VENV uv pip install -q -e /scratch/repo
$VENV/bin/python -c "import vllm,torch,peft,trl;print('VENV_OK',vllm.__version__,torch.__version__)"
# llama-server wrapper with the CUDA libs from the pip nvidia wheels
mkdir -p /scratch/work/llama.cpp/build/bin
LIBS=$(ls -d $VENV/lib/python3.12/site-packages/nvidia/*/lib | tr '\n' ':')
cat > /scratch/work/llama.cpp/build/bin/llama-server <<W
#!/bin/bash
export LD_LIBRARY_PATH=/scratch/llama-build/bin:$LIBS\${LD_LIBRARY_PATH:-}
exec /scratch/llama-build/bin/llama-server "\$@"
W
chmod +x /scratch/work/llama.cpp/build/bin/llama-server
/scratch/work/llama.cpp/build/bin/llama-server --version && echo LLAMA_OK
echo SETUP_DONE
