#-*- coding: utf-8 -*-
import sys
import json
import requests
import geoplotlib
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from geopy.distance import geodesic


# SetUp a COOL DISPLAY: https://developer.here.com/blog/real-time-interaction-between-maps-with-socket.io-and-javascript
# Also get inspired by Dility
def displayChargers(chargers, color="red", img_name="charging_points"):
	""" Puts the charging points in a map. Saves image to disk. """
	lats, lons, powers = [], [], []
	for center in chargers:
	    for charger in center:
	        lats.append(charger["coords"][0])
	        lons.append(charger["coords"][1])
	        powers.append(charger["power"])
	        
	thedata = pd.DataFrame({"lat": lats, "lon": lons, "powers": powers})
	geoplotlib.dot(thedata, color=color)
	geoplotlib.savefig(img_name)
	return True