# -*- coding: utf-8 -*-

import os

import arcpy
import pandas as pd

from templates import (dfToStructuredArr, genFieldParam, genParam,
                       getFeatureValue)


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
                inTablesParam.value = findTablesInFolder(
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
        outTableParam, keepOutTable, outFeatureParam = parameters[5:]
        gdb = arcpy.env.workspace
        idsample = getFeatureValue(inFeatureParam.value,
                                   geoidParam.valueAsText)

        inFeature = inFeatureParam.valueAsText
        geoidField = geoidParam.valueAsText
        keepFields = fieldsParam.valueAsText.split(';')
        tableFold = inTableFolderParam.valueAsText
        tables = inTablesParam.values
        outTable = outTableParam.valueAsText
        outFeature = outFeatureParam.valueAsText
        # Combine separated tables into one single data frame
        messages.addMessage(f'- Merging all the tables in {tableFold}')
        varDf = readTables(tables, idsample)
        varFields = varDf.columns.values[:-1]
        keepFields.extend(varFields)
        joinField = 'ID'
        varDf[joinField] = varDf.index.values
        varArr = dfToStructuredArr(varDf)
        arcpy.da.NumPyArrayToTable(varArr, gdb + '\\' + outTable)

        # Generate a tract feature with only GEOID field
        arcpy.AddMessage(f'- Joining {len(tables)} table(s) to {inFeature}')
        arcpy.management.AddJoin(
            in_layer_or_view=inFeature,
            in_field=geoidField,
            join_table=outTable,
            join_field=joinField,
            join_type="KEEP_ALL",
            index_join_fields="NO_INDEX_JOIN_FIELDS"
        )
        arcpy.conversion.ExportFeatures(
            in_features=inFeature,
            out_features=outFeature,
            where_clause="",
            sort_field=None
        )
        arcpy.RemoveJoin_management(inFeature)
        if (not keepOutTable.value):
            arcpy.Delete_management(outTable)
        arcpy.AddMessage(f'- Cleaning {outFeature}')
        arcpy.management.DeleteField(
            in_table=outFeature,
            drop_field=keepFields,
            method='KEEP_FIELDS'
        )
        arcpy.AddMessage('\nDONE!')
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


def findTablesInFolder(folder: str):
    tables = [folder + '\\' +
              filename for filename in os.listdir(folder)
              if filename.endswith('.csv')]
    return tables


def readTables(tables: list, idsample: str):
    masterDf = pd.DataFrame()
    for tablepath in tables:
        df = pd.read_csv(str(tablepath))
        idField = findIdField(df, idsample)
        df[idField] = df[idField].astype(str)
        df = df.set_index(idField)
        # df = df.rename(columns={idField: sharedField})
        if (masterDf.empty):
            masterDf = df
        else:
            masterDf = pd.merge(masterDf, df,
                                left_index=True, right_index=True)
    return masterDf


def findIdField(df: pd.DataFrame, idsample: str) -> str:
    for c in range(len(df.columns)):
        field = df.columns[c]
        value = str(df.iloc[0, c])
        if (value.isdigit()) and (len(value) == len(idsample)):
            return field
