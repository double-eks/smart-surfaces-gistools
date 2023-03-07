# -*- coding: utf-8 -*-

import arcpy
import pandas as pd

from AirQualitySystem import CountyAirQuality, RequestByCityCounty

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
        self.tools = [RequestByCityCounty, CountyAirQuality]


'''
# ============================================================================ #
# Tool
# ============================================================================ #


class AirNowByLoc(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = 'Request Air Quality Data by Coordinate'
        self.description = ""
        self.canRunInBackground = False

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def getParameterInfo(self):
        """Define parameter definitions"""
        # Parametes relevant to input table
        inputFeature = self.genListParam(
            'Input Feature', data=['Feature Class', 'Feature Layer'],
            visible=True, isList=False)
        lon = self.genListParam('Longitude', data='Field', isList=False)
        lat = self.genListParam('Latitude', data='Field', isList=False)
        lon.filter.list = ['Double', 'Float']
        lat.filter.list = ['Double', 'Float']
        # Parametes relevant to date/time
        interval = self.genListParam('Time Interval', visible=True,
                                     options=['daily', 'weekly', 'biweekly',
                                              'monthly', 'yearly'])
        startDate = self.genListParam('State Date', data='Date', isList=False)
        endDate = self.genListParam('End Date', data='Date', isList=False)
        rateLimit = self.genListParam('Requested Rows',
                                      data='Long', isList=False)

        # Set parameter dependency
        lon.parameterDependencies = [inputFeature.name]
        lat.parameterDependencies = [inputFeature.name]
        endDate.parameterDependencies = [startDate.name]
        # Output parameter
        # table = arcpy.Parameter(
        #     displayName='Output Table',
        #     name='Output-Table',
        #     datatype='Table',
        #     parameterType='Required',
        #     direction='Output'
        # )
        # Set the parameter properties
        params = [
            inputFeature,
            lon,
            lat,
            interval,
            startDate,
            endDate,
            rateLimit
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
        inputParam = parameters[0]
        lonParam = parameters[1]
        latParam = parameters[2]
        intervalParam = parameters[3]
        startParam = parameters[4]
        endParam = parameters[5]
        countParam = parameters[6]

        enableChildParam(inputParam, lonParam, latParam)
        enableChildParam(intervalParam, startParam, endParam)
        validateDateParam(startParam)
        validateDateParam(endParam)

        if (inputParam.value) and (intervalParam.value) and (startParam.value) and (endParam.value):
            if (not countParam.enabled):
                countParam.enabled = True
            count = calculateRequests(inputParam, intervalParam,
                                      startParam, endParam)
            countParam.value = count

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        startParam = parameters[4]
        endParam = parameters[5]
        countParam = parameters[6]
        validateDateParam(startParam, message=True)
        validateDateParam(endParam, message=True)
        if (countParam.value) and (countParam.value > 500):
            countParam.setErrorMessage('Exceed request rate limits (500/hr)')

    # def execute(self, parameters, messages):
    #     """The source code of the tool."""
    #     timeFrame = parameters[0].valueAsText
    #     scale = parameters[1].valueAsText
    #     state = parameters[3].valueAsText
    #     location = parameters[4].valueAsText
    #     startDate = parameters[6].valueAsText
    #     endDate = parameters[7].valueAsText
    #     startYr = int(startDate[:4])
    #     endYr = int(endDate[:4])
    #     outTable = parameters[8].valueAsText
    #     # Request air data
    #     df = pd.DataFrame()
    #     for yr in range(startYr, endYr + 1):
    #         yrDf = requestSingleYr(timeFrame, scale, state, location,
    #                                yr, messages)
    #         df = pd.concat([df, yrDf])
    #     df = df.loc[startDate: endDate]
    #     # Convert dataframe to array to table feature
    #     arr = df.to_records()
    #     arr = arr.astype([
    #         ('Date', 'datetime64[h]'),
    #         ('AQI', '<i8'),
    #         ('Category', '<U64'),
    #         ('Pollutant', '<U64'),
    #         ('State', '<U64'),
    #         ('Location', '<U64')
    #     ])
    #     arcpy.da.NumPyArrayToTable(arr, outTable)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return


def enableChildParam(parent, *args):
    if (parent.value):
        for arg in args:
            if (not arg.enabled):
                arg.enabled = True


def validateDateParam(param, message: bool = False):
    if (not message):
        if (param.value) and (' ' in param.valueAsText):
            dateTime = param.valueAsText
            param.value = dateTime[: dateTime.index(' ')]
    else:
        if (param.value) and (param.value > datetime.now()):
            param.setErrorMessage('Exceed date availability')


def calculateRequests(inputParam, intervalParam, startParam, endParam):
    rows = int(arcpy.GetCount_management(inputParam.value).getOutput(0))
    days = {
        'daily': 1, 'weekly': 7, 'biweekly': 14, 'monthly': 30, 'yearly': 365
    }
    interval = days[intervalParam.valueAsText.lower()]
    delta = endParam.value - startParam.value
    requestedDayCount = delta.days // interval * rows
    return requestedDayCount


# ============================================================================ #
# Source code
# ============================================================================ #


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
'''
