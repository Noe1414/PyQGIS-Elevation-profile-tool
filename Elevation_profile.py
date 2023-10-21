#Import des différents modules


from PyQt5.QtWidgets import * 
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import * 
from PyQt5.QtCore import * 
from math import *
import json
import pandas as pd
import requests
import matplotlib.pyplot as plt
import sys
import os
import re
from qgis.PyQt.QtCore import (
    QPointF,
    QRectF,
    QSize
)
from qgis.core import QgsProject, QgsLayout, QgsLayoutAtlas, QgsExpressionContext, QgsProject, QgsExpressionContextUtils, QgsLayoutItemMap


# Display a file dialog for opening a file
file_dialog = QFileDialog()
shp_file_path, _ = file_dialog.getOpenFileName(None, "Select a shp file", "", "Shapefiles (*.shp)")

if shp_file_path:
    print("Selected file:", shp_file_path)
else:
    print("User canceled the file selection.")


directory_path = QFileDialog.getExistingDirectory(None, "Select a directory to save the elevation profiles", "")
if directory_path:
    print("Selected directory:", directory_path)
else:
    print("User canceled the directory selection.")

shp_elt = QgsVectorLayer(shp_file_path, "Shp layer", "ogr")

#Ask to the user if he wants to export a csv file of the values as well

def ask_yes_no_question(question_text):
    msg_box = QMessageBox()
    msg_box.setText(question_text)
    msg_box.setIcon(QMessageBox.Question)
    msg_box.setWindowTitle("Yes/No Question")
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    result = msg_box.exec_()

    return result == QMessageBox.Yes

question_text = "Do you want to export values in a csv file ?"
user_response = ask_yes_no_question(question_text)

"""
Functions
"""

#The following function calculates the length of the polyline in order to create the profile
    
def calculate_segment_lengths(layer):
    segment_lengths = []

    # Define the projected CRS (e.g., EPSG:3857)
    projected_crs = QgsCoordinateReferenceSystem('EPSG:2154')

    # Create a coordinate transform from the layer's CRS to the projected CRS
    transform = QgsCoordinateTransform(layer.crs(), projected_crs, QgsProject.instance())
    for feature in layer.getFeatures():
        res=[]
        geometry = feature.geometry()
        if geometry.wkbType() == 2:
            multi_line = geometry.asPolyline()
            
            # Reproject the line to the projected CRS
            reprojected_line = [transform.transform(QgsPointXY(x, y)) for x, y in multi_line]

            for i in range(1, len(reprojected_line)):
                segment_length = QgsPointXY(reprojected_line[i - 1]).distance(QgsPointXY(reprojected_line[i]))
                res.append(segment_length)
        if geometry.wkbType() == 5:
            multi_line = geometry.asMultiPolyline()
            
            for line in multi_line:
                # Reproject the line to the projected CRS
                reprojected_line = [transform.transform(QgsPointXY(x, y)) for x, y in line]

                for i in range(1, len(reprojected_line)):
                    segment_length = QgsPointXY(reprojected_line[i - 1]).distance(QgsPointXY(reprojected_line[i]))
                    res.append(segment_length)
        segment_lengths.append(res)
    return segment_lengths

#To avoid errors depending on the version of QGIS

def convert_qvariant_to_python(qvariant):

    if qvariant is None:
        return None
    elif isinstance(qvariant, QgsField):
        return qvariant.name()
    elif str(type(qvariant)) == "<class 'int'>":
        return int(qvariant)
    elif str(type(qvariant)) == "<class 'float'>":
        return float(qvariant)
    elif str(type(qvariant)) == "<class 'str'>":
        return str(qvariant)
    else:
        return str(qvariant)

#Transforms a shp to json
def layer_to_json(layer):
    features = []
    
    # Iterate over the features in the layer
    for feature in layer.getFeatures():
        #attributes = feature.attributes()
        attributes = {field.name(): convert_qvariant_to_python(feature.attribute(field.name())) for field in feature.fields()}
        geometry = feature.geometry().asJson()
        
        # Create a dictionary for each feature
        feature_dict = {
            'attributes': attributes,
            'geometry': json.loads(geometry),
        }
        
        # Append the feature dictionary to the list
        features.append(feature_dict)
    
    # Create the JSON object
    json_object = {
        'type': 'FeatureCollection',
        'features': features,
    }
    
    return json.dumps(json_object)
    
#The get request sent to the API
def get_elevation(latitude, longitude):
    url = f"https://wxs.ign.fr/calcul/alti/rest/elevation.json"
    params = {
        "lon": longitude,
        "lat": latitude,
        "delimiter": ","
    }

    response = requests.get(url, params=params, verify=False)
    data = response.json()
    
    res=[]
    if "elevations" in data:
        for i in range(0,len(data["elevations"])):
            res.append(data["elevations"][i]["z"])
        return res
    else:
        print("Une erreur s'est produite.")
        return None


#Transform the layer to WGS 84, the geodetic system used by the API

couche_origine=shp_elt
couche_transformee = QgsVectorLayer('LineString?crs=EPSG:4326', 'Couche transformée', 'memory')

crs_origine = couche_origine.crs()
crs_destination = QgsCoordinateReferenceSystem('EPSG:4326')  # Projection de destination
transform = QgsCoordinateTransform(crs_origine, crs_destination, QgsProject.instance())


# Copy entities to the transformed layer
indices=[]
for entite in couche_origine.getFeatures():
    nomGraphique = str(entite.id())
    indices.append(nomGraphique)
    geom_origine = entite.geometry()
    geom_copie = QgsGeometry(geom_origine)
    geom_copie.transform(transform)
    
    nouvelle_entite = QgsFeature()
    nouvelle_entite.setGeometry(geom_copie)
    nouvelle_entite.setAttributes(entite.attributes())
    
    couche_transformee.dataProvider().addFeature(nouvelle_entite)

"""
# Enregistrer la couche transformée
chemin_couche_transformee = path + '/SHP/layer.shp'
QgsVectorFileWriter.writeAsVectorFormat(couche_transformee, chemin_couche_transformee, 'UTF-8', couche_transformee.crs(), 'ESRI Shapefile')

"""
#Densify the layer

layer = couche_transformee
geometry_values={}
if layer.isValid():
    layer.startEditing()

    # Récupérer le fournisseur de données de la couche
    provider = layer.dataProvider()
    
    # Densify each feature in the layer
    for feature in layer.getFeatures():
        
        # Récupérer l'identifiant unique de la fonctionnalité
        feature_id = feature.id()

        # Obtenir la géométrie d'origine de la fonctionnalité
        original_geometry = feature.geometry()
        
        length = original_geometry.length()
        # Modifier la géométrie selon vos besoins
        modified_geometry = original_geometry.densifyByDistance(length/250)
        # Ajouter la nouvelle géométrie au dictionnaire de valeurs de géométrie
        geometry_values[feature_id] = modified_geometry
        
    # Save the changes to the shapefile
    provider.changeGeometryValues(geometry_values)
    layer.commitChanges()


json_data = layer_to_json(couche_transformee)
segment_lengths = calculate_segment_lengths(couche_transformee)

# Iterate every element of the layer
for i in range(len(json.loads(json_data)["features"])):
    x=[0]
    count=0
    
    for l in segment_lengths[i]:
        count+=l
        x.append(count)
    
    coord = json.loads(json_data)["features"][i]["geometry"]["coordinates"]
    
    latitude = []  # Latitude du point
    longitude = []  # Longitude du point
    

    for c in coord:
        latitude.append(c[1])
        longitude.append(c[0])
    
    #The number of values we input in the API is limitated, so we will separate the list in 2 to do 2 requests and improve the precision of the elevation profile

    l = round(len(latitude)/2)
    latitude1 = latitude[:l]
    latitude2 = latitude[l:]
    longitude1 = longitude[:l]
    longitude2 = longitude[l:]
    altitude1 = get_elevation(latitude1, longitude1)
    altitude2 = get_elevation(latitude2, longitude2)
    
    altitude = altitude1 + altitude2

    # Données pour l'axe des abscisses (x) et des ordonnées (y)

    #CSV Export
    
    if user_response:
        df = pd.DataFrame(list(zip(x,altitude)))
        df.to_csv(directory_path+"/profil_"+str(indices[i])+".csv",sep=";",index=None)

    # Plot the elevation profile and save it
    plt.figure(figsize=(10,6), dpi=200)
    plt.plot(x, altitude,linewidth='2')
    plt.scatter(x[0],altitude[0],c='black',s=100)
    plt.scatter(x[0],altitude[0],c='white',s=80)
    plt.scatter(x[-1],altitude[-1],c='black',s=100)
    plt.scatter(x[-1],altitude[-1],c='white',s=80)
    """
    t1 = plt.text(x[0],altitude[0],str(altitude[0])+' m',va='top')
    t2 = plt.text(x[-1],altitude[-1],str(altitude[-1])+' m',va='top')
    t1.set_bbox(dict(facecolor='white', alpha=0.3, edgecolor='white'))
    t2.set_bbox(dict(facecolor='white', alpha=0.3, edgecolor='white'))
    """
    # Personnalisation du graphique
    plt.rcParams.update({'font.size': 15})
    plt.xlabel('Length  (m)')
    plt.ylabel('Altitude (m)')
    plt.title('Elevation profile')
    plt.grid()
    plt.savefig(directory_path+"/profil_"+str(indices[i])+".png",bbox_inches='tight')
    # Afficher le graphique
    # plt.show()
