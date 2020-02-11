# -*- coding: utf-8 -*-

# Computational model of Dreissenid mussel spread in a given water system,
# built as a QGIS processing script.

# Computes mussel travel, as facilitated by boat traffic, in the given water
# system, then outputs the routes traveled by contaminated boats. This can be
# rendered as a heatmap layer, with more heavily traveled routes having higher
# weights. Such a map highlights sections of road where watercraft inspection
# stations could intercept many contaminated boats.


from PyQt5.QtCore import QCoreApplication, QVariant
# from PyQt5.QtGui import QColor
from qgis.core import *
import processing


class MusselSpreadSimulationAlgorithm(QgsProcessingAlgorithm):
    '''
    Computes mussel travel, as facilitated by boat traffic, in the given water
    system, then outputs the routes traveled by contaminated boats.
    '''

    ROUTES =        'ROUTES'       # Pickled route data file
    STATE_ROUTES =  'STATE_ROUTES' # Pickled state route data file
    MC_LOOPS =      'MC_LOOPS'     # Number of Monte Carlo loops to run
    YEARS =         'YEARS'        # Number of years to simulate
    PROP_DECONT =   'PROP_DECONT'  # Proportion of all boats decontaminated
    INF_PROP =      'INF_PROP'     # Out-of-state boat contamination proportion
    UNINF_PROP =    'UNINF_PROP'   # Out-of-state boat contamination proportion
#    OUTPUT =        'OUTPUT'       # Heatmap layer
    ROUTE_OUTPUT =  'ROUTE_OUTPUT' # Route layer (not as a heatmap)

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
        return self.tr(
            '''
            Create a heatmap of predicted boater travel in a real-world water \
            system, based on a gravity model and geographic data.

            The two file inputs should contain county and state data, in that \
            order. Both should be .pkl files, as created by the \
            RetrieveRoutes.py and RetrieveRoutes_Borders.py scripts.

            The numerical parameters can be adjusted within the limits \
            provided to tune the model's behavior.

            The Monte Carlo loop value determines how many times the entire \
            gravity model will be looped over. Results from this repetition \
            will be averaged and output. Note that this method helps to reduce \
            the effects of randomly choosing whether each individual \
            contaminated boat causes a lake to become infested, while \
            retaining the potential to for unlikely but possible infestation \
            scenarios to occur.
            '''
#            The first output will be a point layer with heatmap styling, \
#            showing routes over which contaminated boats are found to be \
#            likely to travel. Thus, hotspots correspond to sections of road \
#            where a check station could intercept a large number of \
#            contaminated boats.
#        Below: "The second output..."
            + '''

            The output will be a polyline layer, containing individual \
            routes as features, with parameters corresponding to attributes of \
            the lakes to which they lead.

            IMPORTANT: Note that clicking the "Cancel" button in this window \
            will most likely NOT cause the algorithm to end immediately. The \
            algorithm itself is responsible for handling cancellation \
            requests, and does not check for them very frequently. As such, it \
            may take a few minutes for a cancellation command to be acted upon.
            '''
        )


    def initAlgorithm(self, config=None):
        '''
        Define the inputs and outputs of the algorithm, along with some other
        properties.
        '''

        # Add a parameter for the pickled routes input file
        self.addParameter(QgsProcessingParameterFile(
            self.ROUTES,
            self.tr('Pickled Route Data File (from RetrieveRoutes.py)'),
            extension='pkl'
        ))

        # Add a parameter for the pickled state routes input file
        self.addParameter(QgsProcessingParameterFile(
            self.STATE_ROUTES,
            self.tr(
               'Pickled State Route Data File (from RetrieveRoutes_Borders.py)'
               ),
            extension='pkl'
        ))

#        # Add a new vector layer for the output heatmap
#        self.addParameter(QgsProcessingParameterVectorDestination(
#            self.OUTPUT,
#            self.tr('Output Heatmap Layer'),
#            QgsProcessing.TypeVectorPoint
#        ))
#
        # Add a new feature sink (vector layer) for the route, not as a heatmap
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.ROUTE_OUTPUT,
            self.tr('Routes Layer (not as a heatmap)'),
            QgsProcessing.TypeVectorLine
        ))

        # Add a parameter for the number of Monte Carlo loops to run
        self.addParameter(QgsProcessingParameterNumber(
            self.MC_LOOPS,
            self.tr('Number of Monte Carlo loops (repetitive trials) to run'),
            QgsProcessingParameterNumber.Integer,
            minValue=1, maxValue=1000
        ))

        # Add a parameter for the number of years to simulate
        self.addParameter(QgsProcessingParameterNumber(
            self.YEARS,
            self.tr('Number of years to simulate (accuracy likely to decline '\
                    'significantly with increases to this parameter)'),
            QgsProcessingParameterNumber.Integer,
            minValue=1, maxValue=50
        ))

        # Add a paramater for the percentage of boats that are decontaminated
        self.addParameter(QgsProcessingParameterNumber(
            self.PROP_DECONT,
            self.tr('Proportion of all boats that are deconaminated'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0.0,
            minValue=0.0, maxValue=1.0
        ))

        # Add a parameter for infested state contamination proportion
        # From 2018 FWP data:  64 / 24539  ~0.26%
        self.addParameter(QgsProcessingParameterNumber(
            self.INF_PROP,
            self.tr('Proportion of out-of-state boats from an infested state ' \
                'that are contaminated'),
            QgsProcessingParameterNumber.Double,
            defaultValue=(64 / 24539),
            minValue=0.0, maxValue=1.0
        ))

        # Add a parameter for uninfested state contamination proportion
        # Assume 1/100 of infested:  64 / (24539 * 100)  ~0.0026%
        self.addParameter(QgsProcessingParameterNumber(
            self.UNINF_PROP,
            self.tr('Proportion of out-of-state boats from an uninfested ' \
                'state that are contaminated'),
            QgsProcessingParameterNumber.Double,
            defaultValue=(64 / (24539 * 100)),
            minValue=0.0, maxValue=1.0
        ))

        # Add paramters for model-specific variables:
        self.addParameter(QgsProcessingParameterNumber(
            self.LOW_CALC,
            self.tr('Calcium concentration below which mussels cannot ' \
                'survive (in mg/L)'),
            QgsProcessingParameterNumber.Double,
            defaultValue=28,
            minValue=0.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.LOW_PH,
            self.tr('pH level below which mussels cannot survive'),
            QgsProcessingParameterNumber.Double,
            defaultValue=7.4,
            minValue=0.0, maxValue=14.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.SETTLE_RISK,
            self.tr('Probability that a contaminated boat causes the lake it ' \
            'arrives at to become infested'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0.02,
            minValue=0.0, maxValue=1.0
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.TRIPS_PER_YEAR,
            self.tr('Number of trips to a lake that each boat makes per year'),
            QgsProcessingParameterNumber.Integer,
            defaultValue=8,
            minValue=1, maxValue=20
        ))

        # Consider adding additional vector output layers for lakes and county
        # centers (QgsProcessing.TypeVectorPoint)


    def processAlgorithm(self, parameters, context, feedback):
        '''
        Here is where the processing itself takes place.
        '''

        from openrouteservice.convert import decode_polyline
        import pickle

        # Define data-storage classes for Sites and Counties

        # TODO: Add `assert`ions for @*.setter definitions (infested->bool, etc)
        class Site():
            '''
            Site object; contains information for monitoring locations.
            Site(self, lat, lon[, pH, pHDate, calcium, calciumDate,
            percentClean, habitability, attractiveness, initInfested])
            -> Site object
            '''
            def __init__(self, lat, lon, pH=None, calcium=None,
                         attractiveness=1, initInfested=False, habitability=0.):
                self._lat =            lat
                self._lon =            lon
                self._pH =             pH
                self._calcium =        calcium
                self._attractiveness = attractiveness
                self._initInfested =   initInfested
                self._habitability =   habitability

            @property
            def lat(self):
                return self._lat

            @property
            def lon(self):
                return self._lon

            @property
            def pH(self):
                return self._pH

            @property
            def calcium(self):
                return self._calcium

            @property
            def attractiveness(self):
                return self._attractiveness

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

            @property
            def habitability(self):
                return self._habitability

            @habitability.setter
            def habitability(self, new_hab):
                self._habitability = new_hab


        class County():
            '''
            County object; contains information for counties.
            County(self, lat, lon[, boats]) -> County object
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


        class State():
            '''
            Border object; contains information for border entry points.
            Border(self, lat, lon, states) -> Border object
            where "states" is a list of state names, locations, and boats.
            '''
            def __init__(self, lat, lon, boats, infested, border):
                self._lat =      lat
                self._lon =      lon
                self._boats =    boats
                self._infested = infested
                self._border =   border

            @property
            def lat(self):
                return self._lat

            @property
            def lon(self):
                return self._lon

            @property
            def boats(self):
                return self._boats

            @property
            def infested(self):
                return self._infested

            @property
            def border(self):
                return self._border


        # Define habitability function
        def habitability(pH, calcium, lowpH, lowCalc):
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


        # Retrieve parameters:
        feedback.setProgressText('Retrieving input parameters...')

        # Pickled routes file
        pickledFileName = self.parameterAsFile(
            parameters,
            self.ROUTES,
            context)
        # Pickled border routes file
        stateFileName = self.parameterAsFile(
            parameters,
            self.STATE_ROUTES,
            context)
        # Number of Monte Carlo loops to run
        MCLoops = self.parameterAsInt(
            parameters,
            self.MC_LOOPS,
            context)
        # Number of years to simulate
        years = self.parameterAsInt(
            parameters,
            self.YEARS,
            context)
        # Proportion of all boats assumed to be decontaminated
        propCleaned = self.parameterAsDouble(
            parameters,
            self.PROP_DECONT,
            context)
        # Proportion of infested out-of-state boats assumed to be contaminated
        infProp = self.parameterAsDouble(
            parameters,
            self.INF_PROP,
            context)
        # Proportion of uninfested out-of-state boats assumed to be contaminated
        uninfProp = self.parameterAsDouble(
            parameters,
            self.UNINF_PROP,
            context)
        # Model-specific variables:
        lowCalc = self.parameterAsDouble(parameters,
            self.LOW_CALC,
            context)
        lowpH = self.parameterAsDouble(parameters,
            self.LOW_PH,
            context)
        settleRisk = self.parameterAsDouble(parameters,
            self.SETTLE_RISK,
            context)
        tripsPerYear = self.parameterAsInt(parameters,
            self.TRIPS_PER_YEAR,
            context)

        # Internalize pickled counties, borders, sites, and routes
        # Format:
        #  Counties: name str, lat float, lon float, boats int
        #  States: name str, lat float, lon float, boats int,
        #          border list [name str, lat float, lon float]
        #  Sites: name str, lat float, lon float, pH float|None,
        #         calcium float|None, attractiveness int, initInfested bool
        feedback.setProgressText('Retrieving pickled routes from file...')
        # For counties:
        with open(pickledFileName, 'rb') as pickledFile:
            (countiesList, sitesList, routeMatrix) = pickle.load(pickledFile)
        del pickledFile
        # For outside states:
        with open(stateFileName, 'rb') as stateFile:
            (statesList, stSitesList, stRouteMatrix) = pickle.load(stateFile)
        del stateFile
        # Check to be sure routes are present for the same sites in each file
        if not stSitesList == sitesList:
            feedback.reportError(
                'In-state and out-of-state lakes do not match. Aborting.',
                fatalError=True)
            return {None: None}
        del stSitesList

        # Convert (name, lat, lon, **info) tuples into native objects
        counties = dict()
        for item in countiesList:
            counties[item[0]] = County(item[1], item[2], item[3])
        sites = dict()
        for item in sitesList:
            sites[item[0]] = Site(item[1], item[2], item[3], item[4],
                                  item[5], item[6])
        states = dict()
        for item in statesList:
            states[item[0]] = State(item[1], item[2], item[3], item[4], item[5])
        del item, countiesList, sitesList, statesList


        # Begin Processing
        feedback.pushInfo('Beginning processing')
        from random import choices
        from numpy import array, zeros
        c = zeros([len(counties),len(sites)],dtype=float)
        cs = zeros([len(states),len(sites)],dtype=float)

        # Create route polylines
        feedback.setProgressText('Calculating internal route lengths... '\
                                 '(This could take a while)')
        for i in range(len(counties)):
            # Cancellation check
            if feedback.isCanceled():
                return {None: None}
            # Progress update
            feedback.setProgress(round(100 * i / (len(counties) - 1)))

            for j in range(len(sites)):
                encoded = routeMatrix[i][j]
                decoded = decode_polyline(encoded)
                feat = QgsFeature()
                feat.setGeometry(QgsGeometry.fromPolyline(
                    [QgsPoint(pt[0], pt[1]) for pt in decoded['coordinates']]))
                # Store feature for later retrieval (to avoid taking a really
                # long time regenerating feature geometry when creating output)
                routeMatrix[i][j] = feat
                # Add distance to array c[i][j]
                c[i][j] = feat.geometry().length() * 10  # Gives length in km
        # Route distances are now stored in c[i][j]

        feedback.setProgressText('Calculating out-of-state route lengths... '\
                                 '(This could take a while)')
        for i, s in enumerate(states.values()):
            # Cancellation check
            if feedback.isCanceled():
                return {None: None}
            # Progress update
            feedback.setProgress(round(100 * i / (len(states) - 1)))

            for j in range(len(sites)):
                encoded = stRouteMatrix[i][j]
                decoded = decode_polyline(encoded)
                feat = QgsFeature()
                # Set geometry, including a straight path to state center
                feat.setGeometry(QgsGeometry.fromPolyline(
                    [QgsPoint(pt[0], pt[1]) for pt in (
                        [[s.lon, s.lat]] + decoded['coordinates'])]))
                # Store feature for later retrieval to save time
                stRouteMatrix[i][j] = feat
                # Add distance to array cs[i][j]
                cs[i][j] = feat.geometry().length() * 10  # Converts to km
        # Border route distances are now stored in cb[i][j]
        del encoded, decoded, s

        # TODO: Pickle routeMatrix in QGIS temp folder to reduce processing
        # time for future alg runs

        # Begin Model
        feedback.setProgressText('Starting Monte Carlo model')
        feedback.setProgress(0)

        # Define a model-specific parameter:
        α = 2

        # Calculate habitability values
        for site in sites.values():
            site.habitability \
                = habitability(site.pH, site.calcium, lowpH, lowCalc)

        # Set up arrays
        # Computed in Model:
        A = zeros(len(counties),dtype=float)
        As = zeros(len(states),dtype=float)
        T = zeros([len(counties),len(sites)],dtype=int)
        Ts = zeros([len(states),len(sites)],dtype=int)
        P = zeros(len(counties),dtype=int)
        t = zeros([MCLoops,years,len(counties),len(sites)],dtype=int)
        ts = zeros([MCLoops,years,len(states),len(sites)],dtype=int)
        Q = zeros([len(counties),len(sites)],dtype=int)
        # Extracted from input:
        O = zeros(len(counties),dtype=int)
        Os = zeros(len(states),dtype=int)
        W = zeros(len(sites),dtype=int)
        # c has already been set up and populated with distances, as has cs
        # Results:
        avgInfest = zeros([years,len(sites)],dtype=float)
        feedback.pushInfo('Arrays set up')

        # Set up O[i], Os[i], and W[j]
        for i, county in enumerate(counties.values()):
            O[i] = county.boats
        for i, state in enumerate(states.values()):
            Os[i] = state.boats
        for j, site in enumerate(sites.values()):
            W[j] = site.attractiveness
        # c has already been set up and populated with distances, as has cs
        feedback.pushInfo('Computed c[i][j], cs[i][j], O[i], Os[i], and W[j]')

        # Compute A[i]: balancing factor
        for i in range(len(counties)):
            for j in range(len(sites)):
                A[i] += W[j] * (c[i][j] ** -α)
            A[i] = 1 / A[i]

        # Compute As[i]: balancing factor for states
        for i in range(len(states)):
            for j in range(len(sites)):
                As[i] += W[j] * (cs[i][j] ** -α)
            As[i] = 1 / As[i]

        # Compute T[i][j]: total boats from county i to lake j
        for i in range(len(counties)):
            for j in range(len(sites)):
                T[i][j] = A[i] * O[i] * W[j] * (c[i][j] ** -α)

        # Compute Ts[i][j]: total boats from state i to lake j
        for i in range(len(states)):
            for j in range(len(sites)):
                Ts[i][j] = As[i] * Os[i] * W[j] * (cs[i][j] ** -α)

        feedback.pushInfo('Computed A[i], As[i], T[i][j], and Ts[i][j]')

        # Begin Model Core and Monte Carlo loop
        feedback.setProgressText('\nRunning model...')

        for MCLoop in range(MCLoops):

            feedback.pushInfo(f'Monte Carlo loop {MCLoop}')

            # Reset infestation statuses
            for site in sites.values():
                site.resetInfested()

            # Begin Main Loop
            for year in range(years):
                feedback.pushInfo(f'\tYear {year}')

                # Cancellation check
                if feedback.isCanceled():
                    return {None: None}
                # Progress update
                feedback.setProgress(int(100 * \
                    ((MCLoop * years) + year + 1) / (MCLoops * years)))

                # Compute P[i]: potentially infested boats in county i
                # Note: This assumes that boats take on the status of the
                #  lakes they visit. I.e. a contaminated boat visiting a
                #  clean lake could contaminate the lake, but the boat
                #  becomes clean. Thus, in a given year, each county always has
                #  the same number of contaminated boats from the same lakes.
                P.fill(0)
                for i in range(len(counties)):
                    for j, site in enumerate(sites.values()):
                        if site.infested:
                            P[i] += T[i][j]

                # Compute t[i][j]: infested boats from county i to lake j
                for i in range(len(counties)):
                    for j in range(len(sites)):
                        t[MCLoop][year][i][j] \
                                        = A[i] * P[i] * W[j] * (c[i][j] ** -α)

                # Compute Q[i][j]: yearly infested boats, i to j
                Q.fill(0)
                for j in range(len(sites)):
                    for i in range(len(counties)):
                        Q[i][j] += (tripsPerYear - 1) * t[MCLoop][year][i][j]
                    # Add contaminated out-of-state boats to ts
                    for i, state in enumerate(states.values()):
                        # Randomly choose whether each out-of-state boat is
                        # contaminated; store in ts
                        for boat in range(Ts[i][j]):
                            if choices(
                               [1, 0],
                               [(infProp if state.infested else uninfProp),
                                1 - (infProp if state.infested \
                                     else uninfProp)]
                               )[0] == 1:
                                ts[MCLoop][year][i][j] += 1
                        # Add ts (contaminated boats from state i to lake j)
                        # to Q[i][j]
                        Q[i][j] += ts[MCLoop][year][i][j]

                    # Adjust for decontamination using propCleaned
                    # TODO: Redo this to be stochastic
                    Q = (Q * (1 - propCleaned)).round()

                # Update infestation states (with stochastic factor)
                for j, site in enumerate(sites.values()):
                    for boat in range(int(sum(Q)[j])):
                        if choices(
                            [1, 0],
                            [settleRisk * (2 * site.habitability),
                             1 - (settleRisk * (2 * site.habitability))]
                            )[0] == 1:
                            site.infest()
                    # Update average infestation rate
                    avgInfest[year][j] = (MCLoop * avgInfest[year][j] \
                        + int(site.infested)) / (MCLoop + 1)

            # End Main Loop

        del site, boat
        # End Monte Carlo loop and Model Core

        # End Model
        feedback.pushInfo('Completed Monte Carlo model')

        # Add field definitions:
        fields = QgsFields()
        fList = [QgsField('Origin', QVariant.String),
                 QgsField('Lake', QVariant.String),
                 QgsField('pH', QVariant.Double),
                 QgsField('Calcium', QVariant.Double),
                 QgsField('Habitability', QVariant.Double),
                 QgsField('Attractiveness', QVariant.Int),
                 # Boats on Route fields will go here
                 # Infestation Proportion fields will go here
                 QgsField('Initially Infested', QVariant.Bool),
                 QgsField('Origin Infested', QVariant.Bool),
                 QgsField('Origin Type', QVariant.String)]
        for n in range(years):
            fList.insert(n + 7,
                QgsField(f'Year {n} Infestation Proportion', QVariant.Double))
        for n in range(years):
            fList.insert(n + 6,
                QgsField(f'Year {n} Boats on Route', QVariant.Double))
        for field in fList:
            fields.append(field)
        del fList, n
        # Sink and ID for the route output layer
        (routeSink, routeSinkID) = self.parameterAsSink(
            parameters,
            self.ROUTE_OUTPUT,
            context,
            fields,
            geometryType=QgsWkbTypes.LineString,
            crs=QgsCoordinateReferenceSystem('EPSG:4326')
        )

        # Add route polylines to route layer
        feedback.setProgressText('Adding routes to output layer... '\
                                 '(This could take a while)')
        # Create matrices for average number of boats on routes
        inStBoats = sum(t) / MCLoops
        outStBoats = sum(ts) / MCLoops

        for i, (cName, county) in enumerate(counties.items()):
            # Progress update
            feedback.setProgress(round(100 * i
                                       / (len(counties) + len(states) - 1)))
            for j, (sName, site) in enumerate(sites.items()):
                # Cancellation check
                if feedback.isCanceled():
                    return {None: None}
                feat = routeMatrix[i][j]
                feat.setFields(fields, initAttributes=True)
                # Transfer attributes from each site to its feature
                feat.setAttributes([cName,
                                    sName,
                                    site.pH,
                                    site.calcium,
                                    site.habitability,
                                    site.attractiveness]
                                   + [float(inStBoats[y][i][j])
                                      for y in range(years)]
                                   + [float(avgInfest[j][y])
                                      for y in range(years)]
                                   + [site.initInfested,
                                      None,
                                      'internal county'])
                routeSink.addFeature(feat)
        for i, (tName, state) in enumerate(states.items()):
            # Cancellation check
            if feedback.isCanceled():
                return {None: None}
            # Progress update
            feedback.setProgress(round(100 * (len(counties) + i)
                                       / (len(counties) + len(states) - 1)))
            for j, (sName, site) in enumerate(sites.items()):
                feat = stRouteMatrix[i][j]
                feat.setFields(fields, initAttributes=True)
                # Transfer attributes from each site to its feature
                feat.setAttributes([tName,
                                    sName,
                                    site.pH,
                                    site.calcium,
                                    site.habitability,
                                    site.attractiveness]
                                   + [float(outStBoats[y][i][j])
                                      for y in range(years)]
                                   + [float(avgInfest[j][y])
                                      for y in range(years)]
                                   + [site.initInfested,
                                    state.infested,
                                    'external district'])
                routeSink.addFeature(feat)
        del cName, tName, sName, avgInfest, feat
        routeSink.flushBuffer()
        # All routes are now in routeSink as polyline features

        # Cleanup
        del i, j, site, county, state


# TODO: This could be replaced by using a transparent line symbology
#  Left examples below for creating and setting a renderer

#        # Set up heatmap renderer
#        # ^ Set weight for each point from field(s) (research)
#        rndrr = QgsHeatmapRenderer()
#        rndrr.setColorRamp(QgsGradientColorRamp(
#            QColor('transparent'),QColor(227,26,28)))
#        rndrr.setRadiusUnit(1)
#        rndrr.setRadius(500)
#
#        # Assign heatmap renderer to extracted vertices layer
#        QgsProcessingUtils.mapLayerFromString(vertices['OUTPUT'], context
#            ).setRenderer(rndrr)

        # End Processing
        feedback.setProgressText('Processing complete; finishing up...')

        # Return output layers
        return {self.ROUTE_OUTPUT: routeSinkID}
#        return {self.OUTPUT:       vertices['OUTPUT'],
#                self.ROUTE_OUTPUT: routeSinkID}
