#!/usr/bin/env python3
"""
L4S Simulation Results - Interactive Plotting Script
在 VSCode 中使用 #%% 可以分节运行，类似 Jupyter notebook
"""

# %% 导入依赖
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# %% 配置

# 基于项目根目录设置路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # patches 的父目录就是项目根目录
METRICS_DIR = os.path.join(PROJECT_ROOT, "ns-3.46", "exps", "results", "metrics")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "ns-3.46", "exps", "results", "plots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 颜色方案
PRAGUE_COLOR = "#0D0887"  # 深蓝
CUBIC_COLOR = "#FCA636"   # 橙色
L4S_COLOR = "#22a884"     # 青色

# %% 数据加载和聚合函数
def load_and_aggregate(filename, value_col, time_round=1):
    """加载CSV并计算均值和置信区间"""
    filepath = os.path.join(METRICS_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found")
        return None
    
    df = pd.read_csv(filepath)
    df['time'] = df['time'].round(time_round)
    
    # 按时间分组并计算统计量
    grouped = df.groupby('time')[value_col].agg(['mean', 'std', 'count'])
    grouped = grouped.reset_index()
    grouped['ci'] = 1.96 * grouped['std'] / np.sqrt(grouped['count'])
    grouped['ciLow'] = grouped['mean'] - grouped['ci']
    grouped['ciUp'] = grouped['mean'] + grouped['ci']
    
    return grouped

# %% 加载所有数据
print("Loading data...")
prague_thr = load_and_aggregate('throughput_prague.csv', 'throughput_prague')
cubic_thr = load_and_aggregate('throughput_cubic.csv', 'throughput_cubic')
prague_rtt = load_and_aggregate('prague_rtt.csv', 'prague_rtt')
cubic_rtt = load_and_aggregate('cubic_rtt.csv', 'cubic_rtt')
prague_cwnd = load_and_aggregate('prague_cwnd.csv', 'prague_cwnd')
cubic_cwnd = load_and_aggregate('cubic_cwnd.csv', 'cubic_cwnd')
l4s_qdelay = load_and_aggregate('queue_sojourn_l4s.csv', 'queue_sojourn_l4s')
classic_qdelay = load_and_aggregate('queue_sojourn_classic.csv', 'queue_sojourn_classic')
marks = load_and_aggregate('count_mark_l4s.csv', 'count_mark_l4s', time_round=0)
prob = load_and_aggregate('queue_prob_coupled.csv', 'queue_prob_coupled')
print("Data loaded successfully!")

# %% 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

# %% 1. 吞吐量图 (Throughput)
fig, ax = plt.subplots(figsize=(10, 4))

if prague_thr is not None:
    ax.plot(prague_thr['time'], prague_thr['mean'], color=PRAGUE_COLOR, label='Prague', linewidth=1.5)
    ax.fill_between(prague_thr['time'], prague_thr['ciLow'], prague_thr['ciUp'], 
                    color=PRAGUE_COLOR, alpha=0.2)

if cubic_thr is not None:
    ax.plot(cubic_thr['time'], cubic_thr['mean'], color=CUBIC_COLOR, label='Cubic', linewidth=1.5)
    ax.fill_between(cubic_thr['time'], cubic_thr['ciLow'], cubic_thr['ciUp'], 
                    color=CUBIC_COLOR, alpha=0.2)

ax.set_ylim(0, 12)
ax.set_xlim(0, 60)
ax.set_ylabel('Throughput (Mbps)')
ax.set_title('Throughput Comparison')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'throughput.png'), dpi=150)
print(f"Saved throughput.png")
plt.show()

# %% 2. RTT 图
fig, ax = plt.subplots(figsize=(10, 4))

if prague_rtt is not None:
    ax.plot(prague_rtt['time'], prague_rtt['mean'] * 1000, color=PRAGUE_COLOR, label='Prague', linewidth=1.5)
    ax.fill_between(prague_rtt['time'], prague_rtt['ciLow'] * 1000, prague_rtt['ciUp'] * 1000, 
                    color=PRAGUE_COLOR, alpha=0.2)

if cubic_rtt is not None:
    ax.plot(cubic_rtt['time'], cubic_rtt['mean'] * 1000, color=CUBIC_COLOR, label='Cubic', linewidth=1.5)
    ax.fill_between(cubic_rtt['time'], cubic_rtt['ciLow'] * 1000, cubic_rtt['ciUp'] * 1000, 
                    color=CUBIC_COLOR, alpha=0.2)

ax.set_ylim(0, 40)
ax.set_xlim(0, 60)
ax.set_ylabel('RTT (ms)')
ax.set_xlabel('Time (s)')
ax.set_title('RTT Comparison')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'rtt.png'), dpi=150)
print(f"Saved rtt.png")
plt.show()

# %% 3. 拥塞窗口图 (CWnd)
fig, ax = plt.subplots(figsize=(10, 4))

if prague_cwnd is not None:
    ax.plot(prague_cwnd['time'], prague_cwnd['mean'] / 1024, color=PRAGUE_COLOR, label='Prague', linewidth=1.5)
    ax.fill_between(prague_cwnd['time'], prague_cwnd['ciLow'] / 1024, prague_cwnd['ciUp'] / 1024, 
                    color=PRAGUE_COLOR, alpha=0.2)

if cubic_cwnd is not None:
    ax.plot(cubic_cwnd['time'], cubic_cwnd['mean'] / 1024, color=CUBIC_COLOR, label='Cubic', linewidth=1.5)
    ax.fill_between(cubic_cwnd['time'], cubic_cwnd['ciLow'] / 1024, cubic_cwnd['ciUp'] / 1024, 
                    color=CUBIC_COLOR, alpha=0.2)

ax.set_ylim(0, 200)
ax.set_xlim(0, 60)
ax.set_ylabel('CWnd (KiB)')
ax.set_title('Congestion Window Comparison')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'cwnd.png'), dpi=150)
print(f"Saved cwnd.png")
plt.show()

# %% 4. 队列延迟图 (Queue Delay)
fig, ax = plt.subplots(figsize=(10, 4))

if l4s_qdelay is not None:
    ax.plot(l4s_qdelay['time'], l4s_qdelay['mean'] * 1000, color=PRAGUE_COLOR, label='L4S Queue', linewidth=1.5)
    ax.fill_between(l4s_qdelay['time'], l4s_qdelay['ciLow'] * 1000, l4s_qdelay['ciUp'] * 1000, 
                    color=PRAGUE_COLOR, alpha=0.2)

if classic_qdelay is not None:
    ax.plot(classic_qdelay['time'], classic_qdelay['mean'] * 1000, color=CUBIC_COLOR, label='Classic Queue', linewidth=1.5)
    ax.fill_between(classic_qdelay['time'], classic_qdelay['ciLow'] * 1000, classic_qdelay['ciUp'] * 1000, 
                    color=CUBIC_COLOR, alpha=0.2)

ax.set_ylim(0, 30)
ax.set_xlim(0, 60)
ax.set_ylabel('Queue Delay (ms)')
ax.set_xlabel('Time (s)')
ax.set_title('Queue Sojourn Time')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'queue_delay.png'), dpi=150)
print(f"Saved queue_delay.png")
plt.show()

# %% 5. ECN 标记图
fig, ax = plt.subplots(figsize=(10, 4))

if marks is not None:
    ax.plot(marks['time'], marks['mean'], color=L4S_COLOR, linewidth=1.5)
    ax.fill_between(marks['time'], marks['ciLow'], marks['ciUp'], 
                    color=L4S_COLOR, alpha=0.2)

ax.set_ylim(0, 250)
ax.set_xlim(0, 60)
ax.set_ylabel('ECN Marks (pkts/s)')
ax.set_xlabel('Time (s)')
ax.set_title('L4S ECN Marks')
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'ecn_marks.png'), dpi=150)
print(f"Saved ecn_marks.png")
plt.show()

# %% 6. 标记概率图
fig, ax = plt.subplots(figsize=(10, 4))

if prob is not None:
    ax.plot(prob['time'], prob['mean'] / 2, color=L4S_COLOR, linewidth=1.5)
    ax.fill_between(prob['time'], prob['ciLow'] / 2, prob['ciUp'] / 2, 
                    color=L4S_COLOR, alpha=0.2)

ax.set_ylim(0, 0.05)
ax.set_xlim(0, 60)
ax.set_ylabel('Mark Probability')
ax.set_xlabel('Time (s)')
ax.set_title('Coupled Mark Probability')
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'mark_probability.png'), dpi=150)
print(f"Saved mark_probability.png")
plt.show()

# %% 7. 组合图 - 所有指标在一个图中
fig, axes = plt.subplots(3, 2, figsize=(16, 14))
fig.suptitle('L4S Simulation Results (ns-3) - 30 runs', fontsize=16, fontweight='bold')

# Throughput
ax = axes[0, 0]
if prague_thr is not None:
    ax.plot(prague_thr['time'], prague_thr['mean'], color=PRAGUE_COLOR, label='Prague')
if cubic_thr is not None:
    ax.plot(cubic_thr['time'], cubic_thr['mean'], color=CUBIC_COLOR, label='Cubic')
ax.set_ylabel('Throughput (Mbps)')
ax.set_title('Throughput')
ax.legend()
ax.grid(True, alpha=0.3)

# RTT
ax = axes[0, 1]
if prague_rtt is not None:
    ax.plot(prague_rtt['time'], prague_rtt['mean'] * 1000, color=PRAGUE_COLOR, label='Prague')
if cubic_rtt is not None:
    ax.plot(cubic_rtt['time'], cubic_rtt['mean'] * 1000, color=CUBIC_COLOR, label='Cubic')
ax.set_ylabel('RTT (ms)')
ax.set_title('RTT')
ax.legend()
ax.grid(True, alpha=0.3)

# CWnd
ax = axes[1, 0]
if prague_cwnd is not None:
    ax.plot(prague_cwnd['time'], prague_cwnd['mean'] / 1024, color=PRAGUE_COLOR, label='Prague')
if cubic_cwnd is not None:
    ax.plot(cubic_cwnd['time'], cubic_cwnd['mean'] / 1024, color=CUBIC_COLOR, label='Cubic')
ax.set_ylabel('CWnd (KiB)')
ax.set_title('Congestion Window')
ax.legend()
ax.grid(True, alpha=0.3)

# Queue Delay
ax = axes[1, 1]
if l4s_qdelay is not None:
    ax.plot(l4s_qdelay['time'], l4s_qdelay['mean'] * 1000, color=PRAGUE_COLOR, label='L4S')
if classic_qdelay is not None:
    ax.plot(classic_qdelay['time'], classic_qdelay['mean'] * 1000, color=CUBIC_COLOR, label='Classic')
ax.set_ylabel('Queue Delay (ms)')
ax.set_title('Queue Sojourn Time')
ax.legend()
ax.grid(True, alpha=0.3)

# ECN Marks
ax = axes[2, 0]
if marks is not None:
    ax.plot(marks['time'], marks['mean'], color=L4S_COLOR)
ax.set_ylabel('ECN Marks (pkts/s)')
ax.set_xlabel('Time (s)')
ax.set_title('L4S ECN Marks')
ax.grid(True, alpha=0.3)

# Mark Probability
ax = axes[2, 1]
if prob is not None:
    ax.plot(prob['time'], prob['mean'] / 2, color=L4S_COLOR)
ax.set_ylabel('Mark Probability')
ax.set_xlabel('Time (s)')
ax.set_title('Coupled Mark Probability')
ax.grid(True, alpha=0.3)

fig.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'combined_results.png'), dpi=150)
fig.savefig(os.path.join(OUTPUT_DIR, 'combined_results.pdf'))
print(f"Saved combined_results.png and combined_results.pdf")
plt.show()

# %% 打印统计摘要
print("\n" + "="*60)
print("统计摘要 (Statistics Summary)")
print("="*60)

if prague_thr is not None:
    print(f"\nPrague Throughput: mean={prague_thr['mean'].mean():.2f} Mbps")
if cubic_thr is not None:
    print(f"Cubic Throughput:  mean={cubic_thr['mean'].mean():.2f} Mbps")
if prague_rtt is not None:
    print(f"\nPrague RTT:        mean={prague_rtt['mean'].mean()*1000:.2f} ms")
if cubic_rtt is not None:
    print(f"Cubic RTT:         mean={cubic_rtt['mean'].mean()*1000:.2f} ms")
if l4s_qdelay is not None:
    print(f"\nL4S Queue Delay:   mean={l4s_qdelay['mean'].mean()*1000:.2f} ms")
if classic_qdelay is not None:
    print(f"Classic Queue Delay: mean={classic_qdelay['mean'].mean()*1000:.2f} ms")

print("\n" + "="*60)
print(f"所有图表已保存到: {os.path.abspath(OUTPUT_DIR)}")
print("="*60)