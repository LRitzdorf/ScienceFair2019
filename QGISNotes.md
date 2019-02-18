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

**The API requires that input coordinates be in the format [LON, LAT].** This is the opposite of the normal order, and can be achieved with `revCoords = [ item[::-1] for item in coords ]` (where `coords` is a tuple of 2-tuples, each representing a point).

#### Example (Kalispell to Ashley Lake)
```
import openrouteservice
end = (-114.63478,48.19400)
start = (-114.31506,48.20218)
client = openrouteservice.Client(key='5b3ce3597851110001cf6248e3379d3da4854bb79887b36149de715d')
routes = client.directions((start,end))
encoded = routes['routes'][0]['geometry']
decoded = openrouteservice.convert.decode_polyline(encoded)
layer = QgsVectorLayer("LineString", "Kalispell to Ashley Lake", "memory")
provider = layer.dataProvider()
feat = QgsFeature()
feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(pt[0],pt[1]) for pt in decoded['coordinates']]))
provider.addFeature(feat)
QgsProject.instance().addMapLayer(layer)
import processing
result = processing.run('qgis:densifygeometriesgivenaninterval', {
	'INPUT':layer,
	'INTERVAL':0.001,
	'OUTPUT':'memory:'
	})
result2 = processing.runAndLoadResults('native:extractvertices', {
	'INPUT':result['OUTPUT'],
	'OUTPUT':'memory:'
	})
for layer in QgsProject.instance().mapLayers().values():
	if layer.id() == result2['OUTPUT']:
		addedLayer = layer
addedLayer.renderer().setColorRamp(QgsGradientColorRamp(QColor('transparent'),QColor(227,26,28)))
addedLayer.renderer().setRadiusUnit(1)
addedLayer.renderer().setRadius(500)
```
Use `addedLayer.renderer().setWeightExpression(exp)` to set the weighting expression for each feature.

The `routes` object is:
{'routes': [{'summary': {'distance': 41161.1, 'duration': 5248.4}, 'geometry_format': 'encodedpolyline', 'geometry': 'sneeHddvxTY?_D|@BZ~Cy@X_@p@rHp@dHn@hHn@|Gp@jHn@|GJrAJhB?fA?f@ArH?zI?hG@~@BnCJzBJvAZjCJp@Jj@ZxAZjABLd@xApBjEvBhELv@tBvDh@pAj@vAVbALh@Hb@Hb@RzABZBV@R@HFlB@nBD|AAlCAb[BnQCdI?`MDzU@`H@dHCnKGvM?bJKlSErCChC@~@FzBPvBF`@BXZrB`@tBdFjV`@lBz@zDf@xBn@~Bf@nBd@bBfBrG^vA\\lARv@z@|C`CzIjAhEbBlGnE|O~@tDrCnKXbAxCjKz@bDt@~Cd@~AhAfEdBnGl@|B`AlD|A|FhAbELd@jAjEpAzEtChKj@lBvBdG`BxD`ArBdAtBhBfDhE`Ij@bA|AtCfCdEp@`AhBpBr@p@fMtKrCbCpAjArPnNhIbHrE|DzGxFdCvBtCbCx@p@vLhKtD`DnCtBpCnBrBlA~Az@vJ~FbGhDb@X`@XtDxBrCbBhHdExA~@~BjBvBzBlMjOtA`BtKlMp@v@d@j@d@h@lArAXZjXz[dL|MdS|UjApAnAjAtA`AvAt@l@Tl@R|AZ|ANlGPlADZ@hFNl@B~DJlHRnDHpGTd@@p@BzBL|@DT@XB~APpAPz@J|ATbEz@JBhD|@|Af@jC~@vD|AbAf@dAf@rDnB`H|EnAbAv@p@VRf@`@rAlAtBtBj@d@bGzFrM`M|HrHnCpCz@dA|AtBhAfBdAjBbApB|@tBjGhPfEnLjAdEfC`Ll@dCHTPn@v@`C^|@~@tBdApBhAhBnA~A`@t@dGnIhBlC`@n@|@hBx@pBn@zBhBjIrLbl@z@rE\\rCHjALvCBlA@hTGn`@BtHFjHJxELnCPfCRzC^dExDr^|@fJVnCFdAHpC?lCGdAShCMbAe@`CgAxDaFvOm@zBS~@c@fC_CrPcBbL{@nEsAdGqDfO}AnGsElRqAzFcA|FmAdJM`Ay@dG_@vC{C`VOjAc@lDe@lDa@LoBr@yB`AkAd@aC~@{@`@e@\\a@d@_@l@i@lA{AjEyBbGyBjFaBfDo@fAmCbEqAhCqApDsAzEo@nBwEjMyBnE}@tAaAfAw@j@e@T}DfAoAf@k@JcA@_Dc@oBSm@Mk@Si@_@QSq@cA]s@i@qAe@wAWw@Ma@[w@_@g@SO{@g@uCqA}@MSIeCS_JeAo@Wi@Yg@o@sAo@y@e@{@YsAMiBD_A?iBI{@@oAHe@Pc@TkCbBmC~@g@ViCbBwAj@o@NKDy@\\gAl@m@d@kDhDoC|BmAp@u@Vu@Nw@FkIXSIa@Um@e@q@u@w@q@sA_Ai@[kBa@aAIeCFcAP_AZiD~Ay@Pg@BSDM?S?e@FmE~@aANaA?iBOe@?y@PyEfBi@Fi@ASGc@[_@_@QKQCQ?OD]XaB|BEJe@^kDvD{AfA]XY`@e@v@c@z@GJc@j@YV]N_@FE?I?mASs@U_@WMMYc@]}@g@gBUc@_@i@q@q@[Qq@Ka@B_@J]TcB`B[b@qA|B[^_@Za@TmAZ{@JyBLu@b@Wb@Sh@aA`Ee@|A_@`AWh@e@x@[\\a@LO?QEOIOS{@w@c@WSE{@CsALi@JoAf@{@h@_DdCiAlAa@jAYrBg@vE[`BIVUh@_@\\q@Xy@Jy@@_AKi@M{@]e@YcA{@}@cAw@qAsCmGeEyDOSYo@i@eBa@aAk@w@QKc@MQAg@Fe@TQPa@h@gA~Bw@rA_BpB_@`@c@ZSFg@Fi@@uBKwCUq@?q@FaJbASHa@Vo@t@y@xAKR_@h@o@l@w@\\c@Lw@@g@KqAa@}BeAcA]o@Ms@AiAFg@XQNOTYl@Or@EZExAB~BRvH?^IxA_@tEY|EYpCu@lF_@rCk@lFcAtFQhAUxAm@`DIv@CvADhDC|@G~@MpAAH{@fGe@jCKz@Ez@?z@LxICfAId@s@dB[f@WVi@VuCbA{@b@kBlAe@p@a@x@_@tAQ|@GfAGzECr@A^Fv@Pr@r@tA~CnFjE`HxAfEr@pBp@hFxDhXB\\FX|@lGFV@\\PlAFXZ`CHTTlBLtAHlB?t@Er@OdA_@nAERGTe@zAQl@I\\c@lA]t@u@tAg@n@i@l@cDzCcBxB]h@{@~ABJWNc@l@}DlEU^KZ{@pAITONo@nAu@`A_@X}CbAwBrA{@t@wAbBiEhGmA|AcDxCWXu@jAm@v@mEfFk@j@qBdBoAtAmBfB_At@s@V}@NoA?eAEk@?yGA', 'segments': [{'distance': 41161.1, 'duration': 5248.4, 'steps': [{'distance': 106.2, 'duration': 7.6, 'type': 11, 'instruction': 'Head north on North Main Street, US 93', 'name': 'North Main Street, US 93', 'way_points': [0, 2]}, {'distance': 120.4, 'duration': 10.5, 'type': 6, 'instruction': 'Continue straight onto North Main Street, US 93', 'name': 'North Main Street, US 93', 'way_points': [2, 5]}, {'distance': 25094.8, 'duration': 1428.8, 'type': 3, 'instruction': 'Turn sharp right onto West Idaho Street, US 2', 'name': 'West Idaho Street, US 2', 'way_points': [5, 273]}, {'distance': 5611.2, 'duration': 1346.7, 'type': 1, 'instruction': 'Turn right onto Ashley Lake Road', 'name': 'Ashley Lake Road', 'way_points': [273, 387]}, {'distance': 1472.3, 'duration': 353.4, 'type': 12, 'instruction': 'Keep left onto Ashley Lake Road', 'name': 'Ashley Lake Road', 'way_points': [387, 437]}, {'distance': 2456.5, 'duration': 589.6, 'type': 6, 'instruction': 'Continue straight onto Ashley Lake Road', 'name': 'Ashley Lake Road', 'way_points': [437, 503]}, {'distance': 2614.8, 'duration': 627.6, 'type': 6, 'instruction': 'Continue straight onto Ashley Lake Road', 'name': 'Ashley Lake Road', 'way_points': [503, 566]}, {'distance': 3684.9, 'duration': 884.4, 'type': 6, 'instruction': 'Continue straight onto North Ashley Lake Road', 'name': 'North Ashley Lake Road', 'way_points': [566, 640]}, {'distance': 0, 'duration': 0, 'type': 10, 'instruction': 'Arrive at North Ashley Lake Road, on the right', 'name': '', 'way_points': [640, 640]}]}], 'way_points': [0, 640], 'bbox': [-114.647381, 48.090738, -114.315071, 48.20311]}], 'bbox': [-114.647381, 48.090738, -114.315071, 48.20311], 'info': {'attribution': 'openrouteservice.org | OpenStreetMap contributors', 'engine': {'version': '4.7.0', 'build_date': '2018-12-18T13:44:23Z'}, 'service': 'routing', 'timestamp': 1550449490065, 'query': {'profile': 'driving-car', 'preference': 'fastest', 'coordinates': [[-114.31506, 48.20218], [-114.63478, 48.194]], 'language': 'en', 'units': 'm', 'geometry': True, 'geometry_format': 'encodedpolyline', 'instructions_format': 'text', 'instructions': True, 'elevation': False}}}
