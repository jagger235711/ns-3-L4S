import os
import pandas as pd
import numpy as np

# ================= CONFIGURATION =================
OUTPUT_BASE = "exps/results"  # Adjust to your correct folder
NUM_RUNS = 30
METRICS_FOLDER = "metrics"  # Subfolder to organize the metrics CSVs

# 1. METRICS FILES (Time, Value)
FILE_MAP_STANDARD = {
    # TCP
    "prague-cwnd.txt": "prague_cwnd",
    "prague-rtt.txt":  "prague_rtt",
    "cubic-cwnd.txt":  "cubic_cwnd",
    "cubic-rtt.txt":   "cubic_rtt",

    # Queue
    "queue-sojourn-l4s.txt":     "queue_sojourn_l4s",
    "queue-sojourn-classic.txt": "queue_sojourn_classic",
    "queue-prob-cl.txt":         "queue_prob_coupled",
}

# 2. IPs to identify the throughput source
IP_TO_NAME = {
    "10.1.4.2": "cubic",
    "10.1.5.2": "prague"
}

# 3. MARKS CONFIG (Keyword -> Metric)
MARK_KEYWORDS = {
    "L4S": "count_mark_l4s", "classic": "count_mark_classic",
    "drop": "count_drop", "Drop": "count_drop"
}
# =================================================

def main():
    print(f"--- FINAL CONSOLIDATION ---")

    # Dictionary organizing data by metric
    metrics_data = {
        # Marks
        "count_mark_l4s": [], "count_mark_classic": [],
        # Throughput
        "throughput_cubic": [], "throughput_prague": [],
        # TCP
        "prague_cwnd": [], "prague_rtt": [], "cubic_cwnd": [], "cubic_rtt": [],
        # Queue
        "queue_sojourn_l4s": [], "queue_sojourn_classic": [], "queue_prob_coupled": []
    }

    for run_n in range(NUM_RUNS):
        run_folder = os.path.join(OUTPUT_BASE, f"run_{run_n}")
        if not os.path.exists(run_folder): continue

        # [PART 1: MARKS]
        marks_path = os.path.join(run_folder, "queue-marks.txt")
        if os.path.exists(marks_path):
            try:
                df = pd.read_csv(marks_path, sep="|", header=None, names=["RawLine"], engine="python")
                split = df["RawLine"].str.split(n=1, expand=True)
                if split.shape[1] == 2:
                    df["Time"] = pd.to_numeric(split[0], errors="coerce")
                    df["Reason"] = split[1].astype(str)
                    # Process only L4S and classic (ignore drop)
                    for key, metric in MARK_KEYWORDS.items():
                        if metric not in ["count_mark_l4s", "count_mark_classic"]:
                            continue  # Skip drop metrics

                        mask = df["Reason"].str.contains(key, case=False, na=False)
                        if mask.any():
                            df_ev = pd.DataFrame({
                                "time": df.loc[mask, "Time"],
                                metric: 1.0,  # Metric name as column
                                "run_id": run_n
                            })
                            metrics_data[metric].append(df_ev)
            except: pass

        # [PART 2: THROUGHPUT]
        thr_path = os.path.join(run_folder, "throughput.csv")

        if os.path.exists(thr_path):
            try:
                # Order: Time, SrcIP, DstIP, TxPkts, TxBytes, LostPkts
                col_names = ['Time', 'SrcIP', 'DstIP', 'TxPkts', 'TxBytes', 'LostPkts']

                # 2. Read file without header
                tdf = pd.read_csv(thr_path, header=None, names=col_names)

                # 3. Iterate through IPs
                for src_ip, fname in IP_TO_NAME.items():
                    fdata = tdf[tdf["SrcIP"] == src_ip].copy()

                    if not fdata.empty:
                        # Sort by time to ensure chronological order
                        fdata = fdata.sort_values("Time").reset_index(drop=True)

                        # Calculate difference between consecutive cumulative values
                        delta_bytes = fdata["TxBytes"].diff()

                        # Convert delta from bytes to Mbps (assuming 1 second interval)
                        # Formula: (delta_bytes * 8) / 1_000_000 = Mbps
                        throughput_mbps = (delta_bytes * 8) / 1_000_000

                        # Fill first value with 0 (no previous value to subtract)
                        throughput_mbps = throughput_mbps.fillna(0)

                        metric_name = f"throughput_{fname}"
                        metrics_data[metric_name].append(pd.DataFrame({
                            "time": fdata["Time"],
                            metric_name: throughput_mbps,  # Metric name as column
                            "run_id": run_n
                        }))
            except Exception as e:
                print(f"Error processing throughput.csv in Run {run_n}: {e}")

        # [PART 3: STANDARD FILES]
        for fname, metric in FILE_MAP_STANDARD.items():
            fpath = os.path.join(run_folder, fname)
            if not os.path.exists(fpath): continue

            try:
                df = None

                # IF QUEUE FILE -> USE SPACE (sep=r'\s+')
                if "queue-" in fname:
                    # r'\s+' catches any space or tab. Python engine is safer for this.
                    df = pd.read_csv(fpath, header=None, sep=r'\s+', names=["Time", "Value"], engine="python")

                # IF TCP FILE -> USE COMMA
                else:
                    df = pd.read_csv(fpath, header=None, sep=",", names=["Time", "Value"], engine="c")

                if df is not None and not df.empty:
                    # Rename columns to final format
                    df.columns = ["time", metric]
                    df["run_id"] = run_n

                    # Type conversions
                    df["time"] = pd.to_numeric(df["time"], errors='coerce').astype(np.float32)
                    df[metric] = pd.to_numeric(df[metric], errors='coerce').astype(np.float32)
                    df.dropna(inplace=True)

                    metrics_data[metric].append(df)
            except Exception as e:
                print(f"Error in {fname} in Run {run_n}: {e}")

    # [SAVE]
    if any(metrics_data.values()):
        # Create metrics folder if it doesn't exist
        metrics_dir = os.path.join(OUTPUT_BASE, METRICS_FOLDER)
        os.makedirs(metrics_dir, exist_ok=True)

        print(f"Consolidating and saving files by metric in {metrics_dir}...")
        saved_count = 0

        for metric, df_list in metrics_data.items():
            if not df_list:  # Skip empty metrics
                continue

            # Concatenate all DataFrames for this metric
            metric_df = pd.concat(df_list, ignore_index=True)

            # Sort by run_id and time
            metric_df.sort_values(by=["run_id", "time"], inplace=True)

            # Save in separate CSV inside metrics folder
            output_path = os.path.join(metrics_dir, f"{metric}.csv")
            metric_df.to_csv(output_path, index=False, float_format='%.6g')

            saved_count += 1
            print(f"  ✓ {metric}.csv ({len(metric_df)} lines)")

        print(f"\n✅ SUCCESS! {saved_count} files saved in {metrics_dir}")
    else:
        print("❌ No data found.")

if __name__ == "__main__":
    main()