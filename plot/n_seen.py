import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from plot.generic import save_fig


def curve(seen, n_item=None, fig_name='seen.pdf',
          font_size=42, line_width=3,
          label_size=22):

    y = np.sum(seen, axis=0)

    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111)
    ax.set_ylabel('N seen', fontsize=font_size)
    ax.set_xlabel('Time', fontsize=font_size)

    ax.tick_params(axis="both", labelsize=label_size)
    ax.plot(y, color="black", linewidth=line_width)

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    if n_item is not None:
        ax.set_ylim(top=n_item+0.5)

    plt.tight_layout()
    save_fig(fig_name)