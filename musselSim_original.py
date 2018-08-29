"""
Mathematical model of zebra and quagga mussel spread in a water system
By Lucas Ritzdorf

Changes: Two output files

Read this header fully!


Input file format:

[Header - If not included, first data line is ignored.]
Name\tLatitude\tLongitude\tParameter\tValue\tAttractiveness\tInfested\n
Name: String
Lat/Lon: Signed decimals
Parameter: String ("Calcium" or "pH")
Value: Decimal (value of Parameter)
Attractiveness: Integer
Infested: Boolean integer

Where \t is a tab and \n is a newline. Label can be either "Calcium" or "pH".
Calcium units: milligrams per liter
Each site must be on its own line, and the input file must end with a newline.

Sites are organized in sitesDict as [Name : Site] pairs.
The Site class contains information about each site.
"""

# Import required libraries
from math import sqrt, log, radians, cos, sin, acos
from random import randint
import tkinter as tk
from tkinter.filedialog import askopenfilename
from numpy import array, zeros

# Set up variables
sources, uncolonized = list(), list()
lowCalc = 28 # Lower limit for mussel reproduction
lowpH = 7.4 # Lower limit for mussel growth
infestedBoatFraction = 127 / 39522 # Average fraction of boats infested
settleRisk = 0.02 # Risk of mussel settling per infested boat
α = 2
iterations_per_yr = 8
MCLimit = 50
yearlimit = 100

class Site():
    """
    Site object; contains information for monitoring locations.
    Site(self, lat, lon[, pH, pHDate, calcium, calciumDate, percentClean,
         riskLevel, habitability, infested]) -> Site object
    """
    def __init__(self, lat, lon, pH=None, pHDate=None, calcium=None,
                 calciumDate=None, percentClean=0, habitability=0.0,
                 infested=False, initInfested=False, attractiveness=1):
        self._lat =            lat
        self._lon =            lon
        self._pH =             pH
        self._calcium =        calcium
        self._percentClean =   percentClean
        self._habitability =   habitability
        self._infested =       infested
        self._initInfested =   initInfested
        self._attractiveness = attractiveness

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
    def pH(self, new_pH):
        self._pH = new_pH

    @property
    def pHDate(self):
        return self._pHDate

    @pH.setter
    def pHDate(self, new_date):
        self._pHDate = new_date

    @property
    def calcium(self):
        return self._calcium

    @calcium.setter
    def calcium(self, new_ca):
        self._calcium = new_ca

    @property
    def calciumDate(self):
        return self._calciumDate

    @calcium.setter
    def calciumDate(self, new_date):
        self._calciumDate = new_date

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
    def infested(self):
        return self._infested

    def infest(self):
        if self._habitability > 0:
            self._infested = True

    @property
    def initInfested(self):
        return self._initInfested

    def initInfest(self):
        if self._habitability > 0:
            self._initInfested = True

    def resetInfested(self):
        self._infested = self._initInfested


class County():
    """
    County object; contains information for counties.
    County(self, lat, lon, boats) -> County object
    """
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


def distance_in_km(lat1, lon1, lat2, lon2):
    """
    Returns diatance (in kilometers) from two GPS coordinates.
    Coordinates must be in decimal degrees.
    Law of Cosines method from
    https://www.movable-type.co.uk/scripts/latlong.html.
    """
    R = 6371    # Earth's mean radius, in kilometers
    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    delta_lon_rad = radians(lon2-lon1)
    return acos(sin(lat1_rad) * sin(lat2_rad) + cos(lat1_rad) * cos(lat2_rad)
                * cos(delta_lon_rad)) * R


def extract_from(text, pos=1):
    """
    Extract and return the (pos)th item from tab-delimited text.
    """
    pos -= 1
    start,end = 0,0
    tabs = list()
    for x in range(0,len(text)):
        if text[x] == '\t':
            tabs.append(x)
        elif text[x] == '"':
            tabs.append(x)
    tabs.append(-1)
    start = tabs[pos-1]
    end = tabs[pos]
    return text[start + 1:end].strip() + text[end]\
           if pos == len(tabs) - 1 else text[start + 1:end].strip()


def makeSites(inFile):
    """
    Populate and return a dictionary of [Name : Site] pairs (sitesDict).
    Attrs: Site(lat, lon[, pH, calcium, percentCleaned, infested])
    See class Site for further details on Site objects.
    """
    global lowCalc, lowpH
    i = 0
    sitesDict = dict()

    for line in inFile:
        if i == 0:
            i = 1
        else:
            name = extract_from(line, 1)
            lat = float(extract_from(line, 2))
            lon = float(extract_from(line, 3))
            item = Site(lat, lon)
            sitesDict[name] = item

    inFile.seek(0)
    i = 0
    for line in inFile:
        if i == 0:
            i = 1
        else:
            name = extract_from(line, 1)
            date = extract_from(line, 4)
            param = extract_from(line, 5)
            try:
                value = float(extract_from(line, 6))
            except ValueError:
                value = None
            try:
                if (param == 'Calcium') and (date > sitesDict[name].calciumDate):
                    sitesDict[name].calcium = value
                    sitesDict[name].calciumDate = date
                elif (param == 'pH') and (date > sitesDict[name].pHDate):
                    sitesDict[name].pH = value
                    sitesDict[name].pHDate = date
            except TypeError:
                if param == 'Calcium':
                    sitesDict[name].calcium = value
                    sitesDict[name].calciumDate = date
                elif param == 'pH':
                    sitesDict[name].pH = value
                    sitesDict[name].pHDate = date
            sitesDict[name].attractiveness = int(extract_from(line,7))

    for name in sitesDict:
        sitesDict[name].habitability = habitability(
            sitesDict[name],name,lowCalc,lowpH)

    inFile.seek(0)
    i = 0
    for line in inFile:
        if i == 0:
            i = 1
        else:
            name = extract_from(line, 1)
            if bool(int(extract_from(line,8))):
                sitesDict[name].initInfest()

    r = list()
    for name in sitesDict:
        if sitesDict[name].habitability == None:
            r.append(item)

    for name in r:
        del sitesDict[name]
    print(f'\nOmitting {len(r)} sites due to lack of data.')
    del r

    print('Site data internalized.')
    return sitesDict


def makeCounties(countyFile):
    """
    Populate and return a dictionary of [Name : County] pairs (countiesDict).
    Attrs: County(lat, lon, boats).
    See class County for further details on County objects.
    """
    i = 0
    countiesDict = dict()
    for line in countyFile:
        if i == 0:
            i = 1
        else:
            name = extract_from(line, 1)
            lat = float(extract_from(line, 2))
            lon = float(extract_from(line, 3))
            boats = int(extract_from(line, 4))
            item = County(lat, lon, boats)
            countiesDict[name] = item
    print('County data internalized.')
    return countiesDict


# Analysis functions

def habitability(site, name, lowCalc, lowpH):
    """
    Returns the habitability of the site, based on pH and calcium levels.
    Result is a probability expressed as a decimal, or None if no data exists.
    """
    if (site.pH == None) and (site.calcium == None):
        # Cannot compute risk
        return None

    elif site.pH == None:
        # Compute risk based only on calcium
        if 0 <= site.calcium < lowCalc:
            CaFactor = 0
        elif lowCalc <= site.calcium:
            CaFactor = (-1 / (site.calcium - lowCalc + 1)) + 1
        else:
            raise ValueError('Negative calcium value for ' + name)
        return CaFactor

    elif site.calcium == None:
        # Compute risk based only on pH
        if 0 <= site.pH < lowpH:
            pHFactor = 0
        elif lowpH <= site.pH:
            pHFactor = (-1 / (10 * (site.pH - lowpH) + 1)) + 1
        else:
            raise ValueError('Negative pH value for ' + name)
        return pHFactor

    else:
        # Compute risk based on calcium and pH
        # Calcium factor
        if 0 <= site.calcium < lowCalc:
            CaFactor = 0
        elif lowCalc <= site.calcium:
            CaFactor = (-1 / (site.calcium - lowCalc + 1)) + 1
        else:
            raise ValueError('Negative calcium value for ' + name)
        # pH factor
        if 0 <= site.pH < lowpH:
            pHFactor = 0
        elif lowpH <= site.pH:
            pHFactor = (-1 / (10 * (site.pH - lowpH) + 1)) + 1
        else:
            raise ValueError('Negative pH value for ' + name)
        return pHFactor * CaFactor


# Beginning of Main Program
tk.Tk().withdraw()
print('\nWelcome to musselSim_v2.6')

# Open site info file
try:
    print('\nSelect spliced SITES file in the "Open" window...')
    inFilePath = askopenfilename()
    inFile = open(inFilePath, 'r')
except FileNotFoundError:
    # "Open" canceled
    raise FileNotFoundError('File selection was canceled.')
except:
    #Other error
    raise RuntimeError('An error occurred during input-file selection.')
print('Selected file "' + inFilePath + '" as input.')

# Open county info file
try:
    print('\nSelect COUNTY file in the "Open" window...')
    countyFilePath = askopenfilename()
    countyFile = open(countyFilePath, 'r')
except FileNotFoundError:
    # "Open" canceled
    raise FileNotFoundError('File selection was canceled.')
except:
    # Other error
    raise RuntimeError('An error occurred during county file selection.')
print('Selected file "' + countyFilePath + '" for county info.')
del countyFilePath

# Set number of Monte Carlo loops to use
print()
while True:
    try:
        MCLoops = int(input('Number of Monte Carlo loops to run: '))
        assert 1 <= MCLoops <= MCLimit
        break
    except ValueError:
        print('Enter an integer.')
    except AssertionError:
        print(f'Loops must be less than {MCLimit}')

# Set number of years to simulate
print()
while True:
    try:
        years = int(input('Number of years to simulate: '))
        assert 1 <= years <= yearlimit
        break
    except ValueError:
        print('Enter an integer.')
    except AssertionError:
        print(f'Years must be less than {yearlimit}')

# Set percent of boats decontaminated
print()
while True:
    try:
        percent_cleaned = int(input('Percentage of boats decontaminated: '))
        assert 0 <= percent_cleaned <= 100
        break
    except ValueError:
        print('Enter an integer.')
    except AssertionError:
        print('Percentage rules: 0 <= Percent <= 100')

# Define output file
outName = input('\nThe output file will be created in the same folder as the '\
                'SITES file.\nWhat should it be named? ')
outAddr = inFilePath[:len(inFilePath)-inFilePath[::-1].find('/')]
outPath1 = outAddr + outName + '_MonteCarlo.tsv'
outPath2 = outAddr + outName + '_SiteSpecific.tsv'
del outName,outAddr,inFilePath

# Internalize site data
sitesDict = makeSites(inFile)
inFile.close()
del inFile

# Internalize county data
countiesDict = makeCounties(countyFile)
countyFile.close()
del countyFile

# Set up dictionaries correlating indexes to names
c,s = 0,0
countyName,siteName = dict(),dict()
for item in countiesDict:
    countyName[c] = item
    c += 1
for item in sitesDict:
    siteName[s] = item
    s += 1
del c,s

# Set up arrays
# Computed in MODEL CORE
A = zeros(len(countiesDict),dtype=float)
T = zeros([len(countiesDict),len(sitesDict)],dtype=int)
P = zeros(len(countiesDict),dtype=int)
t = zeros([len(countiesDict),len(sitesDict)],dtype=int)
Q = zeros(len(sitesDict),dtype=int)
# Extracted from input
O = zeros(len(countiesDict),dtype=int)
W = zeros(len(sitesDict),dtype=int)
c = zeros([len(countiesDict),len(sitesDict)],dtype=float)
# Results
results = zeros([MCLoops,years,len(sitesDict)],dtype=int)

# Compute distances for c[i][j]
for i in range(len(countiesDict)):
    for j in range(len(sitesDict)):
        c[i][j] = distance_in_km(countiesDict[countyName[i]].lat,
                                 countiesDict[countyName[i]].lon,
                                 sitesDict[siteName[j]].lat,
                                 sitesDict[siteName[j]].lon)

# Set up O[i] and W[i]
i = 0
for item in countiesDict:
    O[i] = countiesDict[item].boats
    i += 1

j = 0
for item in sitesDict:
    W[j] = sitesDict[item].attractiveness
    j += 1

print('Arrays set up; computed c[i][j], O[i], and W[i].')

# Compute A[i]: balancing factor
for i in range(len(countiesDict)):
    for j in range(len(sitesDict)):
        A[i] += W[j] * (c[i][j] ** -α)
    A[i] = 1 / A[i]

# Compute T[i][j]: total boats from county i to lake j
for i in range(len(countiesDict)):
    for j in range(len(sitesDict)):
        T[i][j] = A[i] * O[i] * W[j] * (c[i][j] ** -α)
print('Computed A[i] and T[i].')

# MODEL CORE: Simulate boater and infestation dynamics
print('\nBeginning analysis...')

# Monte Carlo loop
for MCLoop in range(MCLoops):
    print(f'\nMonte Carlo loop {MCLoop}')

    # Reset infestation states
    for s in range(len(sitesDict)):
        sitesDict[siteName[s]].resetInfested()
    del s

    # MAIN LOOP
    for year in range(years):
        print(f'\tYear {year}')
        P.fill(0.0)
        t.fill(0.0)
        Q.fill(0.0)
        
        for iteration in range(iterations_per_yr):
            
            # Compute P[i]: potentially infested boats in county i
            for i in range(len(countiesDict)):
                for j in range(len(sitesDict)):
                    if sitesDict[siteName[j]].infested:
                        P[i] += T[i][j]
                # Adjust for decontamination using percent_cleaned
                P[i] = P[i] * (1 - (percent_cleaned / 100))
            
            # Compute t[i][j]: total infested boats from county i to lake j
            t.fill(0.0)
            for i in range(len(countiesDict)):
                for j in range(len(sitesDict)):
                    t[i][j] = A[i] * P[i] * W[j] * (c[i][j] ** -α)
            
            # Compute Q[j]: total infested boats to lake j
            for j in range(len(sitesDict)):
                for i in range(len(countiesDict)):
                    Q[j] += t[i][j]
            
        # Update infestation states (with stochastic factor)
        for j in range(len(sitesDict)):
            for boat in range(Q[j]):
                if randint(1, (1/settleRisk) - round(sitesDict[siteName[j]]
                                                     .habitability * 5)) == 1:
                    sitesDict[siteName[j]].infest()

        # Store results
        for siteIndex in range(len(sitesDict)):
            results[MCLoop][year][siteIndex]\
                    = sitesDict[siteName[siteIndex]].infested

    # End of MAIN LOOP

# End of Monte Carlo loop

# End of MODEL CORE


# Export results
print('\nExporting...')

# Write general data to output
outFile1 = open(outPath1, 'a')
line1 = 'Year:'
for n in range(years):
    line1 += ('\t' + str(n + 1))
del n
outFile1.write(line1 + '\n')
del line1
outFile1.write('Iteration ')
for itn in range(MCLoops):
    line = f'{itn + 1}:\t'\
           + '\t'.join(str(sum(results[itn][y])) for y in range(years))
    outFile1.write(line + '\n')

# Write site-specific data to output
outFile2 = open(outPath2, 'a')
header = ['Name','Latitude','Longitude','Habitability','Initial']
for year in range(years):
    header.append(f'Year {str(year)}')
outFile2.write('\t'.join(header)
              + f'\nResults are averages over {MCLoops} repeated trials.')
for siteNum in range(len(sitesDict)):
    site = sitesDict[siteName[siteNum]]
    outLine = '\t'.join([siteName[siteNum],str(site.lat),str(site.lon),
                         str(site.habitability),str(site.initInfested)])
    outFile2.write('\n' + outLine)
    for year in range(years):
        outFile2.write('\t' + str(sum(results[loopnum][year][siteNum]
                                      for loopnum in range(MCLoops))
                                  /MCLoops))
outFile2.write('\n')

# Clean up
outFile1.close()
outFile2.close()

# Done
print('\nSimulation complete.\nResults are stored in '
      + f'{outPath1} and {outPath2}.')
input('\nPress enter to exit.')
