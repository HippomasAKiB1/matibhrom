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

# Data from Table 1
qwen_hal = [0.983, 0.400, 0.733, 0.283]
qwen_hal_ci = [[0.983 - 0.95, 0.400 - 0.28, 0.733 - 0.62, 0.283 - 0.17],
               [1.00 - 0.983, 0.52 - 0.400, 0.83 - 0.733, 0.40 - 0.283]]

gemma_hal = [0.983, 0.467, 0.583, 0.017]
gemma_hal_ci = [[0.983 - 0.95, 0.467 - 0.33, 0.583 - 0.45, 0.017 - 0.00],
                [1.00 - 0.983, 0.58 - 0.467, 0.70 - 0.583, 0.05 - 0.017]]

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
qwen_acc = [0.017, 0.586, 0.241, 0.150]
gemma_acc = [0.017, 0.525, 0.364, 0.900]

bars3 = ax2.bar(x - width/2, qwen_acc, width, label="Qwen 1.7B",
                color=qwen_color, alpha=0.9, edgecolor="black", linewidth=0.8)
bars4 = ax2.bar(x + width/2, gemma_acc, width, label="Gemma 4B",
                color=gemma_color, alpha=0.9, edgecolor="black", linewidth=0.8)

# Highlight Gemma 4B C3 breakthrough
ax2.annotate("90.0% Sel. Acc.\n(p = 0.0004)",
             xy=(3 + width/2, 0.900), xytext=(2.2, 0.92),
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

qwen_dom = [0.588, 0.425, 0.787]
gemma_dom = [0.500, 0.425, 0.613]

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
