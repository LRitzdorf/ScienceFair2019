# Data-acquisition program written by Lucas Ritzdorf

# Designed to pull route data from OpenRouteService (openrouteservice.org) and
# store it in a text file for later access by a computational model.

# Data will be stored in "encoded polyline" form, as a string of characters.
# This data can be converted to a series of points by the
# openrouteservice.convert.decode_polyline() function, with the string
# representing the encoded polyline as its only argument. This would be done in
# the program utilizing the stored data.

version = 'v0.1'


# Import required libraries
import openrouteservice
import tkinter as tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from numpy import full
import csv
from datetime import date

# Define Site and County classes
class Site():
    '''
    Site object; contains information for monitoring locations.
    Site(self, lat, lon[, pH, pHDate, calcium, calciumDate]) -> Site object
    '''
    def __init__(self, lat, lon, pH=None, pHDate=None, calcium=None,
                 calciumDate=None):
        self._lat =         lat
        self._lon =         lon
        self._pH =          pH
        self._pHDate =      pHDate
        self._calcium =     calcium
        self._calciumDate = calciumDate

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

print(f'OpenRouteService Route Retrieval Program {version}\n')


# Request county, lake, and output files
tk.Tk().withdraw()
lakePath,countyPath,outputPath = '','',''
while lakePath == '':
    print('Select the LAKE file in the "open" window...')
    lakePath = askopenfilename()
while countyPath == '':
    print('Select the COUNTY file in the "Open" window...')
    countyPath = askopenfilename()
while outputPath == '':
    print('Type the name of the new OUTPUT file in the window...')
    outputPath = asksaveasfilename(defaultextension='.csv', filetypes=(
        ('CSV (Comma-Separated Values) File','*.csv'),
        ('TSV (Tab-Separated Values) File','*.tsv'),
        ('All Files','*.*')))
    outputSep = '\t' if outputPath.endswith('.tsv') else ','

# (Try to) Open input files
try:
    with open(countyPath, 'r') as countyFile, open(lakePath, 'r') as lakeFile:
        # Internalize county and lake data, ensuring that the most up-to-date
        # records are used for each lake

        # Create dicts containing names and objects, in the same order that
        # they appear in the data matrix (counties on the vertical axis, sites
        # on the horizontal)
        sites = {}
        counties = {}

        # Populate object lists from data files
        # County data
        dialect = csv.Sniffer().sniff(countyFile.read(1024)); countyFile.seek(0)
        countyReader = csv.reader(countyFile, dialect)
        # Get past, and validate, header line
        try:
            assert countyReader.__next__() \
                   == ['County','Latitude','Longitude','Boats','County Seat']
        except AssertionError:
            print('County file header does not match expected. Please ensure '\
                  'that you chose the correct file as input, and try again. '\
                  'Error trace:')
            raise
        for line in countyReader:
            if line[0] not in counties:
                counties[line[0]] = County(float(line[1]), float(line[2]),
                                           int(line[3]))
        del countyReader
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
            if line[0] not in sites:
                sites[line[0]] = Site(float(line[1]), float(line[2]))
            if line[4] == 'pH':
                sites[line[0]].addpH(float(line[5]),date.fromisoformat(line[3]))
            elif line[4] == 'Calcium':
                sites[line[0]].addCa(float(line[5]),date.fromisoformat(line[3]))

        #Use addpH(value, date) and addCa(value, date) methods of Site()
        #objects to add data - will only be added if date is newer than
        #current data date. Returns boolean values to show whether data was
        #added or not.

        # Create a data matrix to hold encoded polyline strings
        routeMatrix = full((len(counties),len(sites)), '', dtype=object)
        
except FileNotFoundError as e:
    print(f'\nCould not find "{e.filename}". Please check for typing errors '\
          'and try again.\nFull error trace:')
    raise


# Query user's ORS API key
print('\nBe aware that all ORS API requests will be charged against your '\
      'Directions V2 quota in OpenRouteService. The total number of requests '\
      'made will be exactly equal to the number of input counties multiplied '\
      'by the number of input water bodies.\n')
key = input('Type (or paste) your API key here:\n')

# Actual data retrieval
count = 0
client = openrouteservice.Client(key=key)
for ci, county in enumerate(counties):
    for li, site in enumerate(sites):
        # Get directions for the route and write to output file
        try:
            start = (counties[county].lon, counties[county].lat)
            end = (sites[site].lon, sites[site].lat)
            routes = client.directions((start, end))
            count += 1
            encoded = routes['routes'][0]['geometry']
        # Address several possible errors returned by the API
        except openrouteservice.exceptions.ApiError as e:
            print('An error occurred while making an ORS Directions query. A '\
                  f'total of {count} queries were made prior to the error. A '\
                  'brief description is shown above the full error, as '\
                  'reported by the server:')
            if e.args[0] == 401:
                print('The API key is missing from the request.')
            elif e.args[0] == 403:
                print('The API key is not valid.')
            elif e.args[0] == 404:
                print('Unable to find requested object')
                if e.args[1]['error']['code'] == 2010:
                    if e.args[1]['error']['message'][18] == '0':
                        # The first point (the county) cannot be found
                        #Add to a set to:
                        ##Remove the county from the dict
                        ##Remove its row from the matrix
                        pass
                    elif e.args[1]['error']['message'][18] == '1':
                        # The second point (the site) cannot be found
                        #Add to a set to:
                        ##Remove the site from the dict
                        ##Remove its column from the matrix
                        pass
            elif e.args[0] == 413:
                print('The request is too large.')
            elif e.args[0] == 500:
                print('An unknown server error occurred.')
            elif e.args[0] == 501:
                print('The server cannot fulfill this request.')
            elif e.args[0] == 503:
                print('The server is currently unavailable due to '\
                      'overload or maintenance.')
            else:
                print('An unlikely error occurred. Please try again. If '\
                      'the issue persists, something very serious has '\
                      'changed in the OpenRouteService API.')
            raise
        # Query successful, encoded polyline string stored in "encoded"
        routeMatrix[ci][li] = encoded

# Done with data acquisition; report number of queries made to user
print(f'Made a total of {count} ORS Directions queries.')

# Remove problematic locations (counties or sites) from dicts and matrix
#According to (probably a set of) problematic locations from above

# Export data to file by pickling
with open(outputPath, 'a') as outputFile:
    try:
        for obj in (counties, sites, routeMatrix):
            pickle.dump(obj, outputFile)
            # These need to be retrieved in order, via subsequent
            # pickle.load() calls.
    # Address the possibility of a file error (name changed, etc.)
    except IOError:
        print('An error occurred while writing data to the output '\
              'file. Full error trace:')
        raise

print('Complete; exiting.')
