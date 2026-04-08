#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# ========================== 配置区（完全匹配你的真实目录） ==========================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."                          # 项目根目录
NS3_DIR="${PROJECT_DIR}/ns-3.46"                        # ns-3 源码目录
PATCH_FILE="${SCRIPT_DIR}/l4s-implementation.patch"     # 补丁文件（在 patches/ 内）
CODE_FILE="${PROJECT_DIR}/experiments/code.cc"           # 仿真代码
VENV_DIR="${PROJECT_DIR}/.venv"                          # 你的是 .venv 不是 venv！

# 清理历史结果（安全）
CLEAN_DIRS=(
    # "${PROJECT_DIR}/results"
    # "${PROJECT_DIR}/output"
    # "${PROJECT_DIR}/logs"
    # "${NS3_DIR}/results"
    # "${NS3_DIR}/output"
    "${NS3_DIR}/exps"
)
# ==================================================================================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO] $*${NC}"; }
warn()    { echo -e "${YELLOW}[WARN] $*${NC}"; }
error()   { echo -e "${RED}[ERROR] $*${NC}"; exit 1; }

# ========================== 顶部清理历史结果 ==========================
info "=== 清理旧结果，保证全新运行 ==="
for dir in "${CLEAN_DIRS[@]}"; do
    if [[ -d "${dir}" ]]; then
        warn "删除：${dir}"
        rm -rf "${dir}"
    fi
done

# ========================== 主流程（完全按你的目录） ==========================
info "=== 开始 L4S 仿真自动化流程 ==="

# 克隆 ns-3（不存在才克隆）
if [[ ! -d "${NS3_DIR}" ]]; then
    info "克隆 ns-3.46 ..."
    git clone https://gitlab.com/nsnam/ns-3-dev.git ns-3.46
fi

cd "${NS3_DIR}" || error "无法进入 ns-3.46"
git checkout ns-3.46

# 打补丁
[[ -f "${PATCH_FILE}" ]] || error "补丁不存在：${PATCH_FILE}"
info "应用补丁"
git am "${PATCH_FILE}" || error "补丁应用失败"

# 复制仿真代码
[[ -f "${CODE_FILE}" ]] || error "仿真代码不存在：${CODE_FILE}"
info "复制 code.cc 到 scratch"
cp -f "${CODE_FILE}" scratch/

# 编译
info "配置 ns-3"
./ns3 configure --enable-examples --enable-tests

info "编译 ns-3"
./ns3 build

info "单次运行仿真（RngRun=0）"
./ns3 run "scratch/code --pathOut=results --RngRun=0"

# # 激活虚拟环境（你的是 .venv）
# info "激活 Python 虚拟环境 .venv"
# if [[ -f "${VENV_DIR}/bin/activate" ]]; then
#     source "${VENV_DIR}/bin/activate"
# else
#     error "虚拟环境未找到：${VENV_DIR}"
# fi

# # 安装依赖（在项目根目录执行 uv sync）
# cd "${PROJECT_DIR}" || exit 1
# info "安装 Python 依赖"
# uv sync

# # 运行仿真
# cd "${NS3_DIR}" || exit 1
# info "运行仿真"
# python3 "${PROJECT_DIR}/experiments/run-simulation.py"

# info "生成数据集"
# python3 "${PROJECT_DIR}/experiments/create_master_dataset.py"

# # 绘图（plot_results.py 在 patches/ 目录内）
# info "绘制结果图"
# python3 "${SCRIPT_DIR}/plot_results.py"

info "=== 全部执行完成！ ==="