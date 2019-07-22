# -*- coding: utf-8 -*-

# Create a heatmap of a single route, based on data from the OpenRouteService
# API. This is a proof-of-concept script only.

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QColor
from qgis.core import *
import processing
import openrouteservice

# Define variables as necessary
# Here
failures = 0

# Create necessary functions
# Here

class MyProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm creates a heatmap of a single route, based on data from the
    OpenRouteService API. This is a proof-of-concept script only.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

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
        return 'singlepathheatmap'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Single Path Heatmap')

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
        return self.tr("This script creates a heatmap of a single route, \
                        based on data from the OpenRouteService API. This is \
                        a proof-of-concept script only.")

    def initAlgorithm(self, config=None):
        """
        Define the inputs and output of the algorithm, along with some other
        properties.
        """

        # Add a text input for the user's OpenRouteService API key.
        self.addParameter(
            QgsProcessingParameterString(
                self.INPUT,
                self.tr('Your OpenRouteService API Key')
            )
        )

        # Add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Heatmap Layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        This algorithm imports data from 
        """

        # Retrieve the API key.
        APIKey = self.parameterAsString(
            parameters,
            self.INPUT,
            context
        )
        # And the description of the output layer (most likely 'memory:').
        outDesc = self.parameterAsOutputLayer(
            parameters,
            self.OUTPUT,
            context
        )

        feedback.setProgressText('Loading routes...')
        # Begin processing
        start = (-114.31506,48.20218)
        end = (-114.63478,48.19400)
        client = openrouteservice.Client(key=APIKey)
        try:
            routes = client.directions((start,end))
        except openrouteservice.exceptions.ApiError as e:
            feedback.reportError(repr(e), fatalError=True)
            if e.args[0] == 403: feedback.pushDebugInfo(
                'Check the API key you entered. It may be incorrect.')
            return {self.OUTPUT: None}
        encoded = routes['routes'][0]['geometry']
        decoded = openrouteservice.convert.decode_polyline(encoded)
        routeLayer = QgsVectorLayer("LineString", "route",
                               "memory")
        provider = routeLayer.dataProvider()
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPolyline(
            [QgsPoint(pt[0],pt[1]) for pt in decoded['coordinates']]))
        provider.addFeature(feat)
        feedback.setProgressText('\nDensifying paths...')
        result = processing.run('qgis:densifygeometriesgivenaninterval', {
                'INPUT':routeLayer,
                'INTERVAL':0.001,
                'OUTPUT':'memory:'
                }, context=context, feedback=feedback)
        densified = result['OUTPUT']
        feedback.setProgressText('\nExtracting vertices...')
        result2 = processing.run('native:extractvertices', {
                'INPUT':densified,
                'OUTPUT':outDesc
                }, context=context, feedback=feedback)
        # This is the output layer:
        outLayer = result2['OUTPUT'].clone()
        # Set up the desired heatmap renderer:
        feedback.setProgressText('\nSetting up renderer...')
        rndrr = QgsHeatmapRenderer()
        rndrr.setColorRamp(QgsGradientColorRamp(
            QColor('transparent'),QColor(227,26,28)))
        rndrr.setRadiusUnit(1)
        rndrr.setRadius(500)
        # Set the output layer's renderer to the heatmap renderer just defined
        outLayer.setRenderer(rndrr)
        # Done with processing
        feedback.setProgressText('\nDone with processing.')

        # Return the output layer.
        return {self.OUTPUT: outLayer}
