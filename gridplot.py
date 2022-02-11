#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 20 21:00:38 2022.

@author: fabian
"""

import matplotlib.pyplot as plt
import numpy as np
from cartopy import crs as ccrs
from matplotlib.legend_handler import HandlerPatch
from powersimdata.input.export_data import export_to_pypsa

from common import load_scenario

INTERCONNECT = "Texas"


def axes2pt(fig, ax):
    return np.diff(ax.transData.transform([(0, 0), (0, 1)]), axis=0)[0][1] * (
        56.0 / fig.dpi
    )


class HandlerCircle(HandlerPatch):
    def create_artists(
        self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans
    ):
        fig = legend.get_figure()
        radius = orig_handle.get_radius() * axes2pt(fig, legend.axes)
        center = 1.5 * radius - 0.5 * xdescent, 0.5 * radius - 0.5 * ydescent
        p = plt.Circle(center, radius)
        self.update_prop(p, orig_handle, legend)
        p.set_transform(trans)
        return [p]


if __name__ == "__main__":

    scenario = load_scenario(interconnect=INTERCONNECT)
    n = export_to_pypsa(scenario)

    fig, ax = plt.subplots(
        figsize=(10, 10), subplot_kw={"projection": ccrs.PlateCarree()}
    )
    if INTERCONNECT == "Texas":
        bus_scale = 1e4
    else:
        bus_scale = 5e3

    n.plot(
        bus_sizes=n.generators.groupby(["bus", "carrier"]).p_nom.sum() / bus_scale,
        ax=ax,
        margin=0.1,
        color_geomap=True,
    )

    refsize = 500
    radius = (refsize / bus_scale) ** 0.5
    unit = "MW"
    handles = [plt.Circle((0, 0), radius, facecolor=c) for c in n.carriers.color]
    labels = list(n.carriers.nice_name)

    handles.append(plt.Circle((0, 0), radius, facecolor="white", edgecolor="k"))
    labels.append(f"{refsize} {unit}")

    ax.legend(
        handles,
        labels,
        handler_map={plt.Circle: HandlerCircle()},
        loc="upper center",
        bbox_to_anchor=(0.5, 0),
        ncol=5,
        frameon=False,
    )

    fig.savefig(f"{INTERCONNECT}-grid.pdf", bbox_inches="tight")
