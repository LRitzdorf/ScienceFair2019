# -*- coding: utf-8 -*-

# Create a heatmap rendering of a single route between two points.
# Normally, this would be relatively pointless, but this script is intended as a
# proof-of-concept for the idea of heatmapping many different routes together,
# to create on overall travel intensity map.

from qgis.core import *
import qgis.utils

class MyProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm processes a CSV imput file into a Shapefile polyline layer.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

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
        return self.tr("Create a heatmap of a single line segment.\
                        This is a proof-of-concept script only.")

    def initAlgorithm(self, config=None):
        """
        Define the inputs and output of the algorithm, along with some other
        properties.
        """

        # No input is necessary for this algorithm.

        # Add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Test Heatmap')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        This algorithm imports data from 
        """

        # Retrieve the feature sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.

        fields = QgsFields()
        fields.append(QgsField('id',QVariant.Int))
        fields.append(QgsField('name',QVariant.String))
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

        feedback.setProgressText('Creating test heatmap...')
        # Stop the algorithm if cancel button has been clicked
        if feedback.isCanceled():
            feedback.pushInfo('User cancelled the import operation')
            break
        # Or proceed with processing
        feat = QgsFeature(fields)
        feat.setAttribute('id', '0')
        feat.setAttribute('name', 'Segment for test heatmap')
        feat.setGeometry(QgsLineString([
            QgsPoint(y=48.201946, x=-114.314984),
            QgsPoint(y=48.182118, x=-114.614361)
            ]))

        feedback.pushInfo('Done.')

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: dest_id}
    
