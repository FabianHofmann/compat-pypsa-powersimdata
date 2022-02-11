#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 11 12:08:19 2022.

@author: fabian
"""

import matplotlib.pyplot as plt
import pypsa
from cartopy import crs as ccrs
from common import figures, networks

INTERCONNECT = "Texas"

if __name__ == "__main__":

    n = pypsa.Network(str(networks / f"{INTERCONNECT}-optimized.nc"))
    bus_scale = 5e-4
    production = n.generators_t.p.mean()
    production = n.generators.assign(p=production).groupby(["bus", "carrier"]).p.sum()

    nrows = 2
    ncols = (len(n.carriers) + 2) // 2
    # %%
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(20, 10), subplot_kw={"projection": ccrs.PlateCarree()}
    )

    for i, c in enumerate(n.carriers.index):
        ax = axes.ravel()[i]

        n.plot(
            ax=ax,
            bus_sizes=production.loc[:, c] * bus_scale,
            bus_colors=n.carriers.color[c],
            margin=0.0,
            color_geomap=True,
            title=n.carriers.nice_name[c],
            bus_alpha=0.7,
            line_colors="darkslategrey",
            line_widths=0.6,
        )

    ax = axes.ravel()[i + 1]

    n.plot(
        ax=ax,
        bus_sizes=n.loads_t.p.mean() * bus_scale,
        bus_colors="orange",
        margin=0.0,
        color_geomap=True,
        title="Load",
        bus_alpha=0.7,
        line_colors="darkslategrey",
        line_widths=0.6,
    )

    if ncols * nrows > (len(n.carriers) + 1):
        axes.ravel()[-1].axis("off")

    fig.tight_layout()
    fig.savefig(figures / f"{INTERCONNECT}-optimal-production.pdf")

    # %%

    fig, ax = plt.subplots(
        figsize=(10, 10), subplot_kw={"projection": ccrs.PlateCarree()}
    )

    n.plot(
        ax=ax,
        margin=0.0,
        color_geomap=True,
        flow="mean",
        title="Average Flow",
        bus_sizes=0.0001,
        bus_alpha=0.7,
        line_colors="teal",
        line_widths=0.2,
    )
    fig.tight_layout()
    fig.savefig(figures / f"{INTERCONNECT}-optimal-flow.pdf")
