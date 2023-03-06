import re
from datetime import date, datetime
from urllib.request import urlopen

import arcpy
import pandas as pd
from bs4 import BeautifulSoup

from templates import (dfToStructuredArr, downloadZipToDf, enableChildParam,
                       formatDateOnly, genDateParam, genParam)

# ============================================================================ #
# Initial tool object
# ============================================================================ #


class RequestByCityCounty(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = 'Request Air Quality Data by City/County'
        self.description = ""
        self.canRunInBackground = False

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def getParameterInfo(self):
        """Define parameter definitions"""
        # Input parameters
        timeFrame = genParam('Time Frame', listOptions=['daily', 'hourly'])
        spaceScale = genParam(
            'Request for', listOptions=['city', 'county'])
        zipCode = genParam('Use Any Zip in the Area to Look Up City-County-State',
                           dataType='Long', isVisible=False)
        state = genParam('State', isVisible=False)
        location = genParam('Location', isVisible=False)
        lookup = genParam('Check LookUp Location Before Go',
                          dataType='Boolean', isVisible=False)
        startDate = genDateParam('Start Date')
        endDate = genDateParam('End Date')
        # Set parameter dependency
        state.parameterDependencies = [zipCode.name]
        location.parameterDependencies = [zipCode.name]
        lookup.parameterDependencies = [zipCode.name]
        endDate.parameterDependencies = [startDate.name]
        # Output parameter
        table = genParam('Output Table', dataType='Table', isInput=False)
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

        enableChildParam(scaleParam, zipParam)
        enableChildParam(zipParam, stateParam, locParam, checkParam)
        formatDateOnly(startParam, endParam)

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

        if (startParam.value) and (not endParam.value):
            startyr = int(startParam.valueAsText[:4])
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
        # Filter time
        rows = (df.Date >= pd.Timestamp(startDate)) & (
            df.Date <= pd.Timestamp(endDate))
        df = df.loc[rows]
        if (df.empty):
            messages.addWarningMessage('No data found')
        else:
            # Dataframe to structured array to table
            arr = dfToStructuredArr(df)
            arcpy.da.NumPyArrayToTable(arr, outTable)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


# ============================================================================ #
# Define parameters
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


def requestSingleYr(timeFrame: str, scale: str, state: str, location: str,
                    year: int, messages):
    # Request table zip and convert to df
    scale = 'county' if ('county' in scale) else 'cbsa'
    urlTemplate = 'https://aqs.epa.gov/aqsweb/airdata/{}_aqi_by_{}_{}.zip'
    url = urlTemplate.format(timeFrame, scale, year)
    df = downloadZipToDf(url)
    if (df.empty):
        messages.addWarningMessage(f'No data available in {year}')
    else:  # Clean fields
        filterField = 'county Name' if ('county' in scale) else 'CBSA'
        keys = ['Date', 'AQI', 'Category', 'Defining Parameter']
        if (filterField == 'CBSA'):
            col = '{}, {}'.format(location.capitalize(),
                                  state.upper())
        else:
            col = location
        df = df[df[filterField] == col]
        df = df[keys]
        df['Date'] = pd.to_datetime(df['Date'])
        df[state] = state
        df[location] = location
        df = df.rename(columns={'Defining Parameter': 'Pollutant'})
    return df
