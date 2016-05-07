import numpy as np
import pandas as pd
import json
from time import time
from collections import defaultdict
import sys, traceback
import os
import math
from geopy.distance import VincentyDistance as vincenty
import itertools

import helpers as hlp

def sortAmedities():
    start = time()
    sortedAmenities = {}
    for amenityType, locations in data.groupby('type_lowest'):
        sortedAmenities[amenityType] = list(zip(locations.location_lat.tolist(),
                                                locations.location_lng.tolist(),
                                               locations.type_lowest.tolist()))
        sortedAmenities[amenityType].sort(key = lambda x : x[0])
    amenityLocations = [(key, value) for (key, value) in sortedAmenities.items()]
    amenityLocations.sort(key = lambda x: x[0])
    ###
    amenities = [amenity for amenity, loc in amenityLocations]
    print('Sorting took', time()-start, 'to execute')
    return amenities, amenityLocations

def naiveMaterialization(data, lngEps, amenities, amenityLocations):
    neighborsByAmenity = {}
    start = time()
    for amenityTypeId, (amenityType, locations) in enumerate(amenityLocations):
        print(amenityTypeId, amenityType)
        amenityNeighbors = []
        for location in locations:
            locationNeighbors = []
            for (nextAmenityType, nextLocations) in amenityLocations[amenityTypeId+1:]:
                for neighborLocation in nextLocations:
                    if neighborLocation[0] -  location[0] < -lngEps:
                        continue
                    if location[0] - neighborLocation[0] > lngEps:
                        break
                    if vincenty(location[:2], neighborLocation[:2]).meters <= 50:
                        locationNeighbors.append(neighborLocation)
            amenityNeighbors.append((location, locationNeighbors))
        neighborsByAmenity[amenityType] = amenityNeighbors
        print(time()-start, 'to execute')
    print('Naive Materialzation took', time()-start, 'to execute')

# Cool Materialization
def minePatterns(hashTable, latCells, lngCells, latStep, lngStep, lngEps):
    neighborsByAmenity = {}
    start = time()
    for lat in range(latCells):
        for lng in range(lngCells):
            currentCell = hashTable[lat, lng]
            for amenityType in amenitiesList:
                amenityNeighbors = []
                if amenityType not in neighborsByAmenity:
                    neighborsByAmenity[amenityType] = []
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
                    locationNeighbors = []
                    for neighborAmenityType in filter(lambda x: currentCell[amenitiesIndices[x]]
                                                      and x != amenityType,
                                                      amenitiesList[amenitiesIndices[amenityType]+1:]):
                        for neighborLocation in currentCell[amenitiesIndices[neighborAmenityType]]:
                            if neighborLocation[0] -  location[0] < -lngEps:
                                continue
                            if location[0] - neighborLocation[0] > lngEps:
                                break
                            if vincenty(location[:2], neighborLocation[:2]).meters <= 50:
                                locationNeighbors.append((neighborLocation[0],
                                                         neighborLocation[1],
                                                         neighborAmenityType))
                    if len(locationNeighbors):
                        amenityNeighbors.append(((location[0],
                                                 location[1],
                                                 amenityType), locationNeighbors))
                neighborsByAmenity[amenityType].extend(amenityNeighbors)
    return time() - start, neighborsByAmenity

# some other stuff, probably star to clique transform
def starToClique(amenityLocations):
    start = time()
    amenities = [amenity for amenity, loc in amenityLocations]
    patterns = {1:[[amenity] for amenity in amenities]}
    patternsInstances = {}
    k = 2
    while len(patterns[k-1]):
        candidates = hlp.generateCandidates(patterns[k-1], amenities, k-1)
        if not len(candidates):
            break
        print('Length:', k)
        print('Candiates: ', len(candidates))
        starInstances = {}
        for colocation in candidates:
            colocationStarInstancesCandidates = neighborsByAmenity[colocation[0]]
            starInstances['.'.join(colocation)] = [instance for instance in colocationStarInstancesCandidates
                                                   if hlp.checkStar(instance, colocation)]
        cliques = {}
        patternsInstances[k] = {}
        for colocation, instances in starInstances.items():
            if len(instances):
                if k == 2:
                    patternsInstances[k][colocation] = [[instance[0]] + [location for location in instance[1] if location[2] in colocation] for instance in instances]
                else:
                    cliqueInstances = []
                    for instance in instances:
    #                     print('.'.join(colocation.split('.')))
    #                     print(len(patternsInstances[k-1]['.'.join(colocation.split('.')[1:])]))
    #                     print(len(instances))
    #                     print([location for location in instance[1] if location[2] in colocation])
    #                     print(patternsInstances[k-1]['.'.join(colocation.split('.')[1:])])

                        if [location for location in instance[1] if location[2] in colocation] in patternsInstances[k-1]['.'.join(colocation.split('.')[1:])]:
                            cliqueInstances.append([instance[0]] + [location for location in instance[1] if location[2] in colocation])
                    if len(cliqueInstances):
                        patternsInstances[k][colocation] = cliqueInstances

        patterns[k] = [clique.split('.') for clique in patternsInstances[k]]
        print('Patterns: ', len(patterns[k]))
        print('')
        k += 1
    print("cliqueToStart took",time() - start)

cities, amenitiesIndices, amenitiesList = hlp.loadCities("../amenities_list.json", "../cities/", "small.csv")
start = time()

data = cities['small']
minLat, minLng, maxLat, maxLng = data.location_lat.min(), data.location_lng.min(), data.location_lat.max(), data.location_lng.max()
lowerLeft = minLat, minLng
upperRight = maxLat, maxLng

cityCoords, hashTable, lngEps, latEps = hlp.initializeContainers(minLat, minLng, maxLat, maxLng, amenitiesList)
latCells, lngCells, _ = cityCoords.shape
latStep = (maxLat - minLat)/latCells
lngStep = (maxLng - minLng)/lngCells

amenities, amenityLocations = sortAmedities()
#naiveMaterialization(data, lngEps, amenities, amenityLocations)

materTime, neighborsByAmenity = minePatterns(hashTable, latCells, lngCells, latStep, lngStep, lngEps)
starToClique(amenityLocations)

print('Total algorithm time took', time()-start, 'to execute')