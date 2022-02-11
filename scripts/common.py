#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 11 11:24:37 2022.

@author: fabian
"""
from powersimdata import Scenario


def load_scenario(interconnect="Western"):
    """
    This code is copied from https://breakthrough-
    energy.github.io/docs/powersimdata/scenario.html#creating-a-scenario.
    """
    scenario = Scenario()
    # print name of Scenario object state
    print(scenario.state.name)

    # Start building a scenario
    scenario.set_grid(grid_model="usa_tamu", interconnect=interconnect)

    # set plan and scenario names
    scenario.set_name("test", "dummy")
    # set start date, end date and interval
    scenario.set_time("2016-08-01 00:00:00", "2016-08-31 23:00:00", "24H")
    # set demand profile version
    scenario.set_base_profile("demand", "vJan2021")
    # set hydro profile version
    scenario.set_base_profile("hydro", "vJan2021")
    # set solar profile version
    scenario.set_base_profile("solar", "vJan2021")
    # set wind profile version
    scenario.set_base_profile("wind", "vJan2021")

    return scenario
