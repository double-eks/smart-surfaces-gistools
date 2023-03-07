# -*- coding: utf-8 -*-

import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [JoinMultiTables]


class JoinMultiTables(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Join Multiple Tables to Feature"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        inFeature = arcpy.Parameter(
            displayName='Input Feature',
            name='Input-Feature',
            datatype=['Feature Class', 'Feature Layer', 'Table'],
            parameterType='Required',
            direction='Input'
        )
        geoidField = arcpy.Parameter(
            displayName='GeoID Field',
            name='GeoID-Field',
            datatype='Field',
            parameterType='Required',
            direction='Input'
        )
        geoidField.filter.list = ['Text']
        geoidField.parameterDependencies = [inFeature.name]
        # keptFields= genFieldListParam('Input Fields to Be Kept', inFeature)
        params = [
            inFeature,
            # geoidField,
            # keptFields
        ]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
