# Data-acquisition program written by Lucas Ritzdorf

# Designed to pull route data from OpenRouteService (openrouteservice.org) and
# store it in a text file for later access by a computational model.

# Data will be stored in "encoded polyline" form, as a string of characters.
# This data can be converted to a series of points by the
# openrouteservice.convert.decode_polyline() function, with the string
# representing the encoded polyline as its only argument. This would be done in
# the program utilizing the stored data.
version = 'v0.1'


import openrouteservice

print(f'OpenRouteService Route Retrieval Program {version}\n')

# Request county, lake, and output files
countyPath = os.getcwd() + '\\' + input('Type the name of the COUNTY file, ' \
                                        'relative to your current path:\n')
lakePath = os.getcwd() + '\\' + input('Type the name of the LAKE file, ' \
                                      'relative to your current path:\n')
outputPath = os.getcwd() + '\\' + input('\nType the name of the new file to '\
                                        'be created for OUTPUT, relative to '\
                                        'your current path:\n')
# (Try to) Open input files
(countyFile,lakeFile) = (None,None)
try:
    with open(countyPath, 'r') as countyFile, open(lakePath, 'r') as lakeFile:
        #Internalize county and lake data, ensuring that the most up-to-date
        #records are used for each lake
except FileNotFoundError:
    print(f'\nCould not find {f} file as specified above. Please check for '\
          'typing errors and try again.\nFull error trace:')
    raise



        
# Query user's ORS API key
print('\nBe aware that all ORS API requests will be charged against your '\
      'Directions V2 quota in OpenRouteService. The total number of requests '\
      'made will be exactly equal to the number of input counties multiplied '\
      'by the number of input water bodies.\n'
key = input('Type (or paste) your API key here:\n')

# Actual data retrieval
count = 0
client = openrouteservice.Client(key=key)
with open(outputPath, 'a') as outputFile:
#    for county in counties:
#        for lake in lakes:
            # Get directions for the route and write to output file
            try:
#                routes = client.directions((start,end))
                count += 1
                encoded = routes['routes'][0]['geometry']
                #Write route and orig/dest to output file
            # Address several possible errors returned by the API
            except openrouteservice.exceptions.ApiError as e:
                print('An error occurred regarding the ORS Directions query. '\
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
                raise e
            # And the possibility of a file error
            except IOError:
                print('An error occurred while writing data to the output '\
                      'file. Full error trace:')
                raise

print(f'Complete; made a total of {count} queries')
