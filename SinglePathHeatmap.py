# -*- coding: utf-8 -*-

# Create a heatmap rendering of predicted boater travel in a given location and
# based on a provided network of sources (counties) and sinks (lakes), in order
# to create an overall boat-travel intensity map.

from PyQt5.QtCore import QCoreApplication, QVariant
from qgis.core import *
import processing
import openrouteservice

# Define variables as necessary
# Here

# Create necessary functions
# Here

class MyProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm creates a heatmap of routes, based on a gravity model and
    data from the OpenRouteService API.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT' #TODO: Need text here
    OUTPUT = 'memory'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return MyProcessingAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'routeheatmap'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Route Heatmap')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Science Fair 2019')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'sciencefairtwentynineteen'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it.
        """
        return self.tr("Create a heatmap rendering of predicted boater travel \
                        in a given location and based on a provided network \
                        of sources (counties) and sinks (lakes), in order to \
                        create an overall boat-travel intensity map.")

    def initAlgorithm(self, config=None):
        """
        Define the inputs and output of the algorithm, along with some other
        properties.
        """

        # Add a text input for the user's OpenRouteService API key.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('OpenRouteService API Key'),
                [QgsProcessing.TypeFile] #TODO: `TypeText`?
            )
        )

        # Add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Single Route Heatmap')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        This algorithm imports data from 
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsFile( #TODO: Adjust for text
            parameters,
            self.INPUT,
            context
        )

        fields = QgsFields()
        fields.append(QgsField('id',QVariant.Int))
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.LineString,
            QgsCoordinateReferenceSystem('EPSG:4326')
        )

        # If sink was not created, throw an exception to indicate that the
        # algorithm encountered a fatal error. The exception text can be any
        # string, but in this case we use the pre-built invalidSinkError
        # method to return a standard helper text for when a sink cannot be
        # evaluated.
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters,
                                                               self.OUTPUT))
        # Report successful loading of sink
        feedback.pushInfo(f'Successfully loaded sink: {sink}')

        feedback.setProgressText('Loading routes...')
        for lineNum in range(numLines): #TODO: Make this loop over routes
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                feedback.pushInfo('User cancelled the operation')
                break
            # Or proceed with processing
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
        # Done with processing
        feedback.pushInfo( #TODO: Rewrite this message
            f"Done with processing. {failures} errors were encountered.")

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: dest_id}
