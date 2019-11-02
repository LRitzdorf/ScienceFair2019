# -*- coding: utf-8 -*-

# Computational model of Dreissenid mussel spread in a given water system,
# built as a QGIS processing script.

# The *.pickle output file created by RetrieveRoutes.py is to be used as the
# "Pickled Routes" input item.

# Computes mussel travel, as facilitated by boat traffic, in the given water
# system, then outputs the routes traveled by contaminated boats as a heatmap
# layer, with more heavily traveled routes having higher weights.

from PyQt5.QtCore import QCoreApplication, QVariant
from PyQt5.QtGui import QColor
from qgis.core import *
import processing
from openrouteservice.convert import decode_polyline
import pickle

# Define initial variables


class MusselSpreadSimulationAlgorithm(QgsProcessingAlgorithm):
    '''
    Computes mussel travel, as facilitated by boat traffic, in the given water
    system, then outputs the routes traveled by contaminated boats as a heatmap
    layer, with more heavily traveled routes having higher weights.
    '''

    INPUT =        'INPUT'         # Lake file
    COUNTIES =     'COUNTIES'      # County file
    ROUTES =       'ROUTES'        # Pickled route data file
    OUTPUT =       'OUTPUT'        # Heatmap layer
    ROUTE_OUTPUT = 'ROUTE_OUTPUT'  # Route layer (not as a heatmap)

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return MusselSpreadSimulationAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'musselspreadsimulation'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Mussel Spread Simulation')

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

    def tags(self):
        return ['mussels', 'gravity model', 'simulation']

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it.
        """
        return self.tr('''
            Create a heatmap of predicted boater travel in a real-world water
            system, based on a gravity model and route data.

            All inputs are files. The first two should contain lake and county
            data, in that order. The third should be the .pickle file created
            by the RetrieveRoutes.py script.

            The output will be a point layer with heatmap styling, showing
            routes over which contaminated boats are deemed likely to travel.
            Higher-traffic routes will be given a higher weight.
            ''')

    def initAlgorithm(self, config=None):
        """
        Define the inputs and outputs of the algorithm, along with some other
        properties.
        """

        # Add a parameter for the lake input file
        self.addParameter(QgsProcessingParameterFile(
            INPUT,
            self.tr('Lake Input File'),
            extension='csv'
        ))

        # Add a parameter for the county input file
        self.addParameter(QgsProcessingParameterFile(
            COUNTIES,
            self.tr('County Input File'),
            extension='csv'
        ))

        # Add a parameter for the pickled routes input file
        self.addParameter(QgsProcessingParameterFile(
            ROUTES,
            self.tr('Pickled Route Data File (from RetrieveRoutes.py)'),
            extension='pkl'
        ))

        # Add a new vector layer for the output heatmap
        self.addParameter(QgsProcessingParameterVectorDestination(
            OUTPUT,
            self.tr('Output Heatmap Layer'),
            QgsProcessing.TypeVectorPoint
        ))

        # Add a new feature sink (vector layer) for the route, not as a heatmap
        self.addParameter(QgsProcessingParameterFeatureSink(
            ROUTE_OUTPUT,
            self.tr('Routes Layer (not as a heatmap)'),
            QgsProcessing.TypeVectorLine
        ))

        # Consider adding additional vector output layers for lakes and county
        # centers (QgsProcessing.TypeVectorPoint)

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve parameters:
        feedback.setProgressText('Retrieving input parameters...')
        # Lake input file
        pass    # Not currently needed

        # County input file
        pass    # Not currently needed

        # Pickled routes file
        pickledFileName = self.parameterAsFile(
            parameters,
            ROUTES,
            context
        )

        # Sink and ID for the route output layer
        # Consider adding field definitions:
        ##fields = QgsFields()
        ##fields.append(QgsField('County', QVariant.String))
        ##fields.append(QgsField('Lake', QVariant.String))
        ##fields.append(QgsField('Habitability', QVariant.Float))
        ##fields.append(QgsField('Weight', QVariant.Float))
        (routeSink, routeSinkID) = self.parameterAsSink(
            parameters,
            ROUTE_OUTPUT,
            context,
            fields,
            geometryType=QgsWkbTypes.LineString,
            crs=QgsCoordinateReferenceSystem('EPSG:4326')
        )

        # Internalize pickled routes
        feedback.setProgressText('Loading pickled routes...')
        # Define classes first to allow successful unpickling:
        class Site():
            pass
        class County():
            pass
        # A rather complex process to allow items to be unpickled and assigned
        # in order:
        counties = None; sites = None; routeMatrix = None
        l = [counties, sites, routeMatrix]
        feedback.setProgressText('Retrieving pickled routes from file...')
        with open(pickledFileName, 'r+b') as pickledFile:
            for i in range(len(l)):
                l[i] = pickle.load(f)
        (counties, sites, routeMatrix) = tuple(l)
        del l, i

        # Begin Processing
        feedback.pushInfo('Beginning processing')

        # Add route polylines to route layer
        feedback.setProgressText('Adding routes to route layer...')
        for ci, county in enumerate(counties):
            for si, site in enumerate(sites):
                encoded = routeMatrix[ci][si]
                decoded = decode_polyline(encoded)
                feat = QgsFeature()
                # Remember to add fields here, with values from site._[attr]
                feat.setGeometry(QgsGeometry.fromPolyline(
                    [QgsPoint(pt[0], pt[1]) for pt in decoded['coordinates']]
                ))
                routeSink.addFeature(feat)
        routeSink.FlushBuffer()
        # All routes are now in routeSink as polyline features

        # Begin Model
        feedback.pushInfo('Starting Monte Carlo model')
        # Actual model code goes here
        # End Model
        feedback.pushInfo('Completed Monte Carlo model')

        # Heatmap processing (based on results of Monte Carlo model)
        feedback.setProgressText('Building heatmap from model results...')
        # Densify routes layer
        densified = processing.run('qgis:densifygeometriesgivenaninterval',
                                   {'INPUT': routeSinkID,
                                    'INTERVAL': 0.001,
                                    'OUTPUT': 'memory:'},
                                   context=context, feedback=feedback,
                                   is_child_algorithm=True)

        # Extract vertices
        # ^ Preserve fields for each polyline, pass on to points (research)
        vertices = processing.run('native:extractvertices',
                                  {'INPUT': densified['OUTPUT'],
                                   'OUTPUT': parameters[OUTPUT]},
                                  context=context, feedback=feedback,
                                  is_child_algorithm=True)
        del densified

        # Set up heatmap renderer
        # ^ Set weight for each point from field(s) (research)
        rndrr = QgsHeatmapRenderer()
        rndrr.setColorRamp(QgsGradientColorRamp(
            QColor('transparent'),QColor(227,26,28)))
        rndrr.setRadiusUnit(1)
        rndrr.setRadius(500)

        # Assign heatmap renderer to extracted vertices layer
        QgsProcessingUtils.mapLayerFromString(vertices['OUTPUT'], context
            ).setRenderer(rndrr)

        # End Processing
        feedback.pushInfo('Processing complete; finishing up...')

        # Return output layers
        return {OUTPUT:       vertices['OUTPUT'],
                ROUTE_OUTPUT: routeSinkID}
