#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  4 15:16:47 2022.

@author: fabian
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from cartopy import crs as ccrs
from common import load_scenario
from powersimdata.input.export_data import export_to_pypsa
from pypsa.networkclustering import get_clustering_from_busmap

INTERCONNECT = "Texas"
GROUP_BRANCHES = True
CLUSTER = False
LOAD_SHEDDING = True
NSNAPSHOT = 500
NHORIZON = 5

SOLVER_PARAMS = {
    "crossover": 0,
    "method": 2,
    "BarConvTol": 1.0e-4,
    "FeasibilityTol": 1.0e-4,
}


def recisum(ds):
    """
    Take the "reciprocal" sum for parallel resistances.
    """
    return 1 / (1 / ds).sum()


if __name__ == "__main__":

    figures = Path("../figures")
    if not figures.exists():
        figures.mkdir()

    networks = Path("../networks")
    if not figures.exists():
        figures.mkdir()

    scenario = load_scenario(interconnect=INTERCONNECT)

    # %%
    n = export_to_pypsa(scenario)

    if NSNAPSHOT:
        n.snapshots = n.snapshots[:NSNAPSHOT]

    if GROUP_BRANCHES:
        for c in n.branch_components:

            groups = n.df(c)[["bus0", "bus1"]].apply(set, axis=1).apply("".join)

            if len(groups) == len(n.df(c)):
                continue

            assert (
                n.df(c).groupby(groups).v_nom.apply(set).apply(len) == 1
            ).all(), "Cannot group parallel branches of different voltage levels."

            n.df(c)["z"] = n.df(c).r + 1j * n.df(c).x
            strategy = {
                "s_nom": ("s_nom", "sum"),
                "num_parallel": ("num_parallel", "sum"),
                "z": ("z", recisum),
            }
            branches = n.df(c).groupby(groups, sort=False).agg(**strategy)
            branches.index = groups.index[~groups.duplicated()]
            branches = branches.assign(r=np.real(branches.z), x=np.imag(branches.z))
            branches = branches.drop(columns="z")
            n.df(c).update(branches)

            n.remove(c, n.df(c).index.difference(branches.index))
            n.df(c).drop(columns="z", inplace=True)

    if CLUSTER:
        n.buses.drop(columns="name", inplace=True)
        C = get_clustering_from_busmap(n, n.buses.substation)
        n = C.network
    else:
        n = n[n.buses[n.buses.index != n.buses.substation].index]

    if LOAD_SHEDDING:
        n.madd(
            "Generator",
            n.buses.index,
            suffix=" load shedding",
            bus=n.buses.index,
            sign=1e-3,
            marginal_cost=1e2,
            p_nom=1e9,
            carrier="load",
        )
        n.add("Carrier", "load", nice_name="Load Shedding", color="red")

    for sns in np.array_split(n.snapshots, NHORIZON):
        n.lopf(
            pyomo=False,
            solver_name="gurobi",
            snapshots=sns,
            solver_options=SOLVER_PARAMS,
        )

    if LOAD_SHEDDING:
        # calculate back the net production in MW
        n.generators_t.p *= n.generators.sign

    # =========================================================================
    # STORE THE NETWORK
    # =========================================================================

    n.export_to_netcdf(networks / f"{INTERCONNECT}-optimized.nc")

    # =========================================================================
    # PLOT THE NETWORK
    # =========================================================================

    bus_scale = 5e-4
    production = n.generators_t.p.mean()
    production = n.generators.assign(p=production).groupby(["bus", "carrier"]).p.sum()

    nrows = 2
    ncols = (len(n.carriers) + 1) // 2

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
            line_colors="grey",
            line_widths=0.6,
        )
    if ncols * nrows > len(n.carriers):
        axes.ravel()[-1].axis("off")

    fig.tight_layout()
    fig.savefig(figures / f"{INTERCONNECT}-optimal-production.pdf")
