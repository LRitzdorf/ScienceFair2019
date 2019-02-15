# -*- coding: utf-8 -*-

# Create a heatmap rendering of predicted boater travel in a given location and
# based on a provided network of sources (counties) and sinks (lakes), in order
# to create an overall boat-travel intensity map.

from PyQt5.QtCore import QCoreApplication, QVariant
from qgis.core import *
import processing

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
                self.tr('Boat Travel Heatmap')
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

        # Check whether the API key is valid.
        if True: #TODO: Check API key for validity
            feedback.reportError(
                "The provided OpenRouteService API key appears to be invalid.",
                fatalError=True)
            raise QgsProcessingException(self.invalidSourceError(parameters,
                                                                 self.INPUT))
        
        # Report successful loading of source.
        feedback.pushInfo('Validated your OpenRouteService API key.')

        fields = QgsFields()
        fields.append(QgsField('id',QVariant.Int))
        fields.append(QgsField('name',QVariant.String)) #TODO: Revise this?
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

        # Set up variables for processing
        numLines = lineCount(source)
        total = 100.0 / numLines
        importFails = [0,0]
        fin = open(source, "r")
        csvRdr = reader(fin, delimiter=',')

        feedback.setProgressText('Importing features...')
        for lineNum in range(numLines):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                feedback.pushInfo('User cancelled the import operation')
                break
            # Or proceed with processing
            try: #TODO: Revise all of this
                line = csvRdr.__next__()
                # Initial header setup
                if lineNum == 0:
                    fieldPositions = {
                        'Name'  :line.index(headerInfo['Object Name']),
                        'ObjID' :line.index(headerInfo['Object ID']),
                        'BegLat':line.index(headerInfo['Starting Latitude']),
                        'BegLon':line.index(headerInfo['Starting Longitude']),
                        'EndLat':line.index(headerInfo['Ending Latitude']),
                        'EndLon':line.index(headerInfo['Ending Longitude'])
                    }
                # Actual processing
                else:
                    feat = QgsFeature(fields)
                    feat.setAttribute('name',
                        line[fieldPositions['Name']])
                    feat.setAttribute('id',
                        line[fieldPositions['ObjID']])
                    feat.setGeometry(QgsLineString([
                        QgsPoint(
                            x=float(line[fieldPositions['BegLon']]),
                            y=float(line[fieldPositions['BegLat']])
                        ),
                        QgsPoint(
                            x=float(line[fieldPositions['EndLon']]),
                            y=float(line[fieldPositions['EndLat']])
                        )
                    ]))
                    res = sink.addFeature(feat) #Or ,QgsFeatureSink.FastInsert)
                    if res == False: importFails[0] += 1
            except ValueError: #TODO: And this
                importFails[1] += 1
            except IndexError: #TODO: This too
                if line == ['']:
                    feedback.pushInfo(f"Blank line at line {lineNum}")
                else: importFails[1] += 1
            feedback.setProgress(int(lineNum * total)) #TODO: And finally this
        fin.close()
        feedback.pushInfo( #TODO: Rewrite this message
            f"{sum(importFails)} feature(s) failed to import; "\
            + f"{importFails[1]} of those had missing data")

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: dest_id}
