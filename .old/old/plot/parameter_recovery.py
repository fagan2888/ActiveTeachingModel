import os

import numpy as np
import matplotlib.pyplot as plt
import scipy.stats

from utils.plot import save_fig

SCRIPT_NAME = os.path.basename(__file__).split(".")[0]


def plot(data, extension=''):

    # Create fig
    fig, axes = plt.subplots(nrows=len(data.keys()), figsize=(5, 10))

    i = 0
    for title, dic in sorted(data.items()):

        ax = axes[i]

        x, y = dic["initial"], dic["recovered"]

        ax.scatter(x, y, alpha=0.5)

        ax.set_title(title)

        max_ = max(x+y)
        min_ = min(x+y)

        ax.set_xlim(min_, max_)
        ax.set_ylim(min_, max_)

        ticks_positions = [round(i, 2) for i in np.linspace(min_, max_, 3)]

        ax.set_xticks(ticks_positions)
        ax.set_yticks(ticks_positions)

        ax.set_aspect(1)
        i += 1

        try:
            cor, p = scipy.stats.pearsonr(x, y)

            print(f'Pearson corr {title}: $r_pearson={cor:.2f}$, $p={p:.3f}$')

        except:
            pass

    f_name = f"parameter_recovery{extension}.pdf"
    save_fig(fig_name=f_name, sub_folder=SCRIPT_NAME)
