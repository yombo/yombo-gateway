/*
 * Google Maps: Latitude-Longitude Finder Tool
 * http://salman-w.blogspot.com/2009/03/latitude-longitude-finder-tool.html
 */
function loadmap() {
	// initialize map
	var map = new google.maps.Map(document.getElementById("gmap"), {
		center: new google.maps.LatLng(($("#location_latitude").val().length) ? $("#location_latitude").val() : 37.757720, ($("#location_longitude").val().length) ? $("#location_longitude").val() : -122.437600),
		zoom: 10,
    streetViewControl: false,
		mapTypeId: google.maps.MapTypeId.ROADMAP
	});
	// initialize marker
	var marker = new google.maps.Marker({
		position: map.getCenter(),
		draggable: true,
		map: map
	});
	// intercept map and marker movements
	google.maps.event.addListener(map, "idle", function() {
		marker.setPosition(map.getCenter());
		$('#location_latitude').val(map.getCenter().lat().toFixed(3));
		$('#location_longitude').val(map.getCenter().lng().toFixed(3));

		var elevator = new google.maps.ElevationService();
		// console.log(map.getCenter().lat());
		// console.log(map.getCenter().lng());
		// console.log(map.getCenter().lat().toFixed(6));
		// console.log(map.getCenter().lng().toFixed(6));

    var locations = [];
		locations.push(new google.maps.LatLng(map.getCenter().lat() , map.getCenter().lng()));
    var positionalRequest = {
      'locations': locations
    }

		console.log(positionalRequest);
		var text;

		elevator.getElevationForLocations(positionalRequest, function (results, status) {
		  console.log(results);
		  console.log(status);
			if (status == google.maps.ElevationStatus.OK) {

				// Retrieve the first result
				if (results[0]) {
//                            text =
					$('#location_elevation').val(Math.round(results[0].elevation));
				} else {
					alert('No results found');
				}
			}
			else {
				// alert('Elevation service failed due to: ' + status);
			}
		});
	});
	google.maps.event.addListener(marker, "dragend", function(mapEvent) {
		map.panTo(mapEvent.latLng);
	});
	var isOperationInProgress = 'No';
	// initialize geocoder
	var geocoder = new google.maps.Geocoder();

	google.maps.event.addDomListener(document.getElementById("search_btn"), "click", function(event) {
		if (!event.alreadyCalled_) {

			geocoder.geocode({ address: document.getElementById("search_txt").value }, function(results, status) {
				if (status == google.maps.GeocoderStatus.OK) {
					var result = results[0];
					document.getElementById("search_txt").value = result.formatted_address;
					if (result.geometry.viewport) {
						map.fitBounds(result.geometry.viewport);
					} else {
						map.setCenter(result.geometry.location);
					}
				} else if (status == google.maps.GeocoderStatus.ZERO_RESULTS) {
					alert("Google could not find that location.");
				} else {
					alert("Sorry, geocoder API failed with an error: " + status);
				}
			});
			event.alreadyCalled_ = true;
		}

	});
	google.maps.event.addDomListener(document.getElementById("search_txt"), "keydown", function(domEvent) {
		if (domEvent.which === 13 || domEvent.keyCode === 13) {
			google.maps.event.trigger(document.getElementById("search_btn"), "click");
		}
	});

}
