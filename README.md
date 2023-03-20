# ArcGIS Pro Toolboxes for Smart Surfaces Group, CMU SoA

This is a package of ArcGIS Pro geoprocessing toolboxes developed by Sean X. from _Carnegie Mellon University_

## Table of Content

1. Introduction\
   [How to Use](#how-to-use)
2. Join Toolbox\
   [Join Multiple Tables to Feature](#Join1)
3. Air Quality Toolbox\
   [Request Daily AQI by ZIP](#aq1)\
   [Request Daily AQI by County](#aq2)
<br>

<a id="how-to-use"></a>

## How to Use

1. Download the Zip file and decompress
2. Make sure all the **.pyt** (ArcGIS python toolbox file) and **.py** files are in the same dictionary
3. Open ArcGIS Pro **Catalog Panel** -> **Toolboxes** -> **Add Toolbox**
4. Add one \***\*Toolbox.pyt**, choose one geoprocessing tool in the toolbox, and go!

<br>

<a id="Join1"></a>

## (<u><i>JoinToolbox.pyt</i></u>) Join Multiple Tables to Feature

### Tutorial Demo

https://drive.google.com/file/d/1nNYymfaDuDgh_RblMPtXlNQWrRB2ruo-/view?usp=sharing

### Usage

By using this tool **once**, you can
- streamline repetitive tasks 
- avoid concerns about the various types of GEOID data, such as int/float to text.

### Parameters

- Parameters for target feature:\
  <u>Input Feature</u>, <u>GeoID Field</u>, <u>Input Fields to Keep</u>
- Parameters for join table(s):\
  <u>Input Folder</u>, <u>Input Tables</u>

| Parameter                                | Direction        | Data Type           | Explanation                                                                                                                                |
| ---------------------------------------- | ---------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Input Feature                            | Input            | Feature class/layer | The feature (polygon preferred) contains a GEOID field (required), such as tracts, blocks, counties, etc., on which the join will be based |
| GeoID Field                              | Input            | Field               | The digit ID field (data-type <b>insensitive</b>)                                                                                          |
| Input Fields to Keep                     | Input            | Field(s)            | The field(s) of <b>Input Feature</b> will be kept in the new feature class, which always includes <b>GeoID Field</b>                       |
| Input Folder                             | Input            | Folder path         | The path of folder with all cleaned tables                                                                                                 |
| Input Tables<sup>1</sup>                 | Input            | Table path(s)       | Automatically read all the table files in the <b>Input Folder</b>                                                                          |
| Output Table                             | Output           | Feature Table       |                                                                                                                                            |
| Whether to Save Output Table<sup>2</sup> | Input (optional) | Boolean             | Uncheck as default                                                                                                                         |
| Output Feature                           | Output           | Feature Class       | The result contains GEOID, all the data fields, and the specified fields from the Input Feature (optional)                                 |

1.  It is a good idea to put all the cleaned tables in one same folder. Please note that each table should just include a GEOID column and the data column(s) you need, as the former is for the join and the latter will be joined to the output feature
2.  If you want to keep a feature table as a backup saved in the geodatabase, check this option. Usually it is ok to leave it unchecked

<br>

<a id="aq1"></a>

## (<u><i>AirQualityToolbox.pyt</i></u>) Request Daily AQI by ZIP

### Usage

- Request daily air quality data for a **city** or **county** from EPA Air Quality System in a given time range
- Output a feature table of cleaned data

### Parameters

<i>coming soon</i>

<br>
<a id="aq2"></a>

## (<u><i>AirQualityToolbox.pyt</i></u>) Request Daily AQI by County

### Usage

- Input a county (polygon) feature layer/class to request daily air quality data for a **county** or **counties** from EPA Air Quality System in a given time range
- Output a feature table of cleaned data
  <br>_p.s. should be a bulk of data. total rows = input county count \* requested days_</br>

### Parameters

<i>coming soon</i>

<br>

## Data Source Credit

### AirQualityToolbox.pyt

- US EPA Air Quality System (AQS) - [Air Quality Data Collected at Outdoor Monitors Across the US](https://www.epa.gov/outdoor-air-quality-data)
