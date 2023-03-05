# -*- coding: utf-8 -*-

import arcpy

from RequestAirQuality import AirQualitySystem

arcpy.env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "SmartSurfaces"
        self.alias = "Smart Surfaces Toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [AirQualitySystem]
