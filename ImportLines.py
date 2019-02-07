# -*- coding: utf-8 -*-

# Script to import data from a delimited file in which each row (object)
# contains two sets of coordinates - say, BEGLAT, BEGLON, ENDLAT, and ENDLON -
# which correspond to the start- and endpoints of a line.
# Designed to work from the QGIS Processing Toolbox.
# By Lucas Ritzdorf

from PyQt5.QtCore import QCoreApplication, QVariant
from qgis.core import *
import processing
from itertools import (takewhile,repeat)

# Define default header names and prompts
headerInfo = {"Object ID column":r"OBJECTID *", "Object Name":"WaterbodyName",
              "Starting Latitude":"BEGLAT", "Starting Longitude":"BEGLON",
              "Ending Latitude":"ENDLAT", "Ending Longitude":"ENDLON"}

def lineCount(filename):
    """
    Quickly and efficiently get the number of lines in the file at "filename".
    """
    f = open(filename, 'rb')
    bufgen = takewhile(
        lambda x: x, (f.raw.read(1024*1024) for _ in repeat(None)))
    return sum( buf.count(b'\n') for buf in bufgen )

class MyProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm processes a CSV imput file into a Shapefile polyline layer.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    OUTPUT = 'memory' #Or 'OUTPUT'

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
        return 'csvtoshapefile'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('CSV to Shapefile')

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
        return self.tr("Create a Shapefile polyline layer in memory that is "\
                       "built from a CSV file.")

    def initAlgorithm(self, config=None):
        """
        Define the inputs and output of the algorithm, along with some other
        properties.
        """

        # Add the input CSV source.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('CSV input file'),
                [QgsProcessing.TypeFile]
            )
        )

        # Add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsFile(
            parameters,
            self.INPUT,
            context
        )

        # If source was not found, throw an exception to indicate that the
        # algorithm encountered a fatal error. The exception text can be any
        # string, but in this case we use the pre-built invalidSourceError
        # method to return a standard helper text for when a source cannot be
        # evaluated.
        if (source is None) or (not source.endswith('.csv')):
            raise QgsProcessingException(self.invalidSourceError(parameters,
                                                                 self.INPUT))
        # Report successful loading of source
        feedback.pushInfo('Successfully loaded {source}')

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
        feedback.pushInfo('Successfully loaded {sink}')

        # Set up variable for processing
        numLines = lineCount(source)
        total = 100.0 / numLines
        importFails = [0,0]
        fin = open(source, "r")
        headers = fin.readline().strip().split(",")

        feedback.setProgressText('Importing features...')
        for lineNum in range(numLines):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                feedback.pushInfo('User cancelled the import operation')
                break
            # Or proceed with processing
            try:
                line = fin.readline().strip().split(",")
                feat = QgsFeature(fields)
                feat.setAttribute("name",
                    line[list(headerInfo.keys()).index('Object Name')])
                feat.setAttribute("id",
                    line[list(headerInfo.keys()).index('Object ID column')])
                feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(float(\
                    line[headers.index(begLon)]), float(line[\
                    headers.index(begLat)])),QgsPoint(float(line[\
                    headers.index(endLon)]), float(line[headers.index(\
                    endLat)]))]))
                res = sink.addFeature(feat) #Or ,QgsFeatureSink.FastInsert)
                if res == False: importFails[0] += 1
            except ValueError:
                importFails[1] += 1
            except IndexError:
                if line == ['']: print("Blank line at line", lineNum)
                else: importFails[1] += 1
            feedback.setProgress(int(lineNum * total))
        fin.close()
        print(sum(importFails), "feature(s) failed to import;",\
              importFails[1], "of those had missing data")

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: dest_id}
