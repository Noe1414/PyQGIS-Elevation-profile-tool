# Elevation profile tool

**WARNING : This code has to be run with the QGIS Python console. An error will occur if the code is run outside the application**

The purpose of this code is to create an elevation profile figure just by using a shapefile. 
The API used to get the elevation is from the IGN (Institut national de l'information géographique et forestière).
As a consequence, **this elevation profile tool will only work with shapefile data from France**.


When the code is run, the user can choose if he wants to export the data in a .csv  file as well.

Every API request can handle ~175 values. 

## How it works 

Here are the different steps of the code in order to go from a *.shp* file to an elevation profile :

![alt text](https://raw.githubusercontent.com/Noe1414/PyQGIS-Elevation-profile-tool/main/Images/ToolOperation.png)


The input used in the API are a list of latitudes and and a list of longitudes in WGS 84. The API returns a list of elevation in meters.

![alt text](https://raw.githubusercontent.com/Noe1414/PyQGIS-Elevation-profile-tool/main/Images/API_IGN.png)


