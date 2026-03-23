# l4s-for-ns3
Implementation of L4S protocols (TCP Prague CCA and DualPI2 AQM) for the ns-3 simulator.

In this repository we provide patches to add L4S-related codes for ns-3, including:
- Accurate ECN to the ns-3 TCP infrastructure
- TCP Prague as a TCP congestion control option
- A DualPI2 AQM as a traffic-control qdisc option (currently WIP)

## Repository Structure

```
l4s-for-ns3/
├── patches/
│   └── l4s-implementation.patch    # Complete L4S patch for ns-3.46
├── experiments/
│   ├── code.cc                     # Network simulation topology
│   ├── run-simulation.py           # Automated batch execution script
│   ├── create_plots.ipynb          # Jupyter notebook (R kernel) used to plot the results from our first preprint
│   └── create_master_dataset.py    # Results consolidation script
└── README.md
```

## Requirements

- ns-3.46 (downloaded from [nsnam.org](https://www.nsnam.org/) or GitLab)
- Python 3.x with pandas and numpy
- CMake 3.10+
- C++17 compatible compiler (GCC 9+, Clang 10+)

## Installation

### 1. Clone ns-3.46

```bash
git clone https://gitlab.com/nsnam/ns-3-dev.git ns-3.46
cd ns-3.46
git checkout ns-3.46
```

### 2. Apply the L4S patch

```bash
git am /path/to/l4s-for-ns3/patches/l4s-implementation.patch
```

This will apply three commits:
- DualQ Coupled PI Square queue disc implementation
- Accurate ECN support for TCP
- TCP Prague congestion control

### 3. Copy the simulation code

```bash
cp /path/to/l4s-for-ns3/experiments/code.cc scratch/
```

### 4. Configure and build ns-3

```bash
./ns3 configure --enable-examples --enable-tests
./ns3 build
```

## Running Simulations

### Single Simulation

To run a single simulation:

```bash
./ns3 run "scratch/code --pathOut=results --RngRun=0"
```

### Batch Execution

To run multiple simulations with different random seeds:

```bash
cd /path/to/ns-3.46
python3 /path/to/l4s-for-ns3/experiments/run-simulation.py
```

This will:
- Run 30 simulations (configurable via `NUM_RUNS`)
- Save results to `exps/results/run_X/`
- Skip already completed runs

### Processing Results

After simulations complete, consolidate the data:

```bash
python3 /path/to/l4s-for-ns3/experiments/create_master_dataset.py
```

This generates consolidated CSV files in `exps/results/metrics/`:
- `throughput_prague.csv`, `throughput_cubic.csv`
- `prague_cwnd.csv`, `prague_rtt.csv`, `cubic_cwnd.csv`, `cubic_rtt.csv`
- `queue_sojourn_l4s.csv`, `queue_sojourn_classic.csv`
- `count_mark_l4s.csv`, `count_mark_classic.csv`
- `queue_prob_coupled.csv`

## Simulation Topology

```
    1Gbps, 0ms                         1Gbps, 0ms
n0 (Prague) -----|                 |------ n4 (Prague sink)
                 |  rate, delay    |
                n2 -------------- n3 (DualPI² AQM)
                 |                 |
n1 (Cubic)  -----|                 |------ n5 (Cubic sink)
    1Gbps, 0ms                         1Gbps, 0ms
```

The bottleneck link (n2-n3) uses DualQ Coupled PI² with:
- Separate queues for L4S and Classic traffic
- ECN marking based on queue occupancy
- Coupled marking probability between queues

## Configuration

Edit `experiments/run-simulation.py` to customize:
- `NUM_RUNS`: Number of simulation repetitions (default: 30)
- `OUTPUT_BASE`: Output directory path
- `NS3_SCRIPT`: Path to the simulation script

Edit `experiments/code.cc` to modify:
- Link rates and delays
- Queue parameters
- Simulation duration
- Traffic patterns

## Related Papers

- Pre-print: https://arxiv.org/abs/2603.20166
