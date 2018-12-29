# QGIS + Python Notes


## QGIS Startup Python Script
Must be located at: `C:\Users\Lucas Ritzdorf\AppData\Roaming\QGIS\QGIS3\profiles\default\python\startup.py`


## Layers
### Loading Delimited Text
To load a vector layer from a delimited text file, use:
`uri = "/path/to/file.csv?delimiter={}&xField={}&yField={}".format(delimiter, lonFieldName, latFieldName)`

And either:
`layer = QgsVectorLayer(uri, layerName, "delimitedtext")`

Or:
`layer = iface.addVectorLayer(uri, layerName, "delimitedtext")`

### Loading Shapefiles
To load a Shapefile layer, use:
`layer = QgsVectorLayer("/path/to/shapefile.shp", "layerName", "ogr")`

### Checking for Successful Loading
Check that the layer was loaded correctly with:
```
if not layer.isValid():
	print("Layer failed to load. Please try again.")
```
Or, if the `iface.addVectorLayer` function was used:
```
if not layer:
	print("Layer failed to load. Please try again.")
```
