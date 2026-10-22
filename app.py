import os
from flask import Flask, jsonify, render_template_string
import psycopg

app = Flask(__name__)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/transport_gis")

PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cundinamarca Parking GIS</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>body{font:16px Arial,sans-serif;margin:0;color:#222}header{padding:12px 18px;background:#174a63;color:white}#map{height:calc(100vh - 60px)}.popup{line-height:1.5}</style></head>
<body><header><strong>Intermunicipal Transportation — Cundinamarca</strong></header><div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map=L.map('map').setView([4.9,-74.15],8);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
fetch('/api/parking-lots').then(r=>r.json()).then(lots=>{
  const points=[];
  lots.forEach(lot=>{
    const point=[lot.latitude,lot.longitude]; points.push(point);
    L.marker(point).addTo(map).bindPopup(`<div class="popup"><b>${lot.municipality}</b><br>Capacity: ${lot.capacity}<br>Available spaces: ${lot.available_spaces}<br>Buses parked: ${lot.parked_buses}<br>Upcoming departures: ${lot.upcoming_departures}</div>`);
  });
  if(points.length) map.fitBounds(points,{padding:[25,25]});
}).catch(()=>alert('Could not load parking facilities. Check the server and database connection.'));
</script></body></html>'''

@app.get("/")
def index():
    return render_template_string(PAGE)

@app.get("/api/parking-lots")
def parking_lots():
    query = """
        SELECT p.parking_lot_id, p.municipality, p.capacity,
               ST_Y(p.location::geometry) AS latitude,
               ST_X(p.location::geometry) AS longitude,
               COUNT(s.parking_stay_id)::int AS parked_buses,
               (p.capacity - COUNT(s.parking_stay_id))::int AS available_spaces,
               COALESCE(string_agg(
                   to_char(s.scheduled_departure_time, 'YYYY-MM-DD HH24:MI'), ', '
                   ORDER BY s.scheduled_departure_time
               ) FILTER (WHERE s.scheduled_departure_time >= NOW()), 'None') AS upcoming_departures
        FROM parking_lot p
        LEFT JOIN parking_stay s ON s.parking_lot_id = p.parking_lot_id
                                AND s.actual_departure_time IS NULL
        GROUP BY p.parking_lot_id, p.municipality, p.capacity, p.location
        ORDER BY p.municipality
    """
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(query).fetchall()
    keys = ["parking_lot_id", "municipality", "capacity", "latitude", "longitude",
            "parked_buses", "available_spaces", "upcoming_departures"]
    return jsonify([dict(zip(keys, row)) for row in rows])

if __name__ == "__main__":
    app.run(debug=True)
