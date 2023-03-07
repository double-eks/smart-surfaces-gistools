import os

import arcpy
import pandas as pd


def combineMultiTables(tableFiles: list, tractID: str, isInitDf: bool = False):
    df = pd.DataFrame()
    for filepath in tableFiles:
        filepath = str(filepath)
        variableDf = pd.read_csv(filepath)
        currIdField = findIdField(filepath)
        filename = filepath.split('\\')[-1]
        arcpy.AddMessage(
            f'\t>>> find {filename} >>> id field named: {currIdField}')
        if (not isInitDf):
            df = variableDf[currIdField].to_frame()
            df = df.rename(columns={currIdField: tractID})
            isInitDf = True
        df = df.join(variableDf.set_index(currIdField), on=tractID)
        arcpy.AddMessage(
            f'\t>>> read {filename} >>> {len(variableDf)} rows, {len(variableDf.columns) - 1} fields')
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


def copyInputFeature(inputFeature: str, inputFields: str, outputFeature: str):
    fms = arcpy.FieldMappings()
    fieldNames = inputFields.split(';')
    for fieldName in fieldNames:
        fm = arcpy.FieldMap()
        field = arcpy.ListFields(inputFeature, fieldName)[0]
        fm.addInputField(inputFeature, fieldName)
        fm.outputField = field
        fm.mergeRule = 'First'
        fms.addFieldMap(fm)
    arcpy.FeatureClassToFeatureClass_conversion(
        inputFeature, arcpy.env.workspace, outputFeature, field_mapping=fms)


# This is used to execute code if the file was run but not imported
if __name__ == '__main__':

    # Tool parameter accessed with GetParameter or GetParameterAsText
    inputFeature = arcpy.GetParameterAsText(0)
    geoidField = arcpy.GetParameterAsText(1)
    inputFields = arcpy.GetParameterAsText(2)
    tableFolder = arcpy.GetParameterAsText(3)
    tableFiles = arcpy.GetParameter(4)
    mergedVarTable = arcpy.GetParameterAsText(5)
    isKeepTable = arcpy.GetParameter(6)
    outputFeature = arcpy.GetParameterAsText(7)
    gdb = arcpy.env.workspace
    tractID = 'TractID'

    # Combine separated tables into one single data frame
    arcpy.AddMessage(
        f'< 1> Start to merge all the tables in {tableFolder} ...')
    mergedDf = combineMultiTables(tableFiles, tractID)
    arcpy.AddMessage(
        f'</1> Succeeded in merging')

    # Export a csv table and import csv to GIS
    arcpy.AddMessage(
        f'< 2> Start to write {mergedVarTable} table to geodatabase ...')
    mergedTable = os.getcwd() + '\\merged_table.csv'
    mergedDf.to_csv(mergedTable, index=False)
    arcpy.AddMessage(f'\t>>> export {mergedTable}')
    arcpy.conversion.TableToTable(mergedTable, gdb, mergedVarTable)
    os.remove(mergedTable)
    arcpy.AddMessage(f'\t>>> delete {mergedTable}')
    arcpy.AddMessage(
        '</2> Succeeded in writing the merged table')

    # Generate a tract feature with only GEOID field
    arcpy.AddMessage(
        f'< 3> Start to join {mergedVarTable} table to {inputFeature} ...')
    copyInputFeature(inputFeature, inputFields, outputFeature)
    # Find all the variable fields awaiting joins
    variables = [field.name for field in arcpy.ListFields(mergedVarTable)
                 if (field.name not in [tractID, 'OBJECTID'])]
    # Copy a str id field and use the new id to join variable fields
    joinIdName = tractID + 'String'
    arcpy.management.CalculateField(
        mergedVarTable, joinIdName, f"!{tractID}!", "PYTHON3", '', "TEXT", None)
    arcpy.management.JoinField(
        outputFeature, geoidField, mergedVarTable, joinIdName, variables)
    arcpy.AddMessage(f'\t>>> join {len(variables)} variables')
    # Remove the merged table from geodatabase if not checking the button
    if (not isKeepTable):
        arcpy.Delete_management(mergedVarTable)
        arcpy.AddMessage(f'\t>>> remove {mergedVarTable}')
    arcpy.AddMessage(
        f'</3> Succeeded in combining all!')

    arcpy.SetParameter(7, outputFeature)  # Update output tract
