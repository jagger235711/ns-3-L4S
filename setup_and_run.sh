#!/bin/bash
set -e  # 遇到错误立即退出

# 使用说明:
# rm -rf .markers ns-3.46/exps/results 
# ./setup_and_run.sh

# ============================================
# L4S ns-3 环境自动化搭建与运行脚本
# 从代码 clone 状态到批量模拟完成
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()   { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()  { echo -e "${RED}[ERROR]${NC} $1"; }

# 步骤检测标记文件
MARKER_DIR="$SCRIPT_DIR/.markers"
mkdir -p "$MARKER_DIR"

# 检测函数
check_marker() {
    local marker="$MARKER_DIR/$1"
    if [ -f "$marker" ]; then
        return 0  # 已执行
    else
        return 1  # 未执行
    fi
}

create_marker() {
    local marker="$MARKER_DIR/$1"
    touch "$marker"
}

# ============================================
# 1. 依赖检查
# ============================================
if ! check_marker "dependencies_checked"; then
    log_info "检查系统依赖..."
    
    missing_deps=()
    
    # 检查必要工具（ccache 是可选的）
    for cmd in git python3 cmake make g++; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done
    
    # Python 虚拟环境支持（可选）
    if ! python3 -c "import venv" 2>/dev/null; then
        log_warn "python3-venv 未安装，将使用系统环境"
    fi
    
    # 检查 Python 模块
    if ! python3 -c "import pandas, numpy" 2>/dev/null; then
        missing_deps+=("python3-pandas/python3-numpy")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "缺少依赖: ${missing_deps[*]}"
        log_info "请运行: sudo apt update && sudo apt install -y ${missing_deps[*]}"
        exit 1
    fi
    
    create_marker "dependencies_checked"
    log_success "依赖检查通过"
else
    log_info "依赖检查已完成，跳过"
fi

# ============================================
# 2. 下载 ns-3.46
# ============================================
if [ ! -d "ns-3.46" ]; then
    if check_marker "ns3_downloaded"; then
        log_warn "标记显示已下载但目录不存在，重新下载..."
        rm -f "$MARKER_DIR/ns3_downloaded"
    fi
    
    log_info "下载 ns-3.46..."
    if ! check_marker "ns3_downloaded"; then
        wget https://www.nsnam.org/release/ns-3.46/ns-3.46.tar.bz2 -O ns-3.46.tar.bz2
        tar -xjf ns-3.46.tar.bz2
        rm ns-3.46.tar.bz2
        create_marker "ns3_downloaded"
        log_success "ns-3.46 下载完成"
    fi
else
    log_info "ns-3.46 目录已存在，跳过下载"
fi

# ============================================
# 3. 应用 L4S 补丁
# ============================================
cd ns-3.46

if ! git diff --quiet 2>/dev/null; then
    log_warn "ns-3.46 工作区有未提交的修改，将重置..."
    git reset --hard
    git clean -fd
fi

if ! check_marker "l4s_patched"; then
    log_info "应用 L4S 补丁..."
    
    # 检查补丁文件
    PATCH_FILE="$SCRIPT_DIR/patches/l4s-implementation.patch"
    if [ ! -f "$PATCH_FILE" ]; then
        log_error "补丁文件不存在: $PATCH_FILE"
        exit 1
    fi
    
    # 应用补丁
    if git apply --check "$PATCH_FILE" 2>/dev/null; then
        git apply "$PATCH_FILE"
        create_marker "l4s_patched"
        log_success "L4S 补丁应用完成"
    else
        log_error "补丁应用失败，请检查补丁兼容性"
        exit 1
    fi
else
    log_info "L4S 补丁已应用，跳过"
fi

# ============================================
# 4. 复制实验代码
# ============================================
if ! check_marker "code_copied"; then
    log_info "复制实验代码..."
    
    # 复制 scratch 目录下的代码
    if [ -d "$SCRIPT_DIR/experiments" ]; then
        cp -r "$SCRIPT_DIR/experiments"/* scratch/ 2>/dev/null || true
        
        # 确保代码文件存在
        if [ ! -f "scratch/code.cc" ]; then
            log_error "实验代码未找到，请检查 experiments/code.cc"
            exit 1
        fi
        
        create_marker "code_copied"
        log_success "实验代码复制完成"
    else
        log_warn "experiments 目录不存在，跳过复制"
    fi
else
    log_info "实验代码已复制，跳过"
fi

cd "$SCRIPT_DIR"

# ============================================
# 5. 配置 ns-3
# ============================================
cd ns-3.46

if ! check_marker "ns3_configured"; then
    log_info "配置 ns-3（首次配置可能需要几分钟）..."
    
    # 检查是否已经构建过
    if [ -d "build" ]; then
        log_warn "检测到已存在的构建目录，将重新配置..."
        rm -rf build
    fi
    
    # 配置
    ./ns3 configure --enable-examples --enable-tests
    
    create_marker "ns3_configured"
    log_success "ns-3 配置完成"
else
    log_info "ns-3 已配置，跳过"
fi

# ============================================
# 6. 构建 ns-3
# ============================================
if ! check_marker "ns3_built"; then
    log_info "构建 ns-3（这可能需要 15-30 分钟）..."
    
    # 检查是否已经构建完成
    if [ -f "build/ns-3.46/.libs/libns3.46-dpdk.so" ] || [ -f "build/libns3.46-dpdk.so" ]; then
        log_info "检测到已构建的库文件，跳过构建"
        create_marker "ns3_built"
    else
        # 使用 ccache 加速重新构建
        if command -v ccache &> /dev/null; then
            export CC="ccache gcc"
            export CXX="ccache g++"
        fi
        
        ./ns3 build
        
        create_marker "ns3_built"
        log_success "ns-3 构建完成"
    fi
else
    log_info "ns-3 已构建，跳过"
fi

# ============================================
# 7. 创建 Python 虚拟环境
# ============================================
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    if check_marker "venv_created"; then
        rm -f "$MARKER_DIR/venv_created"
    fi
    
    if ! check_marker "venv_created"; then
        log_info "创建 Python 虚拟环境..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install pandas numpy matplotlib
        create_marker "venv_created"
        log_success "虚拟环境创建完成"
    fi
else
    log_info "虚拟环境已存在，跳过创建"
fi

# ============================================
# 8. 运行单次模拟验证
# ============================================
cd ns-3.46

if ! check_marker "test_run_completed"; then
    log_info "运行单次模拟验证环境（60 秒）..."
    
    # 检查之前的测试输出
    if [ -d "exps/results/run_0" ]; then
        log_warn "检测到已存在的测试输出，跳过单次模拟"
        create_marker "test_run_completed"
    else
        ./ns3 run "scratch/code --pathOut=exps/results/run_0 --RngRun=0"
        
        if [ $? -eq 0 ] && [ -d "exps/results/run_0" ]; then
            create_marker "test_run_completed"
            log_success "单次模拟验证通过"
        else
            log_error "单次模拟失败"
            exit 1
        fi
    fi
else
    log_info "单次模拟已验证，跳过"
fi

# ============================================
# 9. 批量模拟（30次）
# ============================================
cd "$SCRIPT_DIR/ns-3.46"

if ! check_marker "batch_run_completed"; then
    log_info "开始批量模拟（30次，预计 5-10 分钟）..."
    
    # 检查是否已部分完成
    existing_runs=$(find exps/results -type d -name "run_[0-9]*" 2>/dev/null | wc -l)
    if [ "$existing_runs" -ge 30 ]; then
        log_warn "检测到 30 个模拟输出目录，跳过批量模拟"
        create_marker "batch_run_completed"
    else
        source "$SCRIPT_DIR/.venv/bin/activate"
        
        # 运行批量模拟
        python3 "$SCRIPT_DIR/experiments/run-simulation.py"
        
        # 验证结果
        completed_runs=$(find exps/results -type d -name "run_[0-9]*" 2>/dev/null | wc -l)
        if [ "$completed_runs" -eq 30 ]; then
            create_marker "batch_run_completed"
            log_success "批量模拟完成（$completed_runs/30）"
        else
            log_warn "批量模拟部分完成（$completed_runs/30），可能需要重新运行"
            # 不标记为完成，允许重新运行
        fi
    fi
else
    log_info "批量模拟已完成，跳过"
fi

# ============================================
# 10. 处理结果数据
# ============================================
cd "$SCRIPT_DIR/ns-3.46"

if ! check_marker "data_processed"; then
    log_info "处理结果数据..."
    
    source "$SCRIPT_DIR/.venv/bin/activate"
    python3 "$SCRIPT_DIR/experiments/create_master_dataset.py"
    
    # 检查输出文件
    if [ -f "exps/results/metrics/throughput_prague.csv" ]; then
        create_marker "data_processed"
        log_success "数据处理完成"
    else
        log_error "数据处理失败，未找到输出文件"
        exit 1
    fi
else
    log_info "结果数据处理已完成，跳过"
fi

# ============================================
# 11. 生成图表
# ============================================
cd "$SCRIPT_DIR/ns-3.46"

if ! check_marker "plots_generated"; then
    log_info "生成图表..."
    
    source "$SCRIPT_DIR/.venv/bin/activate"
    cd exps/results
    MPLBACKEND=Agg python3 plot_results.py
    
    # 检查图表文件
    if [ -f "plots/combined_results.png" ]; then
        create_marker "plots_generated"
        log_success "图表生成完成"
    else
        log_error "图表生成失败"
        exit 1
    fi
else
    log_info "图表已生成，跳过"
fi

# ============================================
# 完成总结
# ============================================
log_success "=========================================="
log_success "所有步骤已完成！"
log_success "=========================================="
log_info "结果位置:"
log_info "  - 原始数据: ns-3.46/exps/results/run_0...run_29"
log_info "  - 处理数据: ns-3.46/exps/results/metrics/"
log_info "  - 图表文件: ns-3.46/exps/results/plots/"
log_info ""
log_info "查看组合图:"
log_info "  xdg-open ns-3.46/exps/results/plots/combined_results.png"
log_info ""
log_info "如需重新运行，删除标记文件:"
log_info "  rm -rf .markers/"
log_success "=========================================="