import matplotlib.pyplot as plt
# import numpy as np

from utils.plot import save_fig


def fig_n_seen(
        data, design_types, fig_name=None, fig_folder=None,
        y_label="N seen", colors=None):

    fig, ax = plt.subplots(figsize=(4, 4))

    if colors is None:
        colors = [f'C{i}' for i in range(len(design_types))]

    for i, dt in enumerate(design_types):

        ax.plot(data[dt], color=colors[i], label=dt)

    ax.set_xlabel("Time")
    ax.set_ylabel(y_label)

    plt.legend()

    if fig_folder is not None and fig_name is not None:
        save_fig(fig_folder=fig_folder, fig_name=fig_name)
    else:
        plt.show()
