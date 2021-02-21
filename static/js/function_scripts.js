// allows to load a graph when ready
function getGraph(id, img){
    var tag = '<img class="plot" src="../static/img/'+img+'">'
    document.getElementById(id).innerHTML = tag;
}

function reCenter(map, lat_, lon){
    map.center = {lat:lat_, lng: long}
}

// Update the map. Puts charger icons in the map
function updateMap(platform, map, response, coords){
    // First delete the previous map
    // document.getElementById("main-map").innerHTML = "";

    var targetElement = document.getElementById('main-map');
    var defaultLayers = platform.createDefaultLayers();

    var routingParameters = {
      'mode': 'fastest;car;traffic:enabled',
      'waypoint0': 'geo!'+coords[0],
      'waypoint1': 'geo!'+coords[1],
      //'mode'     : 'traffic',
      'representation': 'display'
    };

    var onResult = function(result) {
        var route,routeShape,startPoint,endPoint,strip;
        if(result.response.route) {
            route = result.response.route[0];
            routeShape = route.shape;
            strip = new H.geo.Strip();
            routeShape.forEach(function(point) {
                var parts = point.split(',');
                strip.pushLatLngAlt(parts[0], parts[1]);
            });
            startPoint = route.waypoint[0].mappedPosition;
            endPoint = route.waypoint[1].mappedPosition;
            var routeLine = new H.map.Polyline(strip, {
                style: { strokeColor: 'blue', lineWidth: 5 }
            });
            var startMarker = new H.map.Marker({
                lat: startPoint.latitude,
                lng: startPoint.longitude
            });
            var endMarker = new H.map.Marker({
                lat: endPoint.latitude,
                lng: endPoint.longitude
            });
            map.addObjects([routeLine, startMarker, endMarker]);
            map.setViewBounds(routeLine.getBounds());
        }
    };
    var router = platform.getRoutingService();
    router.calculateRoute(routingParameters, onResult,
    function(error) {
        alert(error.message);
    });
    //Step 3: make the map interactive
    // MapEvents enables the event system
    // Behavior implements default interactions for pan/zoom (also on mobile touch environments)
    window.ui = H.ui.UI.createDefault(map, defaultLayers);
}

// Puts charger icons in the map
function putChargers(map){
    // First charger icons
    var icon = new H.map.Icon('/static/img/preview_30.png');
    var coords = window.first_chargers_array;
    // Put first chargers in the map
    for(var i=0; i<coords.length; i++){
        var incidentMarker = new H.map.Marker({
            lat: coords[i]["coords"][0],
            lng: coords[i]["coords"][1]
         },{icon:icon});
        map.addObjects([incidentMarker]);
    }

    // Charger icons
    icon = new H.map.Icon('/static/img/last_30.png');
    var coords = window.chargers_array;
    // Put chargers in the map
    for(var i=0; i<coords.length; i++){
        var incidentMarker = new H.map.Marker({
            lat: coords[i]["coords"][0],
            lng: coords[i]["coords"][1]
         },{icon:icon});
        map.addObjects([incidentMarker]);
    }
}