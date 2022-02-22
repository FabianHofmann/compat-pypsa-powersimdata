#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  4 15:16:47 2022.

@author: fabian
"""

import numpy as np
from common import load_scenario, networks
from powersimdata.input.export_data import export_to_pypsa
from pypsa.networkclustering import get_clustering_from_busmap

INTERCONNECT = "Western"
GROUP_BRANCHES = True
CLUSTER = True
LOAD_SHEDDING = True
CORRECT_AVAILABILITY = True
IGNORE_COMMITTABLES = True  # Make a LP instead of a MILP
NSNAPSHOT = -1
NHORIZON = 50

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

    scenario = load_scenario(interconnect=INTERCONNECT)

    # %%
    n = export_to_pypsa(scenario, skip_substations=not CLUSTER)

    if NSNAPSHOT:
        n.snapshots = n.snapshots[:NSNAPSHOT]

    if CORRECT_AVAILABILITY:
        variables = n.generators_t.p_max_pu.columns
        upper = n.generators.p_min_pu[variables].clip(
            upper=n.generators_t.p_max_pu.min()
        )
        n.generators.p_min_pu.update(upper)

    if IGNORE_COMMITTABLES:
        n.generators.committable = False
        n.generators.p_min_pu = 0

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
        s, c = n.lopf(
            pyomo=False,
            solver_name="gurobi",
            snapshots=sns,
            solver_options=SOLVER_PARAMS,
        )
        assert s == "ok", "Optimization failed."

    if LOAD_SHEDDING:
        # calculate back the net production in MW
        n.generators_t.p *= n.generators.sign

    n.export_to_netcdf(networks / f"{INTERCONNECT}-optimized.nc")
