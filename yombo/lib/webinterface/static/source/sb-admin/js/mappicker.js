		/*
		 * Google Maps: Latitude-Longitude Finder Tool
		 * http://salman-w.blogspot.com/2009/03/latitude-longitude-finder-tool.html
		 */
		function loadmap() {
			// initialize map
			var map = new google.maps.Map(document.getElementById("gmap"), {
				center: new google.maps.LatLng(($("#location-latitude").val().length) ? $("#location-latitude").val() : 37.757720, ($("#location-longitude").val().length) ? $("#location-longitude").val() : -122.437600),
				zoom: 9,
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
				$('#location-latitude').val(map.getCenter().lat().toFixed(3));
				$('#location-longitude').val(map.getCenter().lng().toFixed(3));

                var elevator = new google.maps.ElevationService();
                var denali = new google.maps.LatLng(map.getCenter().lat().toFixed(6) , map.getCenter().lng().toFixed(6));
                var positionalRequest = {'locations':[denali]};

                var text;

                elevator.getElevationForLocations(positionalRequest, function (results, status) {
                    if (status == google.maps.ElevationStatus.OK) {

                        // Retrieve the first result
                        if (results[0]) {
//                            text =
            				$('#location-elevation').val(Math.round(results[0].elevation));
                        } else {
                            alert('No results found');
                        }
                    }
                    else {
                        alert('Elevation service failed due to: ' + status);
                    }
                });


			});
			google.maps.event.addListener(marker, "dragend", function(mapEvent) {
				map.panTo(mapEvent.latLng);
			});
			var isOperationInProgress = 'No';
			// initialize geocoder
			var geocoder = new google.maps.Geocoder();


			google.maps.event.addDomListener(document.getElementById("search-btn"), "click", function(event) {
                if (!event.alreadyCalled_) {
                    geocoder.geocode({ address: document.getElementById("search-txt").value }, function(results, status) {
                        if (status == google.maps.GeocoderStatus.OK) {
                            var result = results[0];
                            document.getElementById("search-txt").value = result.formatted_address;
                            if (result.geometry.viewport) {
                                map.fitBounds(result.geometry.viewport);
                            } else {
                                map.setCenter(result.geometry.location);
                            }
                        } else if (status == google.maps.GeocoderStatus.ZERO_RESULTS) {
                            alert("Google could not find that location.");
                        } else {
                            alert("Sorry, geocoder API failed with an error.");
                        }
                    });
                    event.alreadyCalled_ = true;
                }

            });
			google.maps.event.addDomListener(document.getElementById("search-txt"), "keydown", function(domEvent) {
				if (domEvent.which === 13 || domEvent.keyCode === 13) {
					google.maps.event.trigger(document.getElementById("search-btn"), "click");
				}
			});
			// initialize geolocation
			if (navigator.geolocation) {
				google.maps.event.addDomListener(document.getElementById("detect-btn"), "click", function() {
					navigator.geolocation.getCurrentPosition(function(position) {
						map.setCenter(new google.maps.LatLng(position.coords.latitude, position.coords.longitude));
					}, function() {
						alert("Sorry, geolocation API failed to detect your location.");
					});
				});
				document.getElementById("detect-btn").disabled = false;
			}
		}
