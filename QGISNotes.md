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
Or, if the `iface.addVectorLayer` or `addRasterLayer` function was used:
```
if not layer:
	print("Layer failed to load. Please try again.")
```

### Iterating Over Layers
To iterate over the contents of a vector layer, use the following format:
```
for feature in layer.getFeatures():
	# Do something, such as:
	# Printing a list of the feature's attributes and their values
	print(feature.attributes())
```

### Updating Layers
To redraw a layer, use:
`layer.triggerRepaint()`
Or, to update the entire map canvas, use:
`iface.mapCanvas().refresh()`

To update the symbology shown in the legend entry for a layer, use:
`iface.legendInterface().refreshLayerSymbology(layer)`

### Removing Layers
To delete a layer:
`QgsProject.instance().removeMapLayer(layer_id)`

### More Information
For more information on using vector layers, go [here](https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/vector.html "Using Vector Layers").


## Editing Features

### Direct Modification
To edit a layer's features and immediately push changes to the data source (probably a file, but possibly a database, web server, etc.), use something like this (for the method DeleteFeatures):
```
if layer.dataProvider.capabilities() & layer.dataProvider().DeleteFeatures:
	res = layer.dataProvider().deleteFeatures([5, 10])
```
Here, `res` is a boolean value corresponding to the result of the operation (success or failure).
For more information, go [here](https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/vector.html#modifying-vector-layers "Modifying Vector Layers").

### Using an Editing Buffer
To determine whether a layer is in editing mode, use `layer.isEditable()`.

Must wrap editing calls (see link at end of section) in editing commands:
```
layer.beginEditCommand("Description of Actions")
# Editing commands
if problem_occurred:
  layer.destroyEditCommand()
  return
# More editing commands
layer.endEditCommand()
```

Or, for a more Pythonic alternative, use:
```
with edit(layer):
	# Editing commands
	# More editing commands
```
Here, an error will cause the edit to be canceled, and successful execution will cause the action to complete.

For more information, go [here](https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/vector.html#modifying-vector-layers-with-an-editing-buffer "Modifying Vector Layers with an Editing Buffer").

### In Practice
Successfully added a line (from [this file]( "FishingPressureStr.csv")) with the following:
```
layer = iface.activeLayer()
headers = fin.readline().strip().split(",")

line = fin.readline().strip().split(",")
feat = QgsFeature(layer.fields())
feat.setAttribute("name", line[headers.index("WaterbodyName")])
feat.setAttribute("id", line[headers.index(r"OBJECTID *")])
feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(float(line[headers.index("BEGLON")]), float(line[headers.index("BEGLAT")])), QgsPoint(float(line[headers.index("ENDLON")]), float(line[headers.index("ENDLAT")]))]))
(res, outFeats) = layer.dataProvider().addFeatures([feat])
```
Here, `res` is the boolean result of the operation, and `outFeats` is a list of all `QgsFeature` objects that were added.

Note that the second section of this code block could be wrapped in a `for line in file.readlines()`-type loop (although `readlines()` might be problematic for very large files).

Or, as in the second example above:
```
layer = iface.activeLayer()
headers = fin.readline().strip().split(",")

line = fin.readline().strip().split(",")
with edit(layer):
	feat = QgsFeature(layer.fields())
	feat.setAttribute("name", line[headers.index("WaterbodyName")])
	feat.setAttribute("id", line[headers.index(r"OBJECTID *")])
	feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(float(line[headers.index("BEGLON")]), float(line[headers.index("BEGLAT")])), QgsPoint(float(line[headers.index("ENDLON")]), float(line[headers.index("ENDLAT")]))]))
	(res, outFeats) = layer.dataProvider().addFeatures([feat])
```


## Optimization

### Spatial Indexes
Spatial indexes can dramatically improve the performance of code that makes frequent queries to a vector layer.

To create a spatial index containing all of `layer`'s features: `index = QgsSpatialIndex(layer.getFeatures())`

Then, use something like `nearest = index.nearestNeighbor(QgsPoint(25.4, 12.7), 5)` or `intersect = index.intersects(QgsRectangle(22.5, 15.3, 23.1, 17.2))`.


## Route Finding

### OpenRouteService
There is a [Python library for OpenRouteService](https://github.com/GIScience/openrouteservice-py). It facilitates easy access to ORS functions, and provides the results as native Python data structures (lists, dicts, etc).
ORS limits API queries to **2500 per day**, but users can [contact them](https://openrouteservice.org/contact/) to request quota increases as necessary for their use case(s).

**The API requires that input coordinates be in the format [LON, LAT].** This is the opposite of the normal order, and can be achieved with `revCoords = (coords[0][::-1], coords[1][::-1])` (where `coords` is a tuple containing the original two points).
