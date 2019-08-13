# Data-acquisition program written by Lucas Ritzdorf

# Designed to pull route data from OpenRouteService (openrouteservice.org) and
# store it in a text file for later access by a computational model.

# Data will be stored in "encoded polyline" form, as a string of characters.
# This data can be converted to a series of points by the
# openrouteservice.convert.decode_polyline(enc) function, where enc is the
# string representing the encoded polyline. This would be done in the program
# utilizing the stored data.


# Open county file
countyPath = os.getcwd() + '\\' + input('Type the name of the COUNTY file, ' \
                                       'relative to your current path:\n')
countyFile = open(countyPath, 'r')
# Open lake file
lakePath = os.getcwd() + '\\' + input('Type the name of the LAKE file, ' \
                                       'relative to your current path:\n')
lakeFile = open(lakePath, 'r')
# Create and open output file
# Query user's ORS API key
print('\nBe aware that all ORS API requests will be charged against your '\
      'Directions V2 quota in OpenRouteService. The total number of requests '\
      'made will be exactly equal to the number of input counties multiplied '\
      'by the number of input water bodies.\n'
key = input('Type (or paste) your API key here:\n')

# Actual data retrieval
count = 0
for cLine in countyFile:
    for lLine in lakeFile:
        count += 1
        #Get route from ORS using queried key
        #Write route and orig/dest to output file

print(f'Complete; made a total of {count} queries')
