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

class MusselSpreadSimulationAlgorithm(QgsProcessingAlgorithm):
    '''
    Computes mussel travel, as facilitated by boat traffic, in the given water
    system, then outputs the routes traveled by contaminated boats as a heatmap
    layer, with more heavily traveled routes having higher weights.
    '''

    INPUT =        'INPUT'         # Lake file
    COUNTIES =     'COUNTIES'      # County file
    ROUTES =       'ROUTES'        # Pickled route data file
    MC_LOOPS =     'MC_LOOPS'      # Number of Monte Carlo loops to run
    YEARS =        'YEARS'         # Number of years to simulate
    PCT_DECONT =   'PCT_DECONT'    # Percent of all boats decontaminated
    OUTPUT =       'OUTPUT'        # Heatmap layer
    ROUTE_OUTPUT = 'ROUTE_OUTPUT'  # Route layer (not as a heatmap)

    def tr(self, string):
        '''
        Returns a translatable string with the self.tr() function.
        '''
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return MusselSpreadSimulationAlgorithm()

    def name(self):
        '''
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        '''
        return 'musselspreadsimulation'

    def displayName(self):
        '''
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        '''
        return self.tr('Mussel Spread Simulation')

    def group(self):
        '''
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        '''
        return self.tr('Science Fair 2019')

    def groupId(self):
        '''
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        '''
        return 'sciencefairtwentynineteen'

    def tags(self):
        return ['mussels', 'gravity model', 'simulation']

    def shortHelpString(self):
        '''
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it.
        '''
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
        '''
        Define the inputs and outputs of the algorithm, along with some other
        properties.
        '''

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

        # Add a parameter for the number of Monte Carlo loops to run
        self.addParameter(QgsProcessingParameterNumber(
            MC_LOOPS,
            self.tr('Number of Monte Carlo loops (repetitive trials) to run'),
            QgsProcessingParameterNumber.Integer,
            minValue=1, maxValue=50
        ))

        # Add a parameter for the number of years to simulate
        self.addParameter(QgsProcessingParameterNumber(
            YEARS,
            self.tr('Number of years to simulate (accuracy likely to decline '\
                    'significantly with increases to this parameter)'),
            QgsProcessingParameterNumber.Integer,
            minValue=1, maxValue=20
        ))

        # Add a paramater for the percentage of boats that are decontaminated
        self.addParameter(QgsProcessingParameterNumber(
            PCT_DECONT,
            self.tr('Percentage of all boats that are deconaminated'),
            QgsProcessingParameterNumber.Integer,
            defaultValue=0,
            minValue=0, maxValue=100
        ))

        # Consider adding additional vector output layers for lakes and county
        # centers (QgsProcessing.TypeVectorPoint)


    def processAlgorithm(self, parameters, context, feedback):
        '''
        Here is where the processing itself takes place.
        '''

        from openrouteservice.convert import decode_polyline
        import pickle
        import csv

        # Define data-storage classes for Sites and Counties
        # These MUST support the same attributes as the classes defined in
        # RetrieveRoutes.py, and should be copied and pasted for best results

        class Site():
            '''
            Site object; contains information for monitoring locations.
            Site(self, lat, lon[, pH, pHDate, calcium, calciumDate,
            percentClean, habitability, attractiveness, initInfested])
            -> Site object
            '''
            def __init__(self, lat, lon, pH=None, pHDate=None, calcium=None,
                         calciumDate=None, percentClean=0, habitability=0.0,
                         attractiveness=1, initInfested=False):
                self._lat =            lat
                self._lon =            lon
                self._pH =             pH
                self._pHDate =         pHDate
                self._calcium =        calcium
                self._calciumDate =    calciumDate
                self._percentClean =   percentClean
                self._habitability =   habitability
                self._attractiveness = attracteiveness
                self._initInfested =   initInfested
                self.resetInfested()

            @property
            def lat(self):
                return self._lat

            @property
            def lon(self):
                return self._lon

            @property
            def pH(self):
                return self._pH

            @pH.setter
            def pH(self, newpH):
                self._pH = newpH

            @property
            def pHDate(self):
                return self._pHDate

            @pHDate.setter
            def pHDate(self, newDate):
                self._pHDate = newDate

            def addpH(self, newpH, newDate):
                if (self._pHDate == None) or (newDate > self._pHDate):
                    self._pH = newpH
                    self._pHDate = newDate
                    return True
                return False

            @property
            def calcium(self):
                return self._calcium

            @calcium.setter
            def calcium(self, newCa):
                self._calcium = newCa

            @property
            def calciumDate(self):
                return self._calciumDate

            @calciumDate.setter
            def calciumDate(self, newDate):
                self._calciumDate = newDate

            def addCa(self, newCa, newDate):
                if (self._calciumDate == None) or (newDate > self._calciumDate):
                    self._calcium = newCa
                    self._calciumDate = newDate
                    return True
                return False

            @property
            def percentClean(self):
                return self._percentClean

            @property
            def habitability(self):
                return self._habitability

            @habitability.setter
            def habitability(self, new_hab):
                self._habitability = new_hab

            @property
            def attractiveness(self):
                return self._attractiveness

            @attractiveness.setter
            def attractiveness(self, new_attr):
                self._attractiveness = new_attr

            @property
            def initInfested(self):
                return self._initInfested

            @property
            def infested(self):
                return self._infested

            def infest(self):
                if self._habitability > 0:
                    self._infested = True

            def resetInfested(self):
                self._infested = self._initInfested


        class County():
            '''
            County object; contains information for counties.
            County(self, lat, lon, boats) -> County object
            '''
            def __init__(self, lat, lon, boats):
                self._lat =   lat
                self._lon =   lon
                self._boats = boats

            @property
            def lat(self):
                return self._lat

            @property
            def lon(self):
                return self._lon

            @property
            def boats(self):
                return self._boats

            @boats.setter
            def boats(self, new_boats):
                self._boats = new_boats


        # Retrieve parameters:
        feedback.setProgressText('Retrieving input parameters...')
        # Lake input file
        siteFileName = self.parameterAsFile(
            parameters,
            INPUT,
            context
        )
        # County input file
        countyFileName = self.parameterAsFile(
            parameters,
            COUNTIES,
            context
        )
        # Pickled routes file
        pickledFileName = self.parameterAsFile(
            parameters,
            ROUTES,
            context
        )

        # Add field definitions:
        fields = QgsFields()
        fList = [QgsField('County', QVariant.String),
                 QgsField('Lake', QVariant.String),
                 QgsField('pH', QVariant.Float),
                 QgsField('pH Date', QVariant.String),
                 QgsField('Calcium', QVariant.Float),
                 QgsField('Calcium Date', QVariant.String),
                 QgsField('Habitability', QVariant.Float),
                 QgsField('Attractiveness', QVariant.Int),
                 QgsField('Infestation Proportion', QVariant.Float),
                 QgsField('Initially Infested', QVariant.Bool)]
        for field in fList:
            fields.append(field)
        # Sink and ID for the route output layer
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
        # A rather awkward process to allow items to be unpickled and assigned
        # in order:
        counties = None; sites = None; routeMatrix = None
        l = [counties, sites, routeMatrix]
        feedback.setProgressText('Retrieving pickled routes from file...')
        with open(pickledFileName, 'r+b') as pickledFile:
            for i in range(len(l)):
                l[i] = pickle.load(f)
        (counties, sites, routeMatrix) = tuple(l)
        del l, i

        # Define habitability function
        def habitability(pH, calcium, lowPh, lowCalc):
            """
            Returns the habitability of the site, based on pH and calcium levels.
            Result is a probability expressed as a decimal, or None if no data exists.
            """
            if (pH == None) and (calcium == None):
                # Cannot compute risk
                return None
            elif pH == None:
                # Compute risk based only on calcium
                if 0 <= calcium < lowCalc:
                    CaFactor = 0
                elif lowCalc <= calcium:
                    CaFactor = (-1 / (calcium - lowCalc + 1)) + 1
                else:
                    return None
                return CaFactor
            elif calcium == None:
                # Compute risk based only on pH
                if 0 <= pH < lowpH:
                    pHFactor = 0
                elif lowpH <= pH:
                    pHFactor = (-1 / (10 * (pH - lowpH) + 1)) + 1
                else:
                    return None
                return pHFactor
            else:
                # Compute risk based on calcium and pH
                # Calcium factor
                if 0 <= calcium < lowCalc:
                    CaFactor = 0
                elif lowCalc <= calcium:
                    CaFactor = (-1 / (calcium - lowCalc + 1)) + 1
                else:
                    CaFactor = 1
                # pH factor
                if 0 <= pH < lowpH:
                    pHFactor = 0
                elif lowpH <= pH:
                    pHFactor = (-1 / (10 * (pH - lowpH) + 1)) + 1
                else:
                    pHFactor = 1
                return pHFactor * CaFactor

        # Internalize additional site data from file (i.e. attractiveness)
        #TODO: Add list of new counties, sites to fetch routes for
##        with open(countyFileName, 'r') as countyFile,
##             open(siteFileName, 'r') as lakeFile:
##            # Populate object lists from data files
##            # County data
##            dialect = csv.Sniffer().sniff(countyFile.read(1024)); countyFile.seek(0)
##            countyReader = csv.reader(countyFile, dialect)
##            # Get past, and validate, header line
##            try:
##                assert countyReader.__next__() == \
##                       ['County','Latitude','Longitude','Boats','County Seat']
##            except AssertionError:
##                feedback.reportError(
##                    'County file header does not match expected. Aborting.',
##                    fatalError=True)
##            for line in countyReader:
##                if line[0] not in counties:
##                    counties[line[0]] = County(float(line[1]), float(line[2]),
##                                               int(line[3]))
##            del countyReader
##            # Site data
##            dialect = csv.Sniffer().sniff(lakeFile.read(1024)); lakeFile.seek(0)
##            lakeReader = csv.reader(lakeFile, dialect)
##            # Get past, and validate, header line
##            try:
##                assert lakeReader.__next__() == \
##                       ['IDNumber','Latitude','Longitude','Date','Parameter', \
##                        'Value','Attractiveness','Infested']
##            except AssertionError:
##                feedback.reportError(
##                    'Lake file header does not match expected. Aborting.',
##                    fatalError=True)
##            for line in lakeReader:
##                try:
##                    # Ensure site is in dataset
##                    if line[0] not in sites:
##                        sites[line[0]] = Site(float(line[1]), float(line[2]),
##                                              attractiveness=int(line[6]),
##                                              initInfested=bool(line[7]))
##                    # Add data to site (only if newer than current data)
##                    if line[4] == 'pH':
##                        sites[line[0]].addpH(float(line[5]),
##                                             date.fromisoformat(line[3]))
##                    elif line[4] == 'Calcium':
##                        sites[line[0]].addCa(float(line[5]),
##                                             date.fromisoformat(line[3]))
##                except ValueError:
##                    pass
        for site in sites.values():
            site.habitability = habitability(site.pH, site.calcium,
                                             lowPh, lowCalc)

        #TODO: Fetch routes for new counties, sites

        # Begin Processing
        feedback.pushInfo('Beginning processing')
        from math import sqrt, log, radians, cos, sin, acos
        from random import randint
        from numpy import array, zeros
        c = zeros([len(counties),len(sites)],dtype=float)

        # Add route polylines to route layer
        feedback.setProgressText('Calculating route lengths...')
        for i in range(len(counties)):
            for j in range(len(sites)):
                encoded = routeMatrix[i][j]
                decoded = decode_polyline(encoded)
                feat = QgsFeature()
                feat.setGeometry(QgsGeometry.fromPolyline(
                    [QgsPoint(pt[0], pt[1]) for pt in decoded['coordinates']]
                ))
                # Add distance to array c[i][j]
                c[i][j] = feat.geometry().length() * 10  # Gives length in km
        del encoded, decoded
        # Route distances are now stored in c[i][j]

        # Begin Model
        feedback.setProgressText('Starting Monte Carlo model')

        # Model-specific variables:
        lowCalc = 28
        lowPh = 7.4
        infestedBoatFraction = 127 / 39522  ## 2016 (used mussels + water)
        ## 2017: 17/77235 mussels + 390 standing water
        ## 2018: 16/109789 mussels + 447 standing water
        settleRisk = 0.02
        α = 2
        iterations_per_year = 8  # Assumed number of boat trips per year

        # Set up arrays
        # Computed in Model Core:
        A = zeros(len(counties),dtype=float)
        T = zeros([len(counties),len(sites)],dtype=int)
        P = zeros(len(counties),dtype=int)
        t = zeros([len(counties),len(sites)],dtype=int)
        Q = zeros(len(sites),dtype=int)
        # Extracted from input:
        O = zeros(len(counties),dtype=int)
        W = zeros(len(sites),dtype=int)
        # c has already been set up and populated with distances
        # Results:
        results = zeros([MCLoops,years,len(sites)],dtype=int)

        # Set up O[i] and W[i]
        for i, county in enumerate(counties.values()):
            O[i] = county.boats
        for j, site in enumerate(sites.values()):
            W[j] = site.attractiveness
        # c has already been set up and populated with distances
        feedback.pushInfo('Arrays set up; computed c[i][j], O[i], and W[i]')

        # Compute A[i]: balancing factor
        for i in range(len(counties)):
            for j in range(len(sites)):
                A[i] += W[j] * (c[i][j] ** -α)
            A[i] = 1 / A[i]

        # Compute T[i][j]: total boats from county i to lake j
        for i in range(len(counties)):
            for j in range(len(sites)):
                T[i][j] = A[i] * O[i] * W[j] * (c[i][j] ** -α)
        feedback.pushInfo('Computed A[i] and T[i]')

        # Begin Model Core and Monte Carlo loop
        feedback.setProgressText('Running model...')

        for MCLoop in range(MCLoops):
            feedback.pushInfo(f'Monte Carlo loop {MCLoop}')

            # Reset infestation states
            for site in sites.values():
                site.resetInfested()

            # Begin Main Loop
            for year in range(years):
                feedback.pushInfo(f'\tYear {year}')
                P.fill(0.0)
                Q.fill(0.0)
                
                for iteration in range(iterations_per_yr):
                    
                    # Compute P[i]: potentially infested boats in county i
                    for i in range(len(counties)):
                        for j, site in enumerate(sites.values()):
                            if site.infested:
                                P[i] += T[i][j]
                        # Adjust for decontamination using percent_cleaned
                        P[i] = P[i] * (1 - (percent_cleaned / 100))
                    
                    # Compute t[i][j]: infested boats from county i to lake j
                    t.fill(0.0)
                    for i in range(len(counties)):
                        for j in range(len(sites)):
                            t[i][j] = A[i] * P[i] * W[j] * (c[i][j] ** -α)
                    
                    # Compute Q[j]: total infested boats to lake j
                    for j in range(len(sites)):
                        for i in range(len(counties)):
                            Q[j] += t[i][j]
                    
                # Update infestation states (with stochastic factor)
                for j, site in enumerate(sites.values()):
                    for boat in range(Q[j]):
                        if randint(1, (1/settleRisk)
                                   - round(site.habitability * 5)) == 1:
                            site.infest()

                # Store results
                for j, site in enumerate(sites.values()):
                    results[MCLoop][year][j] = site.infested

            # End Main Loop

        # End Monte Carlo loop and Model Core

        # End Model
        feedback.pushInfo('Completed Monte Carlo model')

        # Add route polylines to route layer
        feedback.setProgressText('Adding routes to route layer...')
        for i, (cName, county) in enumerate(counties.items):
            for j, (sName, site) in enumerate(sites.items):
                encoded = routeMatrix[i][j]
                decoded = decode_polyline(encoded)
                feat = QgsFeature()
                # Transfer attributes from each site to its feature
                feat.setAttributes([cName, sName, site.pH,
                                    site.pHDate.isoformat(), site.calcium,
                                    site.calciumDate.isoformat(),
                                    site.habitability, site.attractiveness,
                                    siteInfestedFraction, site.initInfested]) ##
                feat.setGeometry(QgsGeometry.fromPolyline(
                    [QgsPoint(pt[0], pt[1]) for pt in decoded['coordinates']]
                ))
                routeSink.addFeature(feat)
        del encoded, decoded, cName, sName
        routeSink.FlushBuffer()
        # All routes are now in routeSink as polyline features

        # Cleanup
        del i, j, site, county

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
