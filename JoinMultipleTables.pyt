# -*- coding: utf-8 -*-

import os

import arcpy
import pandas as pd

from templates import genFieldParam, genParam


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
        inFeature = genParam('Input Feature',
                             dataType=['Feature Class', 'Feature Layer'])
        geoidField = genFieldParam('GeoID Field', inFeature,
                                   fieldTypeFilter=['Text'])
        keptFields = genFieldParam('Input Fields to Keep', inFeature,
                                   isMulti=True)
        inFolder = genParam('Input Folder', dataType='DEFolder')
        inTables = genParam('Input Tables', dataType='File',
                            filterList=['csv'], isMulti=True)
        inTables.parameterDependencies = [inFolder.name]
        outTable = genParam('Output Table', isInput=False)
        keepOutTable = genParam('Whether to Save Output Table',
                                dataType='Boolean', paramType='Optional')
        keepOutTable.value = False
        outFeature = genParam('Output Feature', isInput=False,
                              dataType=['Feature Class', 'Feature Layer'])
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
        inFeatureParam, geoidParam, fieldsParam = parameters[:3]
        inTableFolderParam, inTablesParam = parameters[3:5]
        outTable, keepOutTable, outFeature = parameters[5:]
        gdb = arcpy.env.workspace

        # Combine separated tables into one single data frame
        messages.addMessage(
            f'< 1> Start to merge all the tables in {inTableFolderParam.valueAsText} ...')
        tableFiles = inTablesParam.values
        tractID = 'TractID'
        mergedDf = combineMultiTables(tableFiles, tractID)
        messages.addMessage(
            f'</1> Succeeded in merging')
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


def readTablesInFolder(folder: str):
    tables = [folder + '\\' +
              filename for filename in os.listdir(folder) if filename.endswith('.csv')]
    return tables


def combineMultiTables(tableFiles: list, tractID: str, isInitDf: bool = False):
    df = pd.DataFrame()
    for filepath in tableFiles:
        variableDf = pd.read_csv(str(filepath))
        currIdField = findIdField(str(filepath))
        filename = filepath.split('\\')[-1]
        # arcpy.AddMessage(
        #     f'\t>>> find {filename} >>> id field named: {currIdField}')
        if (not isInitDf):
            df = variableDf[currIdField].to_frame()
            df = df.rename(columns={currIdField: tractID})
            isInitDf = True
        df = df.join(variableDf.set_index(currIdField), on=tractID)
        # arcpy.AddMessage(
        #     f'\t>>> read {filename} >>> {len(variableDf)} rows, {len(variableDf.columns) - 1} fields')
    return df


def findIdField(filepath: str):
    # read only the second row of the CSV file
    rSample = pd.read_csv(filepath, nrows=1).iloc[0]
    idIndex = 0
    for i in range(len(rSample)):
        v = rSample[i]
        if (isinstance(v, str)):
            idIndex = i
            break
        elif (isinstance(v, float) or (isinstance(v, int))):
            digitStr = str(int(v))
            if (len(digitStr) == 11):
                idIndex = i
                break
    return str(rSample.index[idIndex])
