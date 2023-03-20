# -*- coding: utf-8 -*-

import re
from datetime import date, datetime
from urllib.request import urlopen

import arcpy
import pandas as pd
from bs4 import BeautifulSoup

from helpers import (dfToStructuredArr, downloadZipToDf, enableChildParam,
                     formatDateOnly, genDateParam, genFieldParam, genParam,
                     getFeatureValue)

# ============================================================================ #
# Geoprocessing tools
# ============================================================================ #


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [RequestByZip, RequestByCounty]


# ============================================================================ #
# Request Daily AQI by ZIP Code
# ============================================================================ #


class RequestByZip(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = 'Request Daily AQI by ZIP Code'
        self.description = ""
        self.canRunInBackground = False

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def getParameterInfo(self):
        """Define parameter definitions"""
        # Input parameters
        spaceScale = genParam('Request for', filterList=['city', 'county'])
        zipCode = genParam('Use Any Zip in the Area to Look Up City-County-State',
                           dataType='Long', isVisible=False)
        state = genParam('State', isVisible=False)
        location = genParam('Location', isVisible=False)
        lookup = genParam('Check LookUp Location Before Go',
                          dataType='Boolean', isVisible=False)
        startDate, endDate = initTimeParams()
        # Set parameter dependency
        state.parameterDependencies = [zipCode.name]
        location.parameterDependencies = [zipCode.name]
        lookup.parameterDependencies = [zipCode.name]
        endDate.parameterDependencies = [startDate.name]
        # Output parameter
        table = genParam('Output Table', dataType='Table', isInput=False)
        # Set the parameter properties
        params = [
            spaceScale,
            zipCode,
            state,
            location,
            lookup,
            startDate,
            endDate,
            table
        ]
        return params

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        scaleParam, zipParam, stateParam, locParam, checkParam, startParam, endParam, outputParam = parameters

        enableChildParam(scaleParam, zipParam)
        enableChildParam(zipParam, stateParam, locParam, checkParam)
        updateDateParams(startParam, endParam)

        if (zipParam.value):
            zipcode = zipParam.value
            zipDf = lookUpByZip(zipcode)
            stateParam.filter.list = [zipDf.state[zipcode]]
            stateParam.value = zipDf.state[zipcode]
            if ('city' in scaleParam.valueAsText):
                locParam.filter.list = [zipDf.city[zipcode]]
                locParam.value = zipDf.city[zipcode]
            else:
                locParam.filter.list = [zipDf.county[zipcode]]
                locParam.value = zipDf.county[zipcode]

        if (locParam.value) and (startParam.value):
            if (not outputParam.altered):
                tableName = '{}_{}_aqi'.format(
                    locParam.valueAsText,
                    startParam.valueAsText[:4]
                )
                tableName = tableName.replace(' ', '_')
                outputParam.value = arcpy.env.workspace + '\\' + tableName

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        scaleParam, zipParam, stateParam, locParam, checkParam, startParam, endParam, outputParam = parameters
        validateDates(startParam, endParam)
        if (zipParam.value):
            if (re.search(r'^\d{5}$', zipParam.valueAsText) == None):
                zipParam.setErrorMessage('Invalid zip code')
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        scaleParam, zipParam, stateParam, locParam, checkParam, startParam, endParam, outputParam = parameters
        scale = scaleParam.valueAsText

        if ('city' in scale):
            urlTemplate = 'https://aqs.epa.gov/aqsweb/airdata/daily_aqi_by_cbsa_{}.zip'
        else:
            urlTemplate = 'https://aqs.epa.gov/aqsweb/airdata/daily_aqi_by_county_{}.zip'

        df = requestAirQuality(urlTemplate, startParam, endParam)
        # Get the data of location
        location = locParam.valueAsText
        df = df[df.Location.str.lower() == location.lower()]
        outputTableFromDf(outputParam, df, messages)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


# ============================================================================ #
# Request Daily AQI by County Feature
# ============================================================================ #


class RequestByCounty(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = 'Request Daily AQI by County Feature'
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        inputFeature = genParam(
            'Input County Feature',
            dataType=['Feature Class', 'Feature Layer', 'Table'])
        idField = genFieldParam('GeoID Field', inputFeature)
        idField.enabled = False
        idField.filter.list = ['Text']
        startDate, endDate = initTimeParams()
        # Output parameter
        table = genParam('Output Table', dataType='Table', isInput=False)
        params = [
            inputFeature,
            idField,
            startDate,
            endDate,
            table
        ]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        inFeatureParam, idParam, startParam, endParam, outputParam = parameters
        updateDateParams(startParam, endParam)
        enableChildParam(inFeatureParam, idParam)
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        inFeatureParam, idParam, startParam, endParam, outputParam = parameters
        validateGeoID(inFeatureParam, idParam)
        validateDates(startParam, endParam)
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        inFeatureParam, idParam, startParam, endParam, outputParam = parameters
        urlTemplate = 'https://aqs.epa.gov/aqsweb/airdata/daily_aqi_by_county_{}.zip'
        df = requestAirQuality(urlTemplate, startParam, endParam)
        # Get the data of location
        arr = arcpy.da.FeatureClassToNumPyArray(inFeatureParam.value,
                                                idParam.valueAsText)
        rows = [geoid[0] for geoid in arr]
        df = df[df.GeoID.isin(rows)]
        outputTableFromDf(outputParam, df, messages)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


# ============================================================================ #
# Define parameters
# ============================================================================ #


def initTimeParams():
    startDate = genDateParam('Start Date')
    endDate = genDateParam('End Date')
    return startDate, endDate


# ============================================================================ #
# Update parameters
# ============================================================================ #


def updateDateParams(startParam, endParam):
    formatDateOnly(startParam, endParam)
    if (startParam.value) and (not endParam.value):
        startyr = int(startParam.valueAsText[:4])
        endParam.value = date(startyr, 12, 31).strftime('%Y/%m/%d')


# ============================================================================ #
# Validate parameters
# ============================================================================ #


def validateDates(startParam, endParam):
    if (startParam.value) and (endParam.value):
        if (startParam.value >= endParam.value):
            endParam.setErrorMessage('Invalid end date')
        if (startParam.value > datetime(2022, 12, 31)):
            startParam.setErrorMessage('No data available')
        if (endParam.value > datetime(2022, 12, 31)):
            endParam.setWarningMessage('No data available since 2023')


def validateGeoID(featureParam, idParam):
    if (idParam.value):
        geoid = getFeatureValue(featureParam.value, idParam.valueAsText)
        if (re.search(r'^\d{5}$', geoid) == None):
            idParam.setErrorMessage('Invalid county GeoID')


# ============================================================================ #
# Helper functions
# ============================================================================ #


def lookUpByZip(zipcode: int):
    url = 'https://www.getzips.com/cgi-bin/ziplook.exe?What=1&Zip={}&Submit=Look+It+Up'
    url = url.format(zipcode)
    html = urlopen(url)
    bs = BeautifulSoup(html.read(), "lxml")
    result = []
    for table in bs.find_all('table'):
        if ('ZIP' in table.text):
            for tr in table.find_all('tr'):
                if ('ZIP' not in tr.text):
                    zipcode, cityState, county, area = tr.text.split('\n')
                    city, state = cityState.split(',')
                    result.append([
                        int(zipcode),
                        city.strip(),
                        state.strip(),
                        county.strip()
                    ])
    df = pd.DataFrame(result, columns=['ZIP', 'city', 'state', 'county'])
    df = df.set_index('ZIP')
    return df


# ============================================================================ #
# Execute source code
# ============================================================================ #


def requestAirQuality(urlTemplate, startParam, endParam):
    startDate = startParam.valueAsText
    endDate = endParam.valueAsText
    startYr = int(startDate[:4])
    endYr = int(endDate[:4])
    df = pd.DataFrame()
    for yr in range(startYr, endYr + 1):
        url = urlTemplate.format(yr)
        yrDf = downloadZipToDf(url)
        yrDf = genAirQualityDf(yrDf, startDate, endDate)
        df = pd.concat([df, yrDf])
    return df


def genAirQualityDf(df: pd.DataFrame, start: str = '', end: str = ''):
    if ('CBSA' in df.columns.values):
        df['GeoID'] = df['CBSA Code']
        df[['Location', 'State']] = df['CBSA'].str.split(', ', expand=True)
    else:
        geoids = [str(df['State Code'][i]).rjust(2, '0') +
                  str(df['County Code'][i]).rjust(3, '0') for i in df.index]
        df['GeoID'] = geoids
        df['Location'] = df['county Name']
    df = df.rename(columns={'Defining Parameter': 'Pollutant'})
    df['Date'] = pd.to_datetime(df['Date'])
    if (start != '') and (end != ''):
        df = df.loc[
            (df.Date >= pd.Timestamp(start)) & (df.Date <= pd.Timestamp(end))
        ]
    outCols = ['GeoID', 'Location', 'Date', 'Pollutant', 'Category', 'AQI']
    return df[outCols]


def outputTableFromDf(outputParam, df, messages):
    if (df.empty):
        messages.addWarningMessage('No data found')
    else:
        # Dataframe to structured array to table
        arr = dfToStructuredArr(df)
        arcpy.da.NumPyArrayToTable(arr, outputParam.valueAsText)
