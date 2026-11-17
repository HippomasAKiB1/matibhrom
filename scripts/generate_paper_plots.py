"""
Generate Publication-Grade Figures for Matibhrom Manuscript (300 DPI).
Produces Figure 2 (Scaling and Abstention Dynamics) and Figure 3 (Domain and Register Disparity).
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Publication styling (ACL style: clean, serif font, professional palette)
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 13,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

out_dir = Path("paper/figures")
out_dir.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# Figure 2: Scaling and Selective Abstention Dynamics
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))

conditions = ["C0\n(Closed)", "C1\n(Oracle)", "C2\n(RAG)", "C3\n(Abstain)"]
x = np.arange(len(conditions))
width = 0.35

# Data from Table 1 (Authoritative Test Split)
qwen_hal = [0.965, 0.644, 0.875, 0.375]
qwen_hal_ci = [[0.965 - 0.95, 0.644 - 0.61, 0.875 - 0.85, 0.375 - 0.34],
               [0.98 - 0.965, 0.67 - 0.644, 0.90 - 0.875, 0.40 - 0.375]]

gemma_hal = [0.894, 0.606, 0.789, 0.033]
gemma_hal_ci = [[0.894 - 0.85, 0.606 - 0.54, 0.789 - 0.73, 0.033 - 0.01],
                [0.94 - 0.894, 0.68 - 0.606, 0.85 - 0.789, 0.06 - 0.033]]

qwen_color = "#386cb0"
gemma_color = "#f0027f"

# Subplot 1: Hallucination Rate
bars1 = ax1.bar(x - width/2, qwen_hal, width, yerr=qwen_hal_ci, label="Qwen 1.7B",
                color=qwen_color, alpha=0.9, capsize=4, edgecolor="black", linewidth=0.8)
bars2 = ax1.bar(x + width/2, gemma_hal, width, yerr=gemma_hal_ci, label="Gemma 4B",
                color=gemma_color, alpha=0.9, capsize=4, edgecolor="black", linewidth=0.8)

ax1.set_ylabel("Hallucination Rate (Lower is Better)")
ax1.set_title("(a) Hallucination Rate with 95% Bootstrap CIs", pad=8)
ax1.set_xticks(x)
ax1.set_xticklabels(conditions)
ax1.set_ylim(0, 1.08)
ax1.grid(axis="y", linestyle="--", alpha=0.5)
ax1.legend(frameon=True, facecolor="white", framealpha=0.9)

# Subplot 2: Selective Accuracy & Abstention Rate
qwen_acc = [0.020, 0.338, 0.104, 0.098]
gemma_acc = [0.080, 0.381, 0.123, 0.538]

bars3 = ax2.bar(x - width/2, qwen_acc, width, label="Qwen 1.7B",
                color=qwen_color, alpha=0.9, edgecolor="black", linewidth=0.8)
bars4 = ax2.bar(x + width/2, gemma_acc, width, label="Gemma 4B",
                color=gemma_color, alpha=0.9, edgecolor="black", linewidth=0.8)

# Highlight Gemma 4B C3 breakthrough
ax2.annotate("53.8% Sel. Acc. (3.3% Hal.)\n(p = 8.38e-13)",
             xy=(3 + width/2, 0.538), xytext=(1.8, 0.75),
             arrowprops=dict(arrowstyle="->", color="black", lw=1.2),
             fontsize=9, fontweight="bold", backgroundcolor="#ffffcc")

ax2.set_ylabel("Selective Accuracy (Higher is Better)")
ax2.set_title("(b) Selective Accuracy across Conditions", pad=8)
ax2.set_xticks(x)
ax2.set_xticklabels(conditions)
ax2.set_ylim(0, 1.08)
ax2.grid(axis="y", linestyle="--", alpha=0.5)
ax2.legend(frameon=True, facecolor="white", framealpha=0.9)

plt.tight_layout()
fig.savefig(out_dir / "figure2_scaling_abstention.png")
plt.close(fig)

# -------------------------------------------------------------
# Figure 3: Domain Disparity and Register Asymmetry
# -------------------------------------------------------------
fig, (ax3, ax4) = plt.subplots(1, 2, figsize=(10, 4.2))

# Subplot 3(a): Domain Breakdown
domains = ["General", "Medical", "Legal"]
x_dom = np.arange(len(domains))

qwen_dom = [0.625, 0.723, 0.796]
gemma_dom = [0.421, 0.625, 0.696]

ax3.bar(x_dom - width/2, qwen_dom, width, label="Qwen 1.7B",
        color=qwen_color, alpha=0.9, edgecolor="black", linewidth=0.8)
ax3.bar(x_dom + width/2, gemma_dom, width, label="Gemma 4B",
        color=gemma_color, alpha=0.9, edgecolor="black", linewidth=0.8)

ax3.set_ylabel("Hallucination Rate")
ax3.set_title("(a) Domain Disparity (Medical vs. Legal)", pad=8)
ax3.set_xticks(x_dom)
ax3.set_xticklabels(domains)
ax3.set_ylim(0, 0.9)
ax3.grid(axis="y", linestyle="--", alpha=0.5)
ax3.legend(frameon=True, facecolor="white", framealpha=0.9)

# Subplot 3(b): Linguistic Register & Dense Retriever Recall
registers = ["Standard Bangla (bn)", "Banglish (Romanized)"]
x_reg = np.arange(len(registers))

recall_vals = [66.67, 30.00]
rank1_vals = [40.00, 13.33]

bar_rec = ax4.bar(x_reg - width/2, recall_vals, width, label="Recall@k (%)",
                  color="#2ca02c", alpha=0.85, edgecolor="black", linewidth=0.8)
bar_r1 = ax4.bar(x_reg + width/2, rank1_vals, width, label="Rank-1 Precision (%)",
                 color="#1f77b4", alpha=0.85, edgecolor="black", linewidth=0.8)

for bar in bar_rec + bar_r1:
    yval = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f"{yval:.1f}%",
             ha="center", va="bottom", fontsize=9, fontweight="bold")

ax4.set_ylabel("Retrieval Metric (%)")
ax4.set_title("(b) BGE-M3 Dense Retrieval Recall Asymmetry", pad=8)
ax4.set_xticks(x_reg)
ax4.set_xticklabels(registers)
ax4.set_ylim(0, 85)
ax4.grid(axis="y", linestyle="--", alpha=0.5)
ax4.legend(frameon=True, facecolor="white", framealpha=0.9)

plt.tight_layout()
fig.savefig(out_dir / "figure3_domain_register.png")
plt.close(fig)

print("Successfully generated figure2_scaling_abstention.png and figure3_domain_register.png in paper/figures/")
