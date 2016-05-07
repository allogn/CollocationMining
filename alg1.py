import numpy as np
from time import time
from collections import defaultdict
import math
from geopy.distance import VincentyDistance as vincenty
import itertools

import helpers as hlp


def hashData(hashTable, data, latCells, lngCells, latStep, lngStep, latEps, lngEps):
    start = time()
    for index, location in data.iterrows():
        lat, lng = location.location_lat, location.location_lng
        currentLatId, currentLngId = int((lat-minLat)/latStep), int((lng-minLng)/lngStep)

        upperLatId, bottomLatId = int((lat+latEps-minLat)/latStep), int((lat-latEps-minLat)/latStep)
        upperLngId, bottomLngId = int((lng+lngEps-minLng)/lngStep), int((lng-lngEps-minLng)/lngStep)
        otherLatId = upperLatId if upperLatId!=currentLatId else bottomLatId if bottomLatId!=currentLatId else currentLatId
        otherLatId = min(otherLatId, latCells-1)
        otherLngId = upperLngId if upperLngId!=currentLngId else bottomLngId if bottomLngId!=currentLngId else currentLngId
        otherLngId = min(otherLngId, lngCells-1)

        for latId in set([currentLatId, otherLatId]):
            for lngId in set([currentLngId, otherLngId]):
                try:
                    if hashTable[latId, lngId, amenitiesIndices[location.type_lowest]]:
                        hashTable[latId, lngId, amenitiesIndices[location.type_lowest]].append((lat, lng))
                        hashTable[latId, lngId, amenitiesIndices[location.type_lowest]].sort(key = lambda x : x[0])
                    else:
                        hashTable[latId, lngId, amenitiesIndices[location.type_lowest]] = [(lat, lng)]
                except Exception as e:
                    pass

    print('Super fast hasing took', time()-start, 'to execute')
    return hashTable, time()-start

def processSet(cur_atype, cur_locations, objectDict, patList, localPatterns, thresh):
    newPatList = list(patList)
    newPatList.append(cur_atype)
    subPattern = '.'.join(newPatList)
    localPatterns[subPattern] = 1
    for location in cur_locations:
        newDict = dict()
        next_locations = []
        next_atype = ''
        for atype,atype_list in objectDict.items():
            new_list = []
            for obj_loc in atype_list:
                if math.sqrt((location[0] - obj_loc[0])**2 +
                     (location[1] - obj_loc[1])**2)<thresh:
                    new_list.append(obj_loc)
            if len(new_list) > 0:
                if len(next_locations) == 0:
                    next_atype = atype
                    next_locations = new_list
                else:
                    newDict[atype] = new_list
        if len(next_locations) > 0:
            processSet(next_atype, next_locations, newDict, newPatList, localPatterns, thresh)

def mineCliquePatterns(hashTable, latCells, lngCells, latStep, lngStep, lngEps):
    patterns = defaultdict(lambda: defaultdict(lambda: 0))
    thresh = math.sqrt(latEps**2+lngEps**2)
    start = time()
    tmp = 0
    for lat in range(latCells):
        for lng in range(lngCells):
            print("Processing cell", lat+1, "/", latCells, ",", lng+1, "/", lngCells)
            currentCell = hashTable[lat, lng]
            for amenityType in amenitiesList:

                # No locations of this type
                if not currentCell[amenitiesIndices[amenityType]]:
                    continue

                cellCoords = cityCoords[lat, lng]
                # Iterate all the objects in this cell and type

                for location in filter(lambda x:
                                           x[0] >= cellCoords[0]
                                       and x[0] < cellCoords[0] + latStep
                                       and x[1] >= cellCoords[1]
                                       and x[1] < cellCoords[1] + lngStep,
                                       currentCell[amenitiesIndices[amenityType]]):
                    localPatterns = defaultdict(lambda: 0)
                    # retrieve unique patterns for current object
                    # then move unique patterns to global pattern storage (cliquePatterns)

                    # this is D array from article "multiway spatial join" by mamoulis
                    newDict = dict()
                    next_locations = []
                    next_atype = ''

                    for neighborAmenityType in filter(lambda x: currentCell[amenitiesIndices[x]]
                                                      and x != amenityType,amenitiesList):
                        cur_locations = []
                        for neighborlocationIndex in range(len(currentCell[amenitiesIndices[neighborAmenityType]])):
                            neighborlocation = currentCell[amenitiesIndices[neighborAmenityType]][neighborlocationIndex]
                            if neighborlocation[0] - location[0] < -lngEps:
                                continue
                            if location[0] - neighborlocation[0] > lngEps:
                                break
                            if vincenty(location, neighborlocation).meters <= 50:
                                cur_locations.append(neighborlocation)
                        if len(cur_locations) > 0:
                            if len(next_locations) == 0:
                                next_locations = cur_locations
                                next_atype = neighborAmenityType
                            else:
                                newDict[neighborAmenityType] = cur_locations

                    if len(next_locations) > 0:
                        processSet(next_atype, next_locations, newDict, [], localPatterns, thresh)
                    # now for current object move every unique pattern to global storage
                    for pat, val in localPatterns.items():
                        patterns[amenityType][pat] += 1
    print('Mining algorithm took', time()-start, 'to execute')
    return time()-start, patterns

def mineStarPatterns(hashTable, latCells, lngCells, latStep, lngStep, lngEps):
    patterns = defaultdict(lambda: defaultdict(lambda: 0))
    start = time()
    for lat in range(latCells):
        for lng in range(lngCells):
            currentCell = hashTable[lat, lng]
            for amenityType in amenitiesList:
                #No locations of this type
                if not currentCell[amenitiesIndices[amenityType]]:
                    continue

                cellCoords = cityCoords[lat, lng]
                #Iterate all the objects in this cell and type
                for location in filter(lambda x:
                                           x[0] >= cellCoords[0]
                                       and x[0] < cellCoords[0] + latStep
                                       and x[1] >= cellCoords[1]
                                       and x[1] < cellCoords[1] + lngStep,
                                       currentCell[amenitiesIndices[amenityType]]):
                    locationPattern = []
                    for neighborAmenityType in filter(lambda x: currentCell[amenitiesIndices[x]]
                                                      and x != amenityType,amenitiesList):

                        for neighborLocation in currentCell[amenitiesIndices[neighborAmenityType]]:
                            if neighborLocation[0] -  location[0] < -lngEps:
                                continue
                            if location[0] - neighborLocation[0] > lngEps:
                                break
                            if vincenty(location, neighborLocation).meters <= 50:
                                locationPattern.append(neighborAmenityType)

                    if len(locationPattern):
                        subPattern = locationPattern[0]
                        patterns[amenityType][subPattern]+=1
                        for pattern in locationPattern[1:]:
                            subPattern = '.'.join([subPattern, pattern])
                            patterns[amenityType][subPattern]+=1

    print('Mining algorithm took', time()-start, 'to execute')
    return time()-start, patterns


# Algorithm 1 : Start Patterns
cities, amenitiesIndices, amenitiesList = hlp.loadCities("../amenities_list.json", "../cities/", "Providence.csv")
start = time()
data = cities['Providence']
minLat, minLng, maxLat, maxLng = data.location_lat.min(), data.location_lng.min(), data.location_lat.max(), data.location_lng.max()
lowerLeft = minLat, minLng
upperRight = maxLat, maxLng

cityCoords, hashTable, lngEps, latEps = hlp.initializeContainers(minLat, minLng, maxLat, maxLng, amenitiesList)

latCells, lngCells, _ = cityCoords.shape
latStep = (maxLat - minLat)/latCells
lngStep = (maxLng - minLng)/lngCells

hashTable, hasingTime = hashData(hashTable, data, latCells, lngCells, latStep, lngStep, lngEps, latEps)
#miningTime, patterns = mineStarPatterns(hashTable, latCells, lngCells, latStep, lngStep, lngEps)
miningTime, patterns = mineCliquePatterns(hashTable, latCells, lngCells, latStep, lngStep, lngEps)
print('Total algorithm time took', time()-start, 'to execute')