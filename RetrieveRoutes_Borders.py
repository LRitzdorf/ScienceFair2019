# Data-acquisition program written by Lucas Ritzdorf

# Designed to pull route data from OpenRouteService (openrouteservice.org) and
# store it in a text file for later access by a computational model.

# Data will be stored in "encoded polyline" form, as a string of characters.
# This data can be converted to a series of points by the
# openrouteservice.convert.decode_polyline() function, with the string
# representing the encoded polyline as its only argument. This would be done in
# the program utilizing the stored data.

version = 'v0.2_borderStations'


# Import required libraries
import openrouteservice
import tkinter as tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from numpy import full, delete
import csv
from datetime import date
from time import time, sleep
import pickle


# Define Site and BorderPoint classes

class Site():
    '''
    Site object; contains information for monitoring locations.
    Site(self, lat, lon[, pH, pHDate, calcium, calciumDate,
    percentClean, habitability, attractiveness, initInfested])
    -> Site object
    '''
    def __init__(self, lat, lon, pH=None, pHDate=None, calcium=None,
                 calciumDate=None, attractiveness=1, initInfested=False):
        self._lat =            lat
        self._lon =            lon
        self._pH =             pH
        self._pHDate =         pHDate
        self._calcium =        calcium
        self._calciumDate =    calciumDate
        self._attractiveness = attractiveness
        self._initInfested =   initInfested

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
    def pHDate(self):
        return self._pHDate

    def addpH(self, newpH, newDate):
        if (self._pHDate == None) or (newDate > self._pHDate):
            self._pH = newpH
            self._pHDate = newDate
            return True
        return False

    @property
    def calcium(self):
        return self._calcium

    @property
    def calciumDate(self):
        return self._calciumDate

    def addCa(self, newCa, newDate):
        if (self._calciumDate == None) or (newDate > self._calciumDate):
            self._calcium = newCa
            self._calciumDate = newDate
            return True
        return False

    @property
    def attractiveness(self):
        return self._attractiveness

    @attractiveness.setter
    def attractiveness(self, new_attr):
        self._attractiveness = new_attr

    @property
    def initInfested(self):
        return self._initInfested

    @initInfested.setter
    def initInfested(self, newState):
        self._initInfested = newState
        self.resetInfested()


class BorderPoint():
    '''
    BorderPoint object; contains information for borders.
    BorderPoint(self, lat, lon[, route, states]) -> BorderPoint object
    '''
    def __init__(self, lat, lon):
        self._lat =    lat
        self._lon =    lon
        self._states = set()

    @property
    def lat(self):
        return self._lat

    @property
    def lon(self):
        return self._lon

    @property
    def states(self):
        return self._states

    def addState(self, name, lat, lon, boats):
        self._states.add({'name':name, 'lat':lat, 'lon':lon, 'boats':boats})


print(f'OpenRouteService Route Retrieval Program {version}\n')


# Request border, lake, and output files
tk.Tk().withdraw()
print('Select the LAKE file in the "Open" window...')
lakePath = askopenfilename()
if lakePath == '':
    print('No file selected; cancelling...'); exit()
print('Select the BORDER file in the "Open" window...')
borderPath = askopenfilename()
if borderPath == '':
    print('No file selected; cancelling...'); exit()
print('Type the name of the new OUTPUT file in the window...')
outputPath = asksaveasfilename(defaultextension='.pickle', filetypes=(
    ('Pickle File','*.pkl'),('All Files','*.*')))
if outputPath == '':
    print('No file selected; cancelling...'); exit()

# (Try to) Open input files
try:
    with open(borderPath, 'r') as borderFile, open(lakePath, 'r') as lakeFile:
        # Internalize border and lake data, ensuring that the most up-to-date
        # records are used for each lake

        # Create dicts containing names and objects, in the same order that
        # they appear in the data matrix (borders on the vertical axis, sites
        # on the horizontal)
        sites = {}
        borders = {}

        # Populate object lists from data files
        # BorderPoint data
        dialect = csv.Sniffer().sniff(borderFile.read(1024)); borderFile.seek(0)
        borderReader = csv.reader(borderFile, dialect)
        # Get past, and validate, header line
        try:
            assert borderReader.__next__() \
                   == ['Name','Latitude','Longitude','State','StateLat',
                       'StateLon','Boats']
        except AssertionError:
            print('Border point file header does not match expected. Please '\
                  'ensure that you chose the correct file as input, and try '\
                  'again. Error trace:')
            raise
        for line in borderReader:
            if line[0] not in borders:
                borders[line[0]] = BorderPoint(float(line[1]), float(line[2]))
            borders[line[0]].addState(line[3], line[4], line[5], line[6])
        del borderReader
        # Site data
        dialect = csv.Sniffer().sniff(lakeFile.read(1024)); lakeFile.seek(0)
        lakeReader = csv.reader(lakeFile, dialect)
        # Get past, and validate, header line
        try:
            assert lakeReader.__next__() \
                   == ['IDNumber','Latitude','Longitude','Date', \
                       'Parameter','Value','Attractiveness','Infested']
        except AssertionError:
            print('Lake file header does not match expected. Please ensure '\
                  'that you chose the correct file as input, and try again. '\
                  'Error trace:')
            raise
        for line in lakeReader:
            try:
                if line[0] not in sites:
                    sites[line[0]] = Site(float(line[1]), float(line[2]))
                if line[4] == 'pH':
                    sites[line[0]].addpH(float(line[5]),
                                         date.fromisoformat(line[3]))
                elif line[4] == 'Calcium':
                    sites[line[0]].addCa(float(line[5]),
                                         date.fromisoformat(line[3]))
            except ValueError:
                pass

        # Create a data matrix to hold encoded polyline strings
        routeMatrix = full((len(borders),len(sites)), '', dtype=object)

except FileNotFoundError as e:
    print(f'\nCould not find "{e.filename}". Please check for typing errors '\
          'and try again.\nFull error trace:')
    raise


# Query user's ORS API key and ratelimit
print('\nBe aware that all ORS API requests will be charged against your '\
      'Directions V2 quota in OpenRouteService. The total number of requests '\
      'made will be less than or equal to the number of input borders '\
      'multiplied by the number of input water bodies '\
      f'({len(borders) * len(sites)}).\n')
key = input('Type (or paste) your API key here:\n')
while True:
    try:
        ratelimit = int(input('Type the number of queries per minute your '\
                              'key is allowed to use (its rate limit - '\
                              'usually 40, or use 0 for no limit):\n'))
        if ratelimit < 0:
            raise ValueError
        break
    except ValueError:
        print('Must be an integer greater than zero.')

# Actual data retrieval
count = 0
ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
badBorders, badSites = set(), set()
start_time = time()
client = openrouteservice.Client(key=key, retry_over_query_limit=True)
for bi, border in enumerate(borders):
    for si, site in enumerate(sites):
        if si in badSites:
            # Leave routeMatrix[ci][si] unaltered (empty)
            continue
        # Ratelimiting
        if ratelimit > 0:
            # Wait for remainder of averge query time
            remain = start_time + (60 / ratelimit) - time()
            if remain > 0:
                sleep(remain)
            start_time = time()
        elif ratelimit == 0:
            # No rate limit; continue
            pass
        # Get directions for the route and write to output file
        try:
            start = (borders[border].lon, borders[border].lat)
            end = (sites[site].lon, sites[site].lat)
            count += 1
            routes = client.directions((start, end))
            encoded = routes['routes'][0]['geometry']
        # Address several possible errors returned by the API
        except openrouteservice.exceptions.ApiError as e:
            print('\nAn error occurred while making an ORS Directions query. '\
                  'The error occurred on the {ordinal(count)} query. '\
                  'A brief description is shown above the full error, as '\
                  'reported by the server:')
            if e.args[0] == 401:
                print('The API key is missing from the request.')
            elif e.args[0] == 403:
                print('The API key is not valid.')
            elif e.args[0] == 404:
                print('Unable to find requested object')
            elif e.args[0] == 413:
                print('The request is too large.')
            elif e.args[0] == 429:
                print('Query limit exceeded.')
            elif e.args[0] == 500:
                if e.args[1]['error']['code'] == 2099:
                    # Assume that the second point (the site) cannot be found
                    badSites.add(si)
                    print('Unroutable site (assumed) found; skipping...')
                    continue
                else:
                    print('An unknown server error occurred.')
            elif e.args[0] == 501:
                print('The server cannot fulfill this request.')
            elif e.args[0] == 503:
                print('The server is currently unavailable due to overload '\
                      'or maintenance.')
            else:
                print('An unlikely error occurred. Please try again. If the '\
                      'issue persists, something very serious has changed in '\
                      'the OpenRouteService API.')
            raise
        except openrouteservice.exceptions.TransportError:
            raise RuntimeError('An HTTPS error occurred. You may be offline. '\
                               'Please check your connection and try again.')
        # Query successful, encoded polyline string stored in "encoded"
        routeMatrix[bi][si] = encoded
    # Can get here from the break when a bad border is detected, or when done
    # with all sites for the current border. Either way, continue to the next
    # border.

# Done with data acquisition; report number of queries made to user
print(f'Made a total of {count} ORS Directions queries.')
del ordinal

# Remove problematic locations (borders or sites) from dicts and matrix
for i, k in enumerate(borders.keys()):
    if i in badBorders:
        del borders[k]
for i, k in enumerate(sites.keys()):
    if i in badSites:
        del sites[k]
routeMatrix = delete(routeMatrix, list(badBorders), 0)
routeMatrix = delete(routeMatrix, list(badSites), 1)

# Convert object lists into an easier-to-retrieve format
bordersList = [
    ( i[0], i[1].lat, i[1].lon, i[1].states )
    for i in borders.items()]
sitesList = [
    ( i[0], i[1].lat, i[1].lon, i[1].pH, i[1].calcium, i[1].attractiveness,
      i[1].initInfested )
    for i in sites.items()]
del i

# Export data to file by pickling
with open(outputPath, 'wb') as outputFile:
    try:
        pickle.dump((bordersList, sitesList, routeMatrix), outputFile)
        # These need to be retrieved as a tuple, via one pickle.load() call
    # Address the possibility of a file error (name changed, etc.)
    except IOError:
        print('An error occurred while writing data to the output '\
              'file. Full error trace:')
        raise

print('Complete; exiting.')
