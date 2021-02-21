#-*- coding: utf-8 -*-
import sys
import json
import shutil
import requests
import geoplotlib
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from geopy.distance import geodesic


def hereApiRouteCall(start =[59.35, 18   ],
                     destin=[57.75, 14.13], 
                     transport="car",
                     mode="fastest",
                     traffic="enabled"):
    """ Gets the here response for a route query. """
    api_id  = "" # to be complited with your HERE id
    api_code = ""# to be complited with your HERE id

    response = requests.get("https://route.api.here.com/routing/7.2/calculateroute.json"+
                            "?app_id={0}&app_code={1}".format(api_id, api_code)+
                            "&waypoint0=geo!{0},{1}".format(start[0], start[1])+
                            "&waypoint1=geo!{0},{1}".format(destin[0], destin[1])+
                            "&mode={0};{1};traffic:{2}".format(mode, transport, traffic)).json()
    return response


def removeHTML(raw_html):
    return BeautifulSoup(raw_html, "lxml").text


def enumerateTime(time):
    """ Formats time to number. """
    time = time.replace("h", "")
    time = time.replace("m", "")
    h, m = time.split(" ")
    return int(h) + int(m)/60


def timeConvert(seconds):
    """ Converts time from seconds to hours. """
    h = seconds // 3600
    m = (seconds // 60 + 1) - h*60
    
    return str(h)+"h "+str(m)+"m"


def getInstructions(raw):
    """ Gets the instructions from a Here API request. """
    instructions = []
    for action in raw:
        clean = removeHTML(action["instruction"])
        instructions.append(clean)
        
    return instructions


def getDirChanges(raw):
    """ Gets the points at which we must change directions.
        Gonna use them to search for chargers. 
    """
    change_dirs   = raw["response"]["route"][0]["leg"][0]["maneuver"]
    coords_dirs   = [x["position"] for x in change_dirs]
    change_points = [[x["latitude"], x["longitude"]] for x in coords_dirs]
    return change_points


def getRouteInfo(response):
    """ Returns a summary of the route to follow. """
    summary = response["response"]["route"][0]["summary"]

    route_info = {"distance"       : summary["distance"]/1000,
                  "time_wo_traffic": timeConvert(summary["baseTime"]),
                  "time_w_traffic" : timeConvert(summary["trafficTime"]),
                  "instructions"   : getInstructions(response["response"]["route"][0]["leg"][0]["maneuver"])
                 }
    return route_info


def chargingSegments(points, b_start=150, b_max=150):
    """ find points near to route separated by more than k kilometers. """
    limits = [{"p": points[0], "n": 1}]
    for i, p in enumerate(points):
        # change between the start autonomy and the max autonomy
        if i==0:
            b = b_start
        else:
            b = b_max
        # add to limits if battery not enough to cover distance
        if geodesic(limits[-1]["p"], p).km > b*0.75: 
            limits.append({"p": points[i-1], "n": 1})
            # calculate number of stops required to make it
            n_stops = (geodesic(limits[-2]["p"], p).km - 0.75*geodesic(limits[-2]["p"], limits[-1]["p"]).km)//(b*0.5)
            limits.append({"p": p, "n": int(n_stops+1)})

    return limits


def chargingCentroids(limits):
    centers = []
    for i, limit in enumerate(limits):
        if i != 0:
            # number of splits
            n = limit["n"]
            # difference of latitude between splits
            lat_diff = (limits[i]["p"][0] - limits[i-1]["p"][0]) / n
            # difference of longitude between splits
            lon_diff = (limits[i]["p"][1] - limits[i-1]["p"][1]) / n
            # distance between splits
            distance = geodesic([0, 0], [lat_diff, lon_diff]).km
            for j in range(n):
                new_lat = limits[i-1]["p"][0]+ lat_diff * (j)
                new_lon = limits[i-1]["p"][1]+ lon_diff * (j)
                r = distance*1.15
                centers.append({"c": [new_lat, new_lon], "r": r})
    return centers


def getAllChargers(centers, country="SE"):
    """ Gets all the chargers for a given route. """
    chargers_global = []

    # get chargers from the API
    responses = [requests.get("https://api.openchargemap.io/v3/poi/?output=json"+
                              "&maxresults=20"+
                              "&countrycode={0}".format(country)+
                              "&latitude={0}&longitude={1}".format(center["c"][0], center["c"][1])+
                              "&distance={0}&distanceunit=KM".format(center["r"]),
                              "&maxresults=500").json() for center in centers]
    # get coords
    for response in responses:
        chargers_particular = []
        for element in response:
            charger = {}
            charger["coords"] = [element["AddressInfo"]["Latitude"], element["AddressInfo"]["Longitude"]]
            # estimate powers
            powers = []
            for connection in element["Connections"]:
                if connection["PowerKW"] is not None:
                    powers.append(connection["PowerKW"])
                elif (connection["Voltage"] and connection["Amps"]) is not None:
                    powers.append((connection["Voltage"]*connection["Amps"])**(1/3) / 1e+3)
                else:
                    if len(powers) == 0:
                        powers = [1.5]

            # get all values to only 2 decimals
            charger["power"] = np.mean(powers)
            if not np.isnan(charger["power"]):
                charger["power"] = int(charger["power"]*100)/100
            else: 
                charger["power"] = 5
            # add to list
            chargers_particular.append(charger)
        chargers_global.append(chargers_particular)
        
    return chargers_global


def kChargers(chargers_global, k=10):
    """ selects k better chargers for an area (around each centroid). """
    chargers_clean = []
    for i, segment in enumerate(chargers_global):
        segmented = []
        for charger in segment: 
            # check charger not in past segments
            add = True
            if i != 0:
                for j in range(i):
                    if charger in chargers_global[i-(j+1)]:
                        add = False
                        break
            if add: 
                segmented.append(charger)

        chargers_clean.append(segmented)

    return [sorted(x, key=lambda x: x["power"])[-k:] for x in chargers_clean] 


def checkArrival(start, charger, b=150):
    """ Checks if car is capable of arriving to charger.
        Returns time if True, otherwise False. 
    """
    response = hereApiRouteCall(start    = start, 
                                destin   = charger,
                                transport= "car",
                                mode     = "shortest")
    summary = getRouteInfo(response)

    if summary["distance"] > b:
        return False, False
    else:
        return summary["distance"], summary["time_wo_traffic"]


def firstChargers(start, chargers, b=150):
    """ Returns the first set of candidate chargers. """
    great_chargers = []
    merged = []
    for i in range(min(4, len(chargers))):
        merged = merged+chargers[i]
    for charger in merged:
        res = checkArrival(start, charger["coords"], b=b)
        great_chargers.append([res, charger])
    # delete chargers which are too far
    great_chargers = [x for x in great_chargers if x[0][0] != False]
    # reformat charger data
    first_chargers = []
    for x in great_chargers:
        first_chargers.append({"dist": x[0][0], "eta": enumerateTime(x[0][1]),
        "coords": x[1]["coords"], "power": x[1]["power"]})
                       
    return list(sorted(first_chargers, key=lambda x: -x["dist"]))


def staticDisplay(start, destin, response, info, img_name="static_route.png"):
    api_id  = ""
    api_code = ""
    # get routing points
    points = getDirChanges(response)[1:]
    points = [str(x[0])+","+str(x[1]) for x in points]
    points = ",".join(points)
    # request the HERE Map Image API
    r = requests.get("https://image.maps.api.here.com/mia/1.6/route"
                     "?app_id={0}".format(api_id)+
                     "&app_code={0}".format(api_code)+
                     "&r0="+str(start[0])+","+str(start[1])+
                     "&r1="+points+
                     "&m0="+str(start[0])+","+str(start[1])+
                     "&m1="+str(destin[0])+","+str(destin[1])+
                     "&lc0=440000ff"+
                     "&sc0=440000ff"+
                     "&lw0=6", stream=True)


    with open(img_name, 'wb') as out_file:
        shutil.copyfileobj(r.raw, out_file)

    return img_name
