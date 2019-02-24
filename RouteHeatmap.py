# -*- coding: utf-8 -*-

# Create a heatmap rendering of predicted boater travel in a given location and
# based on a provided network of sources (counties) and sinks (lakes), in order
# to create an overall boat-travel intensity map.

from PyQt5.QtCore import QCoreApplication, QVariant
from PyQt5.QtGui import QColor
from qgis.core import *
import processing
import openrouteservice

# Create necessary functions
# Here

class MyProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    Create a heatmap rendering of predicted boater travel in a given location
    and based on a provided network of sources (counties) and sinks (lakes), in
    order to create an overall boat-travel intensity map.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    COUNTIES = 'COUNTIES'
    ORS_API_KEY = ''
    ROUTES = 'ROUTES'
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
        return 'boattravelheatmap'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Boat Travel Heatmap')

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
        return self.tr('''
            Create a heatmap of predicted boater travel in a real-world water
            system, based on a gravity model and data from the OpenRouteService
            API.

            The inputs should be point layers.

            The first should represent the lakes to be analyzed, and have
            attributes named "Calcium", "pH", and "Attractiveness", with the
            former expressed in milligrams per liter, and the latter being the
            attraction parameter for the gravity model.

            The second should represent counties in the area to be analyzed,
            and have attributes "Name" and "Boats", containing the county name
            and the number of boats to which the county is home.

            An OpenRouteService API key is required to use this algorithm.
            Enter your API key as the third input. To sign up for API access,
            visit https://openrouteservice.org/dev/#/signup.
            ''')

    def initAlgorithm(self, config=None):
        """
        Define the inputs and output of the algorithm, along with some other
        properties.
        """

        # Add a parameter for the lake layer
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Lake input layer'),
                [QgsProcessing.TypeVectorPoint]
            )
        )

        # Add a parameter for the county layer
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.COUNTIES,
                self.tr('County input layer'),
                [QgsProcessing.TypeVectorPoint]
            )
        )

        # Add a text input for the user's OpenRouteService API key.
        self.addParameter(
            QgsProcessingParameterString(
                self.ORS_API_KEY,
                self.tr('Your OpenRouteService API Key')
            )
        )

        # Add an output for the route layer
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.ROUTES,
                self.tr('Route Layer')
            )
        )

        # Add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Boat Traffic Density Heatmap')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the source layers.
        lakeSource = self.parameterAsSource(
            parameters,
            self.INPUT,
            context
        )
        countySource = self.parameterAsSource(
            parameters,
            self.COUNTIES,
            context
        )

        # Throw an exception if either source was not found.
        if lakeSource is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT))
        if countySource is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.COUNTIES))

        feedback.pushInfo('Successfully loaded lake and county source files')

        # Record the API key.
        APIKey = self.parameterAsString(
            parameters,
            self.ORS_API_KEY,
            context
        )

        # Get a sink for the routes generated, with some attributes
        fields = QgsFields()
        fields.append(QgsField('County', QVariant.String))
        fields.append(QgsField('Lake', QVariant.String))
        fields.append(QgsField('Habitability', QVariant.Float))
        (routeSink, routeSinkID) = self.parameterAsSink(
            parameters,
            self.ROUTES,
            context,
            fields,
            QgsWkbTypes.MultiLineString,
            QgsCoordinateReferenceSystem('EPSG:4326')
        )

        # And get the description of the output layer (most likely 'memory:').
        outDesc = self.parameterAsOutputLayer(
            parameters,
            self.OUTPUT,
            context
        )

        # Variable definitions
        failures = 0

        # Begin processing
        client = openrouteservice.Client(key=APIKey)
        feedback.setProgressText('Loading routes...')
        #TODO: Begin loop here
        #TODO: Replace these with county and lake coordinates (lon, lat)
        start = (-114.31506,48.20218)
        end = (-114.63478,48.19400)
        #TODO: Set the progress bar
        try:
            routes = client.directions((start,end))
        except openrouteservice.exceptions.ApiError as e:
            feedback.reportError(
                'The OpenRouteService API encountered an error.\n' + repr(e),
                fatalError=True)
            if e.args[0] == 403: feedback.pushDebugInfo(
                'The API key you entered may be incorrect, or \
                you may have exhausted your API request quota.')
            return {self.OUTPUT: None}
        encoded = routes['routes'][0]['geometry']
        decoded = openrouteservice.convert.decode_polyline(encoded)
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPolyline(
            [QgsPoint(pt[0],pt[1]) for pt in decoded['coordinates']]))
        routeSink.addFeature(feat, QgsFeatureSink.FastInsert)
        #TODO: End loop here
        feedback.setProgressText('\nDensifying paths...')
        result = processing.run('qgis:densifygeometriesgivenaninterval', {
                'INPUT':routeSinkID,
                'INTERVAL':0.001,
                'OUTPUT':'memory:'
                }, context=context, feedback=feedback)
        densified = result['OUTPUT']
        feedback.setProgressText('\nExtracting vertices...')
        result2 = processing.run('native:extractvertices', {
                'INPUT':densified,
                'OUTPUT':outDesc
                }, context=context, feedback=feedback)
        # Create the output layer.
        outLayer = result2['OUTPUT'].clone()
        # Set up the heatmap renderer as desired.
        feedback.setProgressText('\nSetting up renderer...')
        rndrr = QgsHeatmapRenderer()
        rndrr.setColorRamp(QgsGradientColorRamp(
            QColor('transparent'),QColor(227,26,28)))
        rndrr.setRadiusUnit(1)
        rndrr.setRadius(500)
        # Set the output layer's renderer to the heatmap renderer just defined.
        outLayer.setRenderer(rndrr)
        # Done with processing.
        feedback.setProgressText('\nDone with processing.')

        # Return the output layer.
        return {self.ROUTES: routeSinkID, self.OUTPUT: outLayer.id()}
