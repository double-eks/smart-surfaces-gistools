# -*- coding: utf-8 -*-
import io
import re
import ssl
import zipfile
from datetime import date, datetime
from urllib.request import urlopen

import arcpy
import pandas as pd
import requests
import urllib3
from bs4 import BeautifulSoup

arcpy.env.overwriteOutput = True

# ============================================================================ #
# Adjust request setting for ArcGIS Pro (win)
# ============================================================================ #


class CustomHttpAdapter (requests.adapters.HTTPAdapter):
    # "Transport adapter" that allows us to use custom ssl_context.

    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_context=self.ssl_context)


def get_legacy_session():
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
    session = requests.session()
    session.mount('https://', CustomHttpAdapter(ctx))
    return session


# ============================================================================ #
# Tool
# ============================================================================ #


class AirQualitySystem(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Request AQS Data"
        self.description = ""
        self.canRunInBackground = False

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def getParameterInfo(self):
        """Define parameter definitions"""
        # Input parameters
        timeFrame = self.genListParam('Time Frame', visible=True,
                                      options=['daily', 'hourly'])
        spaceScale = self.genListParam('Request Data by', visible=True,
                                       options=['city', 'county'])
        zipCode = self.genListParam('Use Any Zip in the Area to Look Up City-County-State',
                                    data='Long', isList=False)
        state = self.genListParam('State')
        location = self.genListParam('Location')
        lookup = self.genListParam('Check LookUp Location Before Go',
                                   data='Boolean', isList=False)
        startDate = self.genListParam('State Date', data='Date',
                                      visible=True, isList=False)
        endDate = self.genListParam('End Date', data='Date',
                                    visible=True, isList=False)
        # Set parameter dependency
        state.parameterDependencies = [zipCode.name]
        location.parameterDependencies = [zipCode.name]
        lookup.parameterDependencies = [zipCode.name]
        endDate.parameterDependencies = [startDate.name]
        # Output parameter
        table = arcpy.Parameter(
            displayName='Output Table',
            name='Output-Table',
            datatype='Table',
            parameterType='Required',
            direction='Output'
        )
        # Set the parameter properties
        params = [
            timeFrame,
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

    def genListParam(self, name: str, data: str = 'GPString',
                     visible: bool = False, isList: bool = True,
                     options: list = []):
        alias = name
        if (' ' in name):
            alias = alias.replace(' ', '-')
        param = arcpy.Parameter(
            displayName=name,
            name=alias,
            datatype=data,
            parameterType='Required',
            direction='Input'
        )
        param.enabled = visible
        if (isList):
            param.filter.type = 'ValueList'
            if (options != []):
                param.filter.list = options
        return param

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        scaleParam = parameters[1]
        zipParam = parameters[2]
        stateParam = parameters[3]
        locParam = parameters[4]
        checkParam = parameters[5]
        startParam = parameters[6]
        endParam = parameters[7]
        outputParam = parameters[8]

        if (scaleParam.value):
            if (not zipParam.enabled):
                zipParam.enabled = True

        if (zipParam.value):
            if (not stateParam.enabled):
                stateParam.enabled = True
                locParam.enabled = True
                checkParam.enabled = True
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

        if (startParam.value):
            start = startParam.valueAsText
            if (' ' in start):
                startParam.value = start[:start.index(' ')]
            if (not endParam.value):
                startyr = int(start[:4])
                endParam.value = date(startyr, 12, 31).strftime('%Y/%m/%d')

        if (scaleParam.value) and (locParam.value) and (startParam.value):
            if (not outputParam.altered):
                tableName = '{}_{}_{}_aqi'.format(
                    locParam.valueAsText,
                    startParam.valueAsText[:4],
                    parameters[0].valueAsText
                ).lower()
                tableName = tableName.replace(' ', '_')
                outputParam.value = arcpy.env.workspace + '\\' + tableName

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        zipParam = parameters[2]
        startParam = parameters[6]
        endParam = parameters[7]
        if (zipParam.value):
            if (re.search(r'^\d{5}$', zipParam.valueAsText) == None):
                zipParam.setErrorMessage('Invalid zip code')
        if (startParam.value) and (endParam.value):
            if (startParam.value >= endParam.value):
                endParam.setErrorMessage('Invalid end date')
            if (startParam.value > datetime(2022, 12, 31)):
                startParam.setErrorMessage('No data available')
            if (endParam.value > datetime(2022, 12, 31)):
                endParam.setWarningMessage('No data available since 2023')
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        timeFrame = parameters[0].valueAsText
        scale = parameters[1].valueAsText
        state = parameters[3].valueAsText
        location = parameters[4].valueAsText
        startDate = parameters[6].valueAsText
        endDate = parameters[7].valueAsText
        startYr = int(startDate[:4])
        endYr = int(endDate[:4])
        outTable = parameters[8].valueAsText
        # Request air data
        df = pd.DataFrame()
        for yr in range(startYr, endYr + 1):
            yrDf = requestSingleYr(timeFrame, scale, state, location,
                                   yr, messages)
            df = pd.concat([df, yrDf])
        df = df.loc[startDate: endDate]
        # Convert dataframe to array to table feature
        arr = df.to_records()
        arr = arr.astype([
            ('Date', 'datetime64[h]'),
            ('AQI', '<i8'),
            ('Category', '<U64'),
            ('Pollutant', '<U64'),
            ('State', '<U64'),
            ('Location', '<U64')
        ])
        arcpy.da.NumPyArrayToTable(arr, outTable)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


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
# Source code
# ============================================================================ #


def requestSingleYr(timeFrame: str, scale: str, state: str, location: str,
                    year: int, messages):
    # Request table zip
    scale = 'county' if ('county' in scale) else 'cbsa'
    urlTemplate = 'https://aqs.epa.gov/aqsweb/airdata/{}_aqi_by_{}_{}.zip'
    url = urlTemplate.format(timeFrame, scale, year)
    response = get_legacy_session().get(url)
    if (response.status_code != 200):
        messages.addWarningMessage(f'No data available in {year}')
        return pd.DataFrame()
    # Convert zip file to data frame
    zippedFile = zipfile.ZipFile(io.BytesIO(response.content))
    csvFilename = zippedFile.namelist()[0]
    csvFile = zippedFile.open(csvFilename)
    df = pd.read_csv(csvFile)
    csvFile.close()
    zippedFile.close()
    # Clean fields
    filterField = 'county Name' if ('county' in scale) else 'CBSA'
    df = filterDfByScale(df, state, location, filterField)
    return df


def filterDfByScale(df: pd.DataFrame, state: str, location: str, field: str):
    keys = ['Date', 'AQI', 'Category', 'Defining Parameter']
    if (field == 'CBSA'):
        col = '{}, {}'.format(location.capitalize(),
                              state.upper())
    else:
        col = location
    df = df[df[field] == col]
    df = df[keys]
    df[state] = state
    df[location] = location
    df = df.rename(columns={'Defining Parameter': 'Pollutant'})
    df = df.set_index('Date')
    df.index = pd.to_datetime(df.index)
    return df
