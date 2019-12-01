# Script to import data from a delimited file in which each row (object)
# contains two sets of coordinates - say, BEGLAT, BEGLON, ENDLAT, and ENDLON -
# which correspond to the start- and endpoints of a line.
# By Lucas Ritzdorf

from qgis.core import *
import qgis.utils
from itertools import (takewhile,repeat)
from PyQt5.QtWidgets import QFileDialog

# Supply path to QGIS install location
QgsApplication.setPrefixPath(r"C:/Program Files/QGIS 3.4", True)
# Initialize the application, using False to indicate that a GUI is not present
qgs = QgsApplication([], False)
qgs.initQgis()


# Define default header names and prompts
headerNames = (idHeader, nameHeader, begLat, begLon, endLat, endLon)
defaultNames = (r"OBJECTID *", "WaterbodyName", "BEGLAT", "BEGLON", "ENDLAT",\
                "ENDLON")
headerPrompts = ("Object ID column", "Object Name", "Starting Latitude",\
                 "Starting Longitude", "Ending Latitude", "Ending Longitude")

# Prompt user for header names, if known
print("Enter the following column header names, if known. If not, press enter "\
      "to skip.\n(You may need to view the file in a text editor.)")
for n in range(len(headerNames)):
    headerNames[n] = input(headerPrompts[n] + ": ")

# Process input
for n in range(len(headerNames):
    if headerNames[n] == "":
        item = defaultNames[n]

# Set up input file
fileName,ignore = QFileDialog.getOpenFileName()
del ignore

def lineCount(filename):
    f = open(filename, 'rb')
    bufgen = takewhile(lambda x: x, (f.raw.read(1024*1024) for _ in repeat(None)))
    return sum( buf.count(b'\n') for buf in bufgen )

numLines = lineCount(fileName)
importFails = [0,0]
layer = QgsVectorLayer(\
    "Linestring?crs=epsg:4326&field=id:integer&field=name:string(80)",\
    "Test Layer", "memory")
fin = open(fileName, "r")
headers = fin.readline().strip().split(",")
with edit(layer):
    for lineNum in range(numLines):
        try:
            line = fin.readline().strip().split(",")
            feat = QgsFeature(layer.fields())
            feat.setAttribute("name", line[headers.index(nameHeader)])
            feat.setAttribute("id", line[headers.index(idHeader)])
            feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(float(line[\
                headers.index(begLon)]), float(line[headers.index(begLat)])),\
                QgsPoint(float(line[headers.index(endLon)]), float(line[\
                headers.index(endLat)]))]))
            (res, outFeats) = layer.dataProvider().addFeatures([feat])
            if res == False: importFails[0] += 1
        except ValueError:
            importFails[1] += 1
        except IndexError:
            if line == ['']: print("Blank line at line", lineNum)
            else: importFails[1] += 1
fin.close()
print(sum(importFails), "feature(s) failed to import;", importFails[1],\
    "of those had missing data")

# Export the layer to a Shapefile
error, ignore = QgsVectorFileWriter.writeAsVectorFormat(layer,\
    r"C:/Users/Lucas Ritzdorf/Documents/Science Fair/2019/Data/Test Layer.shp",\
    "utf-8", QgsCoordinateReferenceSystem(None), "ESRI Shapefile")
del ignore
if error != 0: print("Error exporting layer to Shapefile")


qgs.exitQgis()
