import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


plt.rcParams.update({
    "font.size": 7,
    "axes.titlesize": 7,
    "axes.labelsize": 7,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
    "lines.markersize": 3,
})

BIT_WIDTHS = [16, 32, 64, 128, 256, 512, 1024, 2048]


def fig_vbe_adders():
    fig, axes = plt.subplots(
        nrows=4,
        ncols=2,
        figsize=(4, 8),
        dpi=300,
        constrained_layout=True
    )
    axes = axes.flatten()

    plot_columns = {
        "x_count": ("c-", "X count"),
        "cx_count": ("r-", "CX count"),
        "ccx_count": ("b-", "CCX count"),
    }

    for i, n_bits in enumerate(BIT_WIDTHS):
        file = (
            f"benchmarking/thesis_benchmarking/vbe/"
            f"vbe_full_adder_60/vbe_adder_{n_bits}.csv"
        )
        df = pd.read_csv(file)
        ax = axes[i]

        for column, (style, label) in plot_columns.items():
            x = df["id"].to_numpy()[1:]
            y = df[column].to_numpy()[1:]
            ax.loglog(x, y, style, label=label)

        ax.set_title(f"{n_bits}-bit Adder")
        ax.set_xlabel("Step")
        ax.set_ylabel("Gate Count")
        ax.legend(fontsize="x-small")

    plt.savefig(
        "benchmarking/thesis_benchmarking/figs/fig_vbe_adders_60.png",
        dpi=600,
        bbox_inches="tight"
    )
    plt.close()


def fig_nam_adders():
    fig, axes = plt.subplots(
        nrows=4,
        ncols=2,
        figsize=(4, 8),
        dpi=300,
        constrained_layout=True
    )
    axes = axes.flatten()

    plot_columns = {
        "x_count": ("c-", "X count"),
        "cx_count": ("r-", "CX count"),
        "ccx_count": ("b-", "CCX count"),
    }

    for i, n_bits in enumerate(BIT_WIDTHS):
        file = (
            f"benchmarking/thesis_benchmarking/quipper/"
            f"quipper_adder_x_60/quipper_adder_{n_bits}.csv"
        )
        df = pd.read_csv(file)
        ax = axes[i]

        for column, (style, label) in plot_columns.items():
            x = df["id"].to_numpy()[1:]
            y = df[column].to_numpy()[1:]
            ax.loglog(x, y, style, label=label)

        ax.set_title(f"{n_bits}-bit Adder")
        ax.set_xlabel("Step")
        ax.set_ylabel("Gate Count")
        ax.legend(fontsize="x-small")

    plt.savefig(
        "benchmarking/thesis_benchmarking/figs/fig_nam_adders_60.png",
        dpi=600,
        bbox_inches="tight"
    )
    plt.close()


def get_adder_reduction_all(adder, gate_type="cx"):
    """Get gate-count reduction using all rules."""

    from benchmarking.benchmark_vbe_adder import (
        get_decomposed_vbe_ripple_adder
    )
    from benchmarking.benchmark_adders import get_adder

    reductions_pct = []

    for n_bits in BIT_WIDTHS:

        if adder == "vbe":
            file = (
                f"benchmarking/thesis_benchmarking/vbe/"
                f"vbe_full_adder_60/vbe_adder_{n_bits}.csv"
            )
            adder_circuit = get_decomposed_vbe_ripple_adder(
                n_bits=n_bits
            )

        elif adder == "quipper":
            file = (
                f"benchmarking/thesis_benchmarking/quipper/"
                f"quipper_adder_x_60/quipper_adder_{n_bits}.csv"
            )
            adder_circuit = get_adder(n_bits=n_bits)

        else:
            raise ValueError(f"Unknown adder: {adder}")

        gate_start = adder_circuit.count_ops().get(gate_type, 0)

        df = pd.read_csv(file)

        if df.empty:
            continue

        gate_end = df.iloc[-1][f"{gate_type}_count"]

        if gate_start == 0:
            reduction_pct = 0
        else:
            reduction_pct = (
                (gate_start - gate_end) / gate_start
            ) * 100

        reductions_pct.append(reduction_pct)

    print(reductions_pct)
    return reductions_pct


def get_adder_reduction(adder_res, gate_type="cx"):
    """Get gate-count reduction for a specific rule combination."""

    from benchmarking.benchmark_vbe_adder import (
        get_decomposed_vbe_ripple_adder
    )
    from benchmarking.benchmark_adders import get_adder

    reductions_pct = []

    for n_bits in BIT_WIDTHS:

        if adder_res == "vbe_cancel":
            file = (
                f"benchmarking/thesis_benchmarking/vbe/"
                f"vbe_full_adder_cancel_60/vbe_adder_{n_bits}.csv"
            )
            adder_circuit = get_decomposed_vbe_ripple_adder(
                n_bits=n_bits
            )

        elif adder_res == "vbe_1_com_can":
            file = (
                f"benchmarking/thesis_benchmarking/vbe/"
                f"vbe_full_adder_1_com_can_60/"
                f"vbe_adder_{n_bits}.csv"
            )
            adder_circuit = get_decomposed_vbe_ripple_adder(
                n_bits=n_bits
            )

        elif adder_res == "quipper_x":
            file = (
                f"benchmarking/thesis_benchmarking/quipper/"
                f"quipper_adder_x_60/"
                f"quipper_adder_{n_bits}.csv"
            )
            adder_circuit = get_adder(n_bits=n_bits)

        else:
            raise ValueError(f"Unknown adder configuration: {adder_res}")

        gate_start = adder_circuit.count_ops().get(gate_type, 0)

        df = pd.read_csv(file)

        if df.empty:
            continue

        gate_end = df.iloc[-1][f"{gate_type}_count"]

        if gate_start == 0:
            reduction_pct = 0
        else:
            reduction_pct = (
                (gate_start - gate_end) / gate_start
            ) * 100

        reductions_pct.append(reduction_pct)

    print(reductions_pct)
    return reductions_pct


def fig_adders_reduction_nam():
    adders = BIT_WIDTHS
    x = np.arange(len(adders))
    gate_type = "x"

    cancellation_reductions = get_adder_reduction(
        adder_res="quipper_x",
        gate_type=gate_type
    )

    all_rules_reductions = get_adder_reduction_all(
        adder="quipper",
        gate_type=gate_type
    )

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(8, 3),
        dpi=600,
        sharey=True
    )

    # Cancellation
    ax = axes[0]

    ax.grid(
        True,
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.5,
        zorder=0
    )

    ax.set_ylim(60, 80)

    ax.bar(
        x,
        cancellation_reductions,
        color="lightsteelblue",
        zorder=2
    )

    ax.set_title("NOT Cancellation", fontsize=12)
    ax.set_xlabel("Number of bits", fontsize=12)
    ax.set_ylabel(
        "X count reduction (%)",
        fontsize=12
    )

    ax.set_xticks(x)
    ax.set_xticklabels(
        adders,
        rotation=30,
        ha="right"
    )
    ax.tick_params(axis="both", labelsize=11)

    # All rules
    ax = axes[1]

    ax.grid(
        True,
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.5,
        zorder=0
    )

    ax.bar(
        x,
        all_rules_reductions,
        color="lightsteelblue",
        zorder=2
    )

    ax.set_title(
        "Commutation + Cancellation",
        fontsize=12
    )
    ax.set_xlabel("Number of bits", fontsize=12)

    ax.set_xticks(x)
    ax.set_xticklabels(
        adders,
        rotation=30,
        ha="right"
    )
    ax.tick_params(axis="both", labelsize=11)

    plt.tight_layout()

    plt.savefig(
        "benchmarking/thesis_benchmarking/figs/x_nam_c_vs_all.png",
        bbox_inches="tight",
        dpi=600
    )
    plt.close()


def fig_cancel_vs_cancel_x_vs_cancel_commute():
    adders = BIT_WIDTHS
    x = np.arange(len(adders))

    # Cancellation only
    cancel_reductions = get_adder_reduction(
        adder_res="vbe_cancel",
        gate_type="cx"
    )

    # Commutation + cancellation
    commute_cancel_reductions = get_adder_reduction_all(
        adder="vbe",
        gate_type="cx"
    )

    # Rule 3.1f + cancellation
    cancel_x_reductions = get_adder_reduction(
        adder_res="vbe_1_com_can",
        gate_type="cx"
    )

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(10, 4),
        dpi=600,
        gridspec_kw={"width_ratios": [1, 2]}
    )

    # Cancellation only
    ax1.grid(
        True,
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.5,
        zorder=0
    )

    ax1.bar(
        x,
        cancel_reductions,
        width=0.5,
        color="tab:green",
        label="Cancellation",
        zorder=3
    )

    ax1.set_title("Cancellation only", fontsize=12)
    ax1.set_ylabel(
        "CX count reduction (%)",
        fontsize=12
    )
    ax1.set_xlabel("Number of bits", fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(
        adders,
        rotation=30,
        ha="right"
    )
    ax1.tick_params(axis="both", labelsize=11)

    # Commutation + cancellation vs Rule 3.1f + cancellation
    ax2.grid(
        True,
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=0.5,
        zorder=0
    )

    width = 0.35

    ax2.bar(
        x - width / 2,
        commute_cancel_reductions,
        width,
        color="tab:blue",
        label="Commutation + cancellation",
        zorder=3
    )

    ax2.bar(
        x + width / 2,
        cancel_x_reductions,
        width,
        color="tab:orange",
        label="Rule 3.1f + cancellation",
        zorder=3
    )

    ax2.set_ylim(45, 51)

    ax2.set_title(
        "Commutation + Cancellation vs. Rule 3.1f + Cancellation",
        fontsize=12
    )
    ax2.set_xlabel("Number of bits", fontsize=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(
        adders,
        rotation=30,
        ha="right"
    )
    ax2.tick_params(axis="both", labelsize=11)

    # Shared legend
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()

    fig.legend(
        handles1 + handles2,
        labels1 + labels2,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.0),
        ncol=3,
        fontsize=10,
        frameon=False
    )

    plt.tight_layout()

    plt.savefig(
        "benchmarking/thesis_benchmarking/figs/"
        "fig_cancel_vs_cancel_x_vs_cancel_commute.png",
        bbox_inches="tight",
        dpi=600
    )
    plt.close()


if __name__ == "__main__":
    fig_vbe_adders()
    fig_nam_adders()
    fig_adders_reduction_nam()
    # fig_cancel_vs_cancel_x_vs_cancel_commute()