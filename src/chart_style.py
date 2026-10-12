"""Shared matplotlib style so every chart in the project looks consistent."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

IMAGES = Path(__file__).resolve().parents[1] / "images"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

BLUE = "#2a78d6"      # primary series
ORANGE = "#eb6834"    # second series
AQUA = "#1baf7a"      # third series
GRAY = "#b4b2a9"      # de-emphasised / baseline series
CRITICAL = "#d03b3b"  # status colour: late / bad


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "figure.dpi": 110,
            "savefig.dpi": 160,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.edgecolor": BASELINE,
            "axes.labelcolor": INK_SECONDARY,
            "axes.titlecolor": INK,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.titlepad": 26,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelcolor": INK_SECONDARY,
            "ytick.labelcolor": INK_SECONDARY,
            "legend.frameon": False,
            "legend.labelcolor": INK_SECONDARY,
            "lines.linewidth": 2,
            "lines.solid_capstyle": "round",
        }
    )


def subtitle(ax, text: str) -> None:
    """Grey line under the bold title, used to state the takeaway or the definition."""
    ax.text(0, 1.025, text, transform=ax.transAxes, color=INK_SECONDARY, fontsize=9.5, va="bottom")


def pct(decimals: int = 0) -> FuncFormatter:
    return FuncFormatter(lambda v, _: f"{v:.{decimals}%}")


def brl_millions() -> FuncFormatter:
    return FuncFormatter(lambda v, _: f"R${v / 1e6:.1f}M")


def save(fig, name: str) -> Path:
    IMAGES.mkdir(exist_ok=True)
    path = IMAGES / name
    fig.savefig(path, bbox_inches="tight", pad_inches=0.25)
    return path
