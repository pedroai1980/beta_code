#-*- coding: utf-8 -*-
import sys
import json
import requests
import geoplotlib
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from geopy.distance import geodesic
# custom function imports 
from api_functions import *
from eco_functions import *
from display_functions import *
# Flask imports 
from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify

app = Flask(__name__)


# USER PARAMS
# START        = [40.22, -3.6845]
# DESTIN       = [41.57, -0.7528]
# COUNTRY      = "ES"
# BATTERY      = 200

# APP PARAMS
MONTH        = 7
DAY          = 17
AI_PREDICTOR = AI_Predictor()

@app.route('/')
@app.route('/index.html')
def index():
    """ Returns the APP home page. """
    return render_template("index.html")
  

@app.route('/test_route/')
def test_route():
    return render_template("route2.html")

@app.route('/route/', methods=['POST'])
def route():
    """ Runs the App backend. Returns a JSON with the route info. """
    form = request.form 
    # get user params
    start   = form['start'].replace(" ", "").split(",")
    start   = [float(coord) for coord in start]
    destin  = form['destin'].replace(" ", "").split(",")
    destin  = [float(coord) for coord in destin]
    b_start = int(form["battery_start"])
    b_max   = int(form["battery_max"])
    country = str(form["country_code"])
    hora_salida = str(form["hora_salida"])
    # generate repsonse
    print(start, destin, b_max, hora_salida, country)
    info = routeSummaryInstructions(start, destin, b_start, b_max, hora_salida, country)

    return render_template("route.html", info=info)



@app.route('/route/chargers/', methods=['GET'])
def route_chargers():
    """ Runs the App backend. Returns a JSON with the chargers. """
    data = request.args

    start   = [float(data["start_lat"]), float(data["start_lon"])]
    destin  = [float(data["destin_lat"]), float(data["destin_lon"])]
    b_start = int(data["b_start"])
    b_max   = int(data["b_max"])
    country = str(data["country"])
    hora_salida = str(data["hora_salida"]).replace(":", "h ")+"m"
    # Call APIs:
    info = routeSummaryChargers(start, destin, b_start, b_max, hora_salida, country)
    # temporary returns
    first_chargers = [x["coords"] for x in info["first_chargers"]]
    chargers       = []
    for charger_set in info["chargers"]:
        for charger in charger_set:
            if charger["coords"] not in first_chargers:
                chargers.append(charger)

    return jsonify({"first_chargers": info["first_chargers"], "chargers": chargers})


def routeSummaryInstructions(start, 
                 destin,
                 b_start,
                 battery,
                 hora_salida,
                 country,
                 k=15,
                 transport = "car",
                 mode      = "fastest",
                 traffic   = "enabled",
                 verbose   = 0):
    """ Returns a Summary of everything. """
    info = {}
    # call here for route information
    if verbose:
        print("Getting route information")
    response = hereApiRouteCall(start, destin, 
                                transport, mode, traffic)
    # save the basic instructions:
    info["info"] = getRouteInfo(response)
    info["info"]["start"]  = start
    info["info"]["destin"] = destin
    info["info"]["b_start"] = b_start
    info["info"]["battery"] = battery
    info["info"]["country"] = country
    info["info"]["hora_salida"] = hora_salida
    info["info"]["verbose"] = verbose

    return info

def routeSummaryChargers(start, 
                 destin,
                 b_start,
                 battery,
                 hora_salida,
                 country,
                 k=15,
                 transport = "car",
                 mode      = "fastest",
                 traffic   = "enabled",
                 verbose   = 0):
    """ Returns a Summary of everything. """
    info = {}
    # call here for route information
    if verbose:
        print("Getting route information")
    response = hereApiRouteCall(start, destin, 
                                transport, mode, traffic)
    # save the basic instructions:
    info["info"] = getRouteInfo(response)
    info["info"]["start"]  = start
    info["info"]["destin"] = destin
    # Divide the route to find chargers
    if verbose:
        print("Finding chargers")
    points = getDirChanges(response)
    limits = chargingSegments(points, b_start=b_start, b_max=battery)
    centers = chargingCentroids(limits)
    # create list of chargers
    if verbose:
        print("Selecting best chargers")
    chargers_global = getAllChargers(centers, country=country)
    chargers = kChargers(chargers_global, k=k)
    first_chargers = firstChargers(start, chargers, b=b_start)
    # assign score to each charger
    first_chargers_scored = scoreChargers(AI_PREDICTOR,
                                          MONTH,
                                          DAY,
                                          enumerateTime(hora_salida),
                                          first_chargers)
    # record information
    info["chargers"]       = chargers
    info["first_chargers"] = first_chargers_scored
    # create static image 
    # if verbose:
    #     print("Creating a cool display")
    # staticDisplay(start, destin, response, info)

    return info


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
    # print(manager(START,
    #               DESTIN,
    #               BATTERY,
    #               START_TIME,
    #               COUNTRY,
    #               k=15,
    #               verbose = 1))