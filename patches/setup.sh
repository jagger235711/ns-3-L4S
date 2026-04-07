#!/bin/bash
root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ns3_dir="$root_dir/ns-3.46"

git clone https://gitlab.com/nsnam/ns-3-dev.git ns-3.46
cd $ns3_dir
git checkout ns-3.46

git am ../patches/l4s-implementation.patch

cp ../experiments/code.cc scratch/

./ns3 configure --enable-examples --enable-tests
./ns3 build

# ============================================
# 激活虚拟环境
if [ -f "$root_dir/venv/bin/activate" ]; then
    source "$root_dir/venv/bin/activate"
else
    log_error "虚拟环境未找到: $root_dir/venv"
    exit 1
fi

# 安装依赖 pyproject.toml
uv sync


# ./ns3 run "scratch/code --pathOut=results --RngRun=0"#单次模拟

python3 ../experiments/run-simulation.py

python3 ../experiments/create_master_dataset.py # Processing Results  处理结果

# ============================================
cd $root_dir

# 绘图
python3  ./patches/plot_results.py
