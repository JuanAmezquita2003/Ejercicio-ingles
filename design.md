# Workshop 2: GIS for Intermunicipal Transportation

## 1. Purpose
The system manages buses and parking facilities in Cundinamarca, Colombia. It displays parking locations, available spaces, parked buses, departure times, and driver service schedules. Bus locations are updated from administrator-recorded parking arrivals and departures; real-time GPS tracking is outside the project scope.

## 2. Functional requirements
- Register buses, drivers, trips, parking facilities, parking arrivals/departures, and driver schedules.
- Record each trip's origin, destination, departure time, arrival time, and each parking stay's expected dwell time.
- Show parking facilities on a dynamic OpenStreetMap-based map.
- Show each facility's capacity, available spaces, parked buses, planned departures, and driver schedules.
- Reject arrivals if the facility has no available spaces.

## 3. 4+1 architectural views
### Logical view
Core entities are Bus, Driver, Trip, ParkingLot, ParkingStay, and DriverSchedule. A trip links a bus and driver to an origin, destination, and planned times. A parking stay records a bus's arrival, scheduled departure, and actual departure at one facility. The most recent open parking stay identifies a bus's current recorded location.

### Development view
The solution has a browser-based map, a Flask REST API, and PostgreSQL with PostGIS. The browser renders OpenStreetMap tiles with Leaflet. The API serves parking lot data and is the application boundary for future administrator forms. SQL constraints enforce valid capacities and time intervals.

### Process view
An administrator records a bus arrival and planned departure. The API verifies the lot has space and creates an open parking stay. The map refreshes and displays the updated occupancy. On departure, the administrator closes the stay; the map then shows the newly available space. This is event-based location reporting, not live tracking.

### Physical view
A web server hosts the Flask application and serves the map. PostgreSQL/PostGIS stores operational and geographic data. Users connect from a browser over the company network or internet. OpenStreetMap supplies the base map tiles; an internet connection is required to load them.

### Scenario (+1)
A bus arrives at Villeta. The parking administrator records its arrival and scheduled departure. The API checks capacity and stores the parking stay. The map marker reports Villeta's remaining spaces and includes the bus and its scheduled departure. When the bus leaves, the administrator records the departure and the map updates the count.

## 4. Data model and geographic data
The database schema and seed data are in `database.sql`. Geographic points use EPSG:4326. PostGIS `ST_MakePoint` expects longitude first, latitude second. The 21 workshop facilities have a combined capacity of 60 buses.

## 5. Prototype run instructions
1. Create a PostgreSQL database, then run `database.sql` against it.
2. Install dependencies with `pip install -r requirements.txt`.
3. Set `DATABASE_URL`, for example `postgresql://postgres:password@localhost:5432/transport_gis`.
4. Run `python app.py` and open `http://127.0.0.1:5000`.

The prototype map reads the seeded parking facilities from PostGIS. The schema includes the trip, bus, driver, parking stay, and driver schedule structures needed for the full system; the demonstration UI focuses on the map and lot occupancy.
