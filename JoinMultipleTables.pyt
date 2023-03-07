# -*- coding: utf-8 -*-

import os

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
        keptFields = arcpy.Parameter(
            displayName='Input Fields to Keep',
            name='Input-Fields-to-Keep',
            datatype='Field',
            parameterType='Optional',
            direction='Input',
            multiValue=True
        )
        keptFields.parameterDependencies = [inFeature.name]
        inFolder = arcpy.Parameter(
            displayName='Input Folder',
            name='Input-Folder',
            datatype='DEFolder',
            parameterType='Required',
            direction='Input',
        )
        inTables = arcpy.Parameter(
            displayName='Input Tables',
            name='Input-Tables',
            datatype='File',
            parameterType='Required',
            direction='Input',
            multiValue=True
        )
        inTables.filter.list = ['csv']
        inTables.parameterDependencies = [inFolder.name]
        outTable = arcpy.Parameter(
            displayName='Output Table',
            name='Output-Table',
            datatype='GPString',
            parameterType='Required',
            direction='Output',
        )
        keepOutTable = arcpy.Parameter(
            displayName='Whether to Save Output Table',
            name='Whether-to-Save-Output-Table',
            datatype='Boolean',
            parameterType='Optional',
            direction='Input',
        )
        keepOutTable.value = False
        outFeature = arcpy.Parameter(
            displayName='Output Feature',
            name='Output-Feature',
            datatype=['Feature Class', 'Feature Layer'],
            parameterType='Required',
            direction='Output',
        )
        outFeature.parameterDependencies = [inFeature.name]
        params = [
            inFeature,
            geoidField,
            keptFields,
            inFolder,
            inTables,
            outTable,
            keepOutTable,
            outFeature
        ]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        inFeatureParam, geoidParam, fieldsParam = parameters[:3]
        inTableFolderParam, inTablesParam = parameters[3:5]
        outTable, keepOutTable, outFeature = parameters[5:]
        if (geoidParam.value):
            if (not fieldsParam.value):
                fieldsParam.value = geoidParam.value
        if (inTableFolderParam.value):
            if (not inTablesParam.value):
                inTablesParam.value = readTablesInFolder(
                    inTableFolderParam.valueAsText)
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


def readTablesInFolder(folder: str):
    tables = [folder + '\\' +
              filename for filename in os.listdir(folder) if filename.endswith('.csv')]
    return tables
