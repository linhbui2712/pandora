import matplotlib.pyplot as plt
import glob
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import ScalarFormatter

plt.rcParams.update({
    "font.size": 7,
    "axes.titlesize": 7,
    "axes.labelsize": 7,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
    "lines.markersize": 3,
})

def fig_vbe_adders():
    bit_widths = [16, 32, 64, 128, 256, 512, 1024, 2048]

    fig, axes = plt.subplots(nrows=2, ncols=4, figsize=(8, 4), dpi=300, constrained_layout=True)
    axes = axes.flatten()

    plot_columns = {
        
        
        'x_count': ('c-', 'X count'),
        'cx_count': ('r-', 'CX count'),
        'ccx_count': ('b-', 'CCX count'),
    }

    for i, n_bits in enumerate(bit_widths):
        df = pd.read_csv(f'benchmarking/thesis_benchmarking/vbe/vbe_full_adder_only_x_30/vbe_adder_{n_bits}.csv')
        ax = axes[i]

        for col, (style, label) in plot_columns.items():
            x = np.array(df['id'])[1:]
            y = np.array(df[col])[1:]
            ax.loglog(x, y, style, label=label)

        ax.set_title(f'{n_bits}-bit Adder')
        ax.set_xlabel('Step')
        ax.set_ylabel('Gate Count')
        ax.legend(fontsize='x-small')

    plt.savefig("benchmarking/thesis_benchmarking/figs/fig_vbe_adders.png", bbox_inches='tight', dpi=600)

    plt.close()

def get_vbe_adder_reduction():
    from benchmarking.benchmark_vbe_adder import get_decomposed_vbe_ripple_adder

    bits = [16, 32, 64, 128, 256, 512, 1024, 2048]

    reductions_pct = []
    labels = []

    for n_bits in bits:
        labels.append(f'Adder_{n_bits}')
        file = f"benchmarking/thesis_benchmarking/vbe/vbe_full_adder_only_x_30/vbe_adder_{n_bits}.csv"

        adder_circuit = get_decomposed_vbe_ripple_adder(n_bits=n_bits)
        counts = adder_circuit.count_ops()
        cx_count = counts.get('cx', 0) 

        df = pd.read_csv(file)

        if df.empty:
            continue

        cx_start = cx_count
        cx_end = df.iloc[-1]["cx_count"]

        # Avoid division by zero
        if cx_start == 0:
            reduction_pct = 0
        else:
            reduction_pct = ((cx_start - cx_end) / cx_start) * 100

        reductions_pct.append(reduction_pct)
    
    print(reductions_pct)
    
    return reductions_pct

def fig_vbe_adders_reduction():
    reductions_pct = get_vbe_adder_reduction()
    adders = [16, 32, 64, 128, 256, 512, 1024, 2048]
    x = np.arange(len(adders))

    fig = plt.figure(figsize=(5, 5), dpi=600)
    ax = fig.add_subplot(1, 1, 1)
    ax.grid(True, axis='y', linestyle='--', linewidth=0.8, alpha=0.5, zorder=0)
    ax.bar(x, reductions_pct, color='lightsteelblue', zorder=2)
    ax.set_ylabel("CX count reduced (%)")
    ax.set_title("VBE Adder CX Count Reduction")
    ax.set_xticks(x)
    ax.set_xticklabels(adders, rotation=30, ha='right')

    plt.savefig("benchmarking/thesis_benchmarking/figs/fig_vbe_adders_reduction.png", bbox_inches='tight', dpi=600)

if __name__ == "__main__":
    fig_vbe_adders()
    # fig_vbe_adders_reduction()
    