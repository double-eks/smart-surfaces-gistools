import io
import ssl
import zipfile

import arcpy
import numpy as np
import pandas as pd
import requests
import urllib3


def genParam(name: str,
             dataType: str = 'GPString',
             parameterType='Required',
             isInput: bool = True,
             isVisible: bool = True,
             isFiltered: bool = False,
             filterType: str = 'ValueList',
             listOptions: list = []):
    strictName = name
    if (' ' in name):
        strictName = strictName.replace(' ', '-')
    paramDir = 'Input' if (isInput) else 'Output'
    param = arcpy.Parameter(
        displayName=name,
        name=strictName,
        datatype=dataType,
        parameterType=parameterType,
        direction=paramDir
    )
    param.enabled = isVisible
    if (isFiltered) or (filterType != 'ValueList'):
        param.filter.type = filterType
    if (listOptions != []):
        param.filter.type = 'ValueList'
        param.filter.list = listOptions
    return param


def genDateParam(name: str):
    return genParam(name, dataType='Date')


def enableChildParam(parent, *args):
    if (parent.value):
        for arg in args:
            if (not arg.enabled):
                arg.enabled = True


def formatDateOnly(*args):
    for arg in args:
        if (arg.datatype == 'Date'):
            if (arg.value) and (' ' in arg.valueAsText):
                dateTime = arg.valueAsText
                arg.value = dateTime[: dateTime.index(' ')]


def dfToStructuredArr(df: pd.DataFrame):
    newTypes = []
    for col in df:
        colType = df[col].dtype.str
        if ('O' in colType):
            fieldType = '<U128'
        else:
            fieldType = colType
        newTypes.append((col, fieldType))
    arr = df.to_records(index=False)
    arr = arr.astype(newTypes)
    return arr


def downloadZipToDf(url: str):
    response = get_legacy_session().get(url)
    if (response.status_code != 200):
        return pd.DataFrame()
    zippedFile = zipfile.ZipFile(io.BytesIO(response.content))
    csvFilename = zippedFile.namelist()[0]
    csvFile = zippedFile.open(csvFilename)
    df = pd.read_csv(csvFile)
    csvFile.close()
    zippedFile.close()
    return df


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
