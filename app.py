import json
import os
from datetime import datetime

import psycopg
from flask import Flask, jsonify, render_template_string, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/transport_gis")

PAGE = r'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SIG de transporte de Cundinamarca</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
*{box-sizing:border-box}body{font:14px Arial,sans-serif;margin:0;color:#222}header{height:54px;padding:12px 18px;background:#174a63;color:white;font-size:18px;font-weight:bold}main{display:flex;height:calc(100vh - 54px)}aside{width:360px;overflow:auto;padding:12px;background:#f4f6f7;border-right:1px solid #ccd2d5}#map{flex:1}.card{background:white;border:1px solid #d9dfe2;border-radius:6px;padding:11px;margin-bottom:11px}.card h3{font-size:15px;margin:0 0 8px;color:#174a63}label{display:block;margin:6px 0 3px}input,select,button{font:inherit;padding:7px;width:100%;border:1px solid #bbc5ca;border-radius:4px}button{margin-top:8px;background:#17627e;color:white;border:0;cursor:pointer}button.secondary{background:#687a82}button:hover{filter:brightness(.94)}.row{display:flex;gap:7px}.row>*{flex:1;min-width:0}.small{font-size:12px;color:#57636a}.status{margin-top:6px;color:#8b2525;white-space:pre-wrap}.trip{border-top:1px solid #e5e8ea;padding:7px 0}.trip button{padding:5px;margin-top:4px}.leaflet-popup-content{line-height:1.5}.route-result{display:flex;gap:8px;margin-top:10px}.route-metric{flex:1;text-align:center;background:#e7f2f6;border-radius:6px;padding:10px 5px;color:#174a63}.route-metric strong{display:block;font-size:27px;line-height:1.1}.route-metric span{font-size:12px}.toast{position:fixed;z-index:2000;right:20px;top:68px;max-width:min(440px,calc(100vw - 40px));padding:13px 18px;border-radius:7px;color:white;font-size:15px;font-weight:bold;box-shadow:0 3px 14px #0003;opacity:0;transform:translateY(-8px);pointer-events:none;transition:opacity .2s,transform .2s}.toast.show{opacity:1;transform:translateY(0)}.toast.success{background:#217346}.toast.error{background:#a52a2a}
</style></head><body>
<header>Sistema de transporte intermunicipal — Cundinamarca</header><div id="toast" class="toast" role="status" aria-live="polite"></div><main><aside>
<section class="card"><h3>Ruta vial</h3><label>Parqueadero de origen</label><select id="route-origin"></select><label>Parqueadero de destino</label><select id="route-destination"></select><button id="show-route">Mostrar ruta por carretera</button><button class="secondary" id="clear-route">Borrar ruta</button><div id="route-status" aria-live="polite"></div></section>
<section class="card"><h3>Registrar bus</h3><form id="bus-form"><label>Placa</label><input name="plate" required maxlength="10"><label>Capacidad de asientos</label><input name="seat_capacity" type="number" min="1" required><button>Guardar bus</button></form></section>
<section class="card"><h3>Registrar conductor</h3><form id="driver-form"><label>Nombre completo</label><input name="full_name" required><label>Número de licencia</label><input name="license_number" required><button>Guardar conductor</button></form></section>
<section class="card"><h3>Registrar viaje y ruta</h3><form id="trip-form"><label>Bus</label><select name="bus_id" required></select><label>Conductor</label><select name="driver_id" required></select>
<label>Ciudad/parqueadero de origen</label><select name="origin_lot_id" id="trip-origin" required></select><div class="row"><div><label>Latitud</label><input id="origin_lat" readonly placeholder="Se completa al elegir la ciudad"></div><div><label>Longitud</label><input id="origin_lon" readonly placeholder="Se completa al elegir la ciudad"></div></div>
<label>Ciudad/parqueadero de destino</label><select name="destination_lot_id" id="trip-destination" required></select><div class="row"><div><label>Latitud</label><input id="destination_lat" readonly placeholder="Se completa al elegir la ciudad"></div><div><label>Longitud</label><input id="destination_lon" readonly placeholder="Se completa al elegir la ciudad"></div></div>
<label>Hora de salida</label><input name="departure_time" type="datetime-local" required><label>Hora de llegada</label><input name="arrival_time" type="datetime-local" required><label>Asientos ocupados</label><input name="seats_booked" type="number" min="0" value="0" required><button>Guardar viaje y dibujar ruta</button></form><div id="trip-status" class="status"></div></section>
<section class="card"><h3>Registrar llegada de bus</h3><form id="arrival-form"><label>Bus</label><select name="bus_id" required></select><label>Parqueadero</label><select name="parking_lot_id" required></select><label>Hora prevista de salida</label><input name="scheduled_departure_time" type="datetime-local"><button>Registrar llegada</button></form><div id="arrival-status" class="status"></div></section>
<section class="card"><h3>Registrar salida de bus</h3><form id="departure-form"><label>Bus estacionado</label><select name="parking_stay_id" required></select><button>Registrar salida ahora</button></form><div id="departure-status" class="status"></div></section>
<section class="card"><h3>Viajes y horarios de conductores</h3><div id="trips-list" class="small">Cargando…</div></section>
<div id="page-status" class="status"></div></aside><div id="map"></div></main>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
const map=L.map('map').setView([4.9,-74.15],8);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
let lotMap=new Map(), routeLayer=null, tripLayers=[];
const $=id=>document.getElementById(id);
async function api(url, options={}){let r;try{r=await fetch(url,{...options,headers:{'Content-Type':'application/json',...(options.headers||{})}})}catch(e){throw new Error(`No se pudo conectar con ${url}. Comprueba que Flask siga ejecutándose en esta misma dirección y recarga la página.`)}const text=await r.text();let data;try{data=JSON.parse(text)}catch(e){data={error:`El servidor respondió HTTP ${r.status} con una página no JSON. Revisa la terminal de Flask.`}}if(!r.ok)throw new Error(`${url}: ${data.error||`HTTP ${r.status}`}`);return data;}
function formData(form){return Object.fromEntries(new FormData(form).entries());}
function setStatus(id,text,isError=true){const el=$(id);el.textContent=text;el.style.color=isError?'#8b2525':'#17627e';if(id==='route-status')el.className=text?'status':'';}
let toastTimer;function showToast(message,success){const t=$('toast');t.textContent=(success?'✓ ':'✕ ')+message;t.className='toast show '+(success?'success':'error');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.className='toast',4500);}
function showRouteMetrics(km,minutes){const el=$('route-status');el.className='route-result';el.innerHTML=`<div class="route-metric"><strong>${km}</strong><span>kilómetros</span></div><div class="route-metric"><strong>${minutes}</strong><span>minutos estimados</span></div>`;}
function setSelect(select,items,valueFn,labelFn,placeholder){select.innerHTML='';if(placeholder){const o=document.createElement('option');o.value='';o.textContent=placeholder;select.appendChild(o)}items.forEach(item=>{const o=document.createElement('option');o.value=valueFn(item);o.textContent=labelFn(item);select.appendChild(o)});}
function fillCoordinates(selectId,prefix){const lot=lotMap.get($(selectId).value);$(prefix+'_lat').value=lot?lot.latitude:'';$(prefix+'_lon').value=lot?lot.longitude:'';}
async function refresh(){
 const [lots,buses,drivers,stays,trips]=await Promise.all([api('/api/parking-lots'),api('/api/buses'),api('/api/drivers'),api('/api/active-stays'),api('/api/trips')]);
 lotMap=new Map(lots.map(x=>[String(x.parking_lot_id),x]));
 setSelect($('route-origin'),lots,x=>x.parking_lot_id,x=>x.municipality);
 setSelect($('route-destination'),lots,x=>x.parking_lot_id,x=>x.municipality);
 if(lots.length>1)$('route-destination').selectedIndex=1;
 setSelect($('trip-origin'),lots,x=>x.parking_lot_id,x=>x.municipality,'Selecciona ciudad/parqueadero');
 setSelect($('trip-destination'),lots,x=>x.parking_lot_id,x=>x.municipality,'Selecciona ciudad/parqueadero');
 fillCoordinates('trip-origin','origin');fillCoordinates('trip-destination','destination');
 document.querySelectorAll('#trip-form select[name=bus_id],#arrival-form select[name=bus_id]').forEach(s=>setSelect(s,buses,x=>x.bus_id,x=>`${x.plate} (${x.available_seats} asientos libres)`,'Selecciona un bus'));
 setSelect(document.querySelector('#trip-form select[name=driver_id]'),drivers,x=>x.driver_id,x=>x.full_name,'Selecciona un conductor');
 setSelect(document.querySelector('#arrival-form select[name=parking_lot_id]'),lots,x=>x.parking_lot_id,x=>`${x.municipality} (${x.available_spaces} espacios)`,'Selecciona un parqueadero');
 setSelect(document.querySelector('#departure-form select[name=parking_stay_id]'),stays,x=>x.parking_stay_id,x=>`${x.plate} — ${x.municipality}`,'Selecciona un bus estacionado');
 const points=[];map.eachLayer(layer=>{if(layer instanceof L.Marker)map.removeLayer(layer)});
  lots.forEach(lot=>{const p=[lot.latitude,lot.longitude];points.push(p);L.marker(p).addTo(map).bindPopup(`<b>${lot.municipality}</b><br>Capacidad: ${lot.capacity}<br>Espacios disponibles: ${lot.available_spaces}<br>Buses estacionados: ${lot.parked_buses}<br>Placas: ${lot.parked_bus_plates}<br>Próximas salidas: ${lot.upcoming_departures}<br><b>Horarios de conductores de buses estacionados:</b><br>${lot.driver_schedules}`)});
 if(points.length)map.fitBounds(points,{padding:[25,25]});
 tripLayers.forEach(layer=>map.removeLayer(layer));tripLayers=[];
 trips.forEach(t=>{if(t.route_geometry){const layer=L.geoJSON(t.route_geometry,{style:{color:'#2867c7',weight:4,opacity:.75}}).addTo(map);layer.bindPopup(`<b>${t.origin} → ${t.destination}</b><br>Bus: ${t.plate}<br>Conductor: ${t.driver_name}<br>Asientos disponibles: ${t.available_seats}/${t.seat_capacity}<br>Servicio: ${t.departure_time} – ${t.arrival_time}<br>Ruta: ${(t.route_distance_m/1000).toFixed(1)} km, ${Math.round(t.route_duration_s/60)} min`);tripLayers.push(layer);}});
 $('trips-list').innerHTML=trips.length?trips.map(t=>`<div class="trip"><b>${t.origin} → ${t.destination}</b><br>${t.plate} · ${t.driver_name}<br>${t.departure_time} · ${t.available_seats}/${t.seat_capacity} asientos disponibles<button type="button" data-trip="${t.trip_id}">Ver ruta</button></div>`).join(''):'Aún no hay viajes registrados.';
 document.querySelectorAll('[data-trip]').forEach(btn=>btn.onclick=()=>{const t=trips.find(x=>String(x.trip_id)===btn.dataset.trip);if(t?.route_geometry){const layer=L.geoJSON(t.route_geometry);map.fitBounds(layer.getBounds(),{padding:[25,25]});}});
}
function getRoadRoute(lon1,lat1,lon2,lat2){const url=`https://router.project-osrm.org/route/v1/driving/${lon1},${lat1};${lon2},${lat2}?overview=full&geometries=geojson`;return fetch(url).then(r=>{if(!r.ok)throw new Error(`El servicio de rutas respondió HTTP ${r.status}`);return r.json()}).then(d=>{if(d.code!=='Ok'||!d.routes?.length)throw new Error('No se encontró una ruta transitable para esas coordenadas.');return d.routes[0]}).catch(e=>{if(e instanceof TypeError)throw new Error('No se pudo conectar con el servicio de rutas. Comprueba tu conexión a internet.');throw e})}
$('trip-origin').onchange=()=>fillCoordinates('trip-origin','origin');
$('trip-destination').onchange=()=>fillCoordinates('trip-destination','destination');
$('show-route').onclick=async()=>{const a=lotMap.get($('route-origin').value),b=lotMap.get($('route-destination').value);if(!a||!b||a.parking_lot_id===b.parking_lot_id){setStatus('route-status','Selecciona dos parqueaderos diferentes.');showToast('Selecciona dos parqueaderos diferentes.',false);return}try{setStatus('route-status','Calculando ruta…',false);const r=await getRoadRoute(a.longitude,a.latitude,b.longitude,b.latitude);if(routeLayer)map.removeLayer(routeLayer);routeLayer=L.geoJSON(r.geometry,{style:{color:'#d22f27',weight:5}}).addTo(map);map.fitBounds(routeLayer.getBounds(),{padding:[25,25]});showRouteMetrics((r.distance/1000).toFixed(1),Math.round(r.duration/60));showToast('Ruta calculada correctamente.',true)}catch(e){setStatus('route-status',e.message);showToast(e.message,false)}};
$('clear-route').onclick=()=>{if(routeLayer)map.removeLayer(routeLayer);routeLayer=null;$('route-status').innerHTML='';$('route-status').className='';showToast('Ruta borrada del mapa.',true)};
$('bus-form').onsubmit=async e=>{e.preventDefault();try{await api('/api/buses',{method:'POST',body:JSON.stringify(formData(e.target))});e.target.reset();showToast('Bus registrado correctamente.',true);refresh().catch(err=>showToast('El bus se guardó, pero no se pudo actualizar la vista: '+err.message,false))}catch(err){showToast('No se pudo registrar el bus: '+err.message,false)}};
$('driver-form').onsubmit=async e=>{e.preventDefault();try{await api('/api/drivers',{method:'POST',body:JSON.stringify(formData(e.target))});e.target.reset();showToast('Conductor registrado correctamente.',true);refresh().catch(err=>showToast('El conductor se guardó, pero no se pudo actualizar la vista: '+err.message,false))}catch(err){showToast('No se pudo registrar el conductor: '+err.message,false)}};
$('trip-form').onsubmit=async e=>{e.preventDefault();const f=formData(e.target),origin=lotMap.get(f.origin_lot_id),destination=lotMap.get(f.destination_lot_id);try{if(!origin||!destination)throw new Error('Selecciona una ciudad de origen y otra de destino.');if(origin.parking_lot_id===destination.parking_lot_id)throw new Error('El origen y el destino deben ser diferentes.');setStatus('trip-status','Calculando ruta vial…',false);const route=await getRoadRoute(origin.longitude,origin.latitude,destination.longitude,destination.latitude);const payload={...f,origin:origin.municipality,destination:destination.municipality,origin_lat:origin.latitude,origin_lon:origin.longitude,destination_lat:destination.latitude,destination_lon:destination.longitude,route_geometry:route.geometry,route_distance_m:route.distance,route_duration_s:route.duration};delete payload.origin_lot_id;delete payload.destination_lot_id;await api('/api/trips',{method:'POST',body:JSON.stringify(payload)});e.target.reset();fillCoordinates('trip-origin','origin');fillCoordinates('trip-destination','destination');setStatus('trip-status','');showToast('Viaje registrado correctamente; su ruta aparece en el mapa.',true);refresh().catch(err=>showToast('El viaje se guardó, pero no se pudo actualizar la vista: '+err.message,false))}catch(err){setStatus('trip-status',err.message);showToast('No se pudo registrar el viaje: '+err.message,false)}};
$('arrival-form').onsubmit=async e=>{e.preventDefault();try{await api('/api/arrivals',{method:'POST',body:JSON.stringify(formData(e.target))});e.target.reset();showToast('Llegada del bus registrada correctamente.',true);refresh().catch(err=>showToast('La llegada se guardó, pero no se pudo actualizar la vista: '+err.message,false))}catch(err){showToast('No se pudo registrar la llegada: '+err.message,false)}};
$('departure-form').onsubmit=async e=>{e.preventDefault();try{await api('/api/departures',{method:'POST',body:JSON.stringify(formData(e.target))});showToast('Salida del bus registrada correctamente.',true);refresh().catch(err=>showToast('La salida se guardó, pero no se pudo actualizar la vista: '+err.message,false))}catch(err){showToast('No se pudo registrar la salida: '+err.message,false)}};
refresh().catch(e=>setStatus('page-status','No se pudieron cargar los datos de la aplicación: '+e.message));
</script></body></html>'''


def error(message, status=400):
    return jsonify({"error": str(message)}), status


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    if request.path.startswith("/api/"):
        app.logger.exception("Error en endpoint %s", request.path)
        message = exc.description if isinstance(exc, HTTPException) else str(exc)
        return jsonify({"error": message}), getattr(exc, "code", 500)
    if isinstance(exc, HTTPException):
        return exc
    app.logger.exception("Error inesperado en la aplicación")
    return "Error interno del servidor", 500


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
               COALESCE(string_agg(b.plate, ', ' ORDER BY b.plate)
                   FILTER (WHERE s.parking_stay_id IS NOT NULL), 'None') AS parked_bus_plates,
               COALESCE(string_agg(to_char(s.scheduled_departure_time, 'YYYY-MM-DD HH24:MI'), ', '
                   ORDER BY s.scheduled_departure_time)
                   FILTER (WHERE s.scheduled_departure_time >= NOW()), 'None') AS upcoming_departures,
               COALESCE((SELECT string_agg(d.full_name || ' (' ||
                   to_char(ds.service_start, 'YYYY-MM-DD HH24:MI') || '–' ||
                   to_char(ds.service_end, 'HH24:MI') || ')', '<br>' ORDER BY ds.service_start)
                 FROM parking_stay ps JOIN trip t ON t.bus_id = ps.bus_id
                 JOIN driver_schedule ds ON ds.trip_id = t.trip_id
                 JOIN driver d ON d.driver_id = ds.driver_id
                 WHERE ps.parking_lot_id = p.parking_lot_id
                   AND ps.actual_departure_time IS NULL AND ds.service_end >= NOW()),
                   'No scheduled driver services') AS driver_schedules
        FROM parking_lot p
        LEFT JOIN parking_stay s ON s.parking_lot_id = p.parking_lot_id
                                AND s.actual_departure_time IS NULL
        LEFT JOIN bus b ON b.bus_id = s.bus_id
        GROUP BY p.parking_lot_id, p.municipality, p.capacity, p.location
        ORDER BY p.municipality
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            rows = conn.execute(query).fetchall()
    except Exception as exc:
        return error(exc, 500)
    keys = ["parking_lot_id", "municipality", "capacity", "latitude", "longitude",
            "parked_buses", "available_spaces", "parked_bus_plates", "upcoming_departures", "driver_schedules"]
    return jsonify([dict(zip(keys, row)) for row in rows])


@app.get("/api/buses")
def buses():
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute("""
            SELECT b.bus_id, b.plate, b.seat_capacity,
                   b.seat_capacity - COALESCE((SELECT SUM(t.seats_booked) FROM trip t
                     WHERE t.bus_id=b.bus_id AND t.departure_time <= NOW() AND t.arrival_time >= NOW()),0)::int AS available_seats
            FROM bus b WHERE b.active ORDER BY b.plate
        """).fetchall()
    return jsonify([dict(zip(["bus_id", "plate", "seat_capacity", "available_seats"], row)) for row in rows])


@app.post("/api/buses")
def create_bus():
    data = request.get_json(silent=True) or {}
    try:
        plate = data["plate"].strip().upper()
        capacity = int(data["seat_capacity"])
        if not plate or capacity <= 0:
            raise ValueError("La placa es obligatoria y la capacidad debe ser mayor que cero.")
        with psycopg.connect(DATABASE_URL) as conn:
            row = conn.execute("INSERT INTO bus (plate, seat_capacity) VALUES (%s,%s) RETURNING bus_id", (plate, capacity)).fetchone()
        return jsonify({"bus_id": row[0]}), 201
    except (KeyError, ValueError) as exc:
        return error(exc)
    except psycopg.errors.UniqueViolation:
        return error("Ya existe un bus con esa placa.", 409)
    except Exception as exc:
        return error(exc, 500)


@app.get("/api/drivers")
def drivers():
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute("SELECT driver_id, full_name, license_number FROM driver ORDER BY full_name").fetchall()
    return jsonify([dict(zip(["driver_id", "full_name", "license_number"], row)) for row in rows])


@app.post("/api/drivers")
def create_driver():
    data = request.get_json(silent=True) or {}
    try:
        name, license_number = data["full_name"].strip(), data["license_number"].strip()
        if not name or not license_number:
            raise ValueError("El nombre y el número de licencia son obligatorios.")
        with psycopg.connect(DATABASE_URL) as conn:
            row = conn.execute("INSERT INTO driver (full_name, license_number) VALUES (%s,%s) RETURNING driver_id", (name, license_number)).fetchone()
        return jsonify({"driver_id": row[0]}), 201
    except (KeyError, ValueError) as exc:
        return error(exc)
    except psycopg.errors.UniqueViolation:
        return error("Ya existe un conductor con ese número de licencia.", 409)
    except Exception as exc:
        return error(exc, 500)


@app.get("/api/active-stays")
def active_stays():
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute("""
            SELECT s.parking_stay_id, b.plate, p.municipality
            FROM parking_stay s JOIN bus b USING(bus_id) JOIN parking_lot p USING(parking_lot_id)
            WHERE s.actual_departure_time IS NULL ORDER BY s.arrival_time
        """).fetchall()
    return jsonify([dict(zip(["parking_stay_id", "plate", "municipality"], row)) for row in rows])


@app.post("/api/arrivals")
def create_arrival():
    data = request.get_json(silent=True) or {}
    try:
        bus_id, lot_id = int(data["bus_id"]), int(data["parking_lot_id"])
        scheduled_value = data.get("scheduled_departure_time") or None
        scheduled = datetime.fromisoformat(scheduled_value) if scheduled_value else None
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.transaction():
                database_now = conn.execute("SELECT NOW()::timestamp").fetchone()[0]
                if scheduled and scheduled <= database_now:
                    raise ValueError("La hora prevista de salida debe ser posterior a la hora actual.")
                lot = conn.execute("SELECT capacity FROM parking_lot WHERE parking_lot_id=%s FOR UPDATE", (lot_id,)).fetchone()
                if not lot:
                    raise ValueError("No se encontró el parqueadero.")
                if not conn.execute("SELECT 1 FROM bus WHERE bus_id=%s AND active", (bus_id,)).fetchone():
                    raise ValueError("No se encontró un bus activo con ese identificador.")
                count = conn.execute("SELECT COUNT(*) FROM parking_stay WHERE parking_lot_id=%s AND actual_departure_time IS NULL", (lot_id,)).fetchone()[0]
                if count >= lot[0]:
                    raise ValueError("El parqueadero está lleno.")
                conn.execute("INSERT INTO parking_stay (bus_id, parking_lot_id, arrival_time, scheduled_departure_time) VALUES (%s,%s,NOW(),%s)", (bus_id, lot_id, scheduled))
        return jsonify({"message": "Llegada registrada."}), 201
    except (KeyError, TypeError, ValueError) as exc:
        return error(exc)
    except psycopg.errors.UniqueViolation:
        return error("Este bus ya tiene una llegada abierta en un parqueadero.", 409)
    except Exception as exc:
        return error(exc, 500)


@app.post("/api/departures")
def close_arrival():
    data = request.get_json(silent=True) or {}
    try:
        stay_id = int(data["parking_stay_id"])
        with psycopg.connect(DATABASE_URL) as conn:
            row = conn.execute("UPDATE parking_stay SET actual_departure_time=NOW() WHERE parking_stay_id=%s AND actual_departure_time IS NULL RETURNING parking_stay_id", (stay_id,)).fetchone()
        if not row:
            raise ValueError("No se encontró una llegada activa para ese bus.")
        return jsonify({"message": "Salida registrada."})
    except (KeyError, TypeError, ValueError) as exc:
        return error(exc)
    except Exception as exc:
        return error(exc, 500)


@app.post("/api/trips")
def create_trip():
    data = request.get_json(silent=True) or {}
    try:
        bus_id, driver_id = int(data["bus_id"]), int(data["driver_id"])
        seats_booked = int(data.get("seats_booked", 0))
        origin, destination = data["origin"].strip(), data["destination"].strip()
        departure = datetime.fromisoformat(data["departure_time"])
        arrival = datetime.fromisoformat(data["arrival_time"])
        if arrival <= departure:
            raise ValueError("La hora de llegada debe ser posterior a la hora de salida.")
        if not origin or not destination:
            raise ValueError("Los nombres del origen y del destino son obligatorios.")
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.transaction():
                bus = conn.execute("SELECT seat_capacity FROM bus WHERE bus_id=%s AND active FOR UPDATE", (bus_id,)).fetchone()
                if not bus:
                    raise ValueError("No se encontró un bus activo con ese identificador.")
                if not conn.execute("SELECT 1 FROM driver WHERE driver_id=%s", (driver_id,)).fetchone():
                    raise ValueError("No se encontró el conductor.")
                if seats_booked < 0 or seats_booked > bus[0]:
                    raise ValueError(f"Los asientos ocupados deben estar entre 0 y la capacidad del bus ({bus[0]}).")
                route_geometry = json.dumps(data["route_geometry"])
                dist, duration = float(data["route_distance_m"]), float(data["route_duration_s"])
                row = conn.execute("""
                    INSERT INTO trip (bus_id, driver_id, origin, destination, origin_location, destination_location,
                                      departure_time, arrival_time, seats_booked, route_geometry, route_distance_m, route_duration_s)
                    VALUES (%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography,
                            ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography,%s,%s,%s,
                            ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),%s,%s)
                    RETURNING trip_id
                """, (bus_id, driver_id, origin, destination,
                      float(data["origin_lon"]), float(data["origin_lat"]),
                      float(data["destination_lon"]), float(data["destination_lat"]),
                      departure, arrival, seats_booked, route_geometry, dist, duration)).fetchone()
                conn.execute("INSERT INTO driver_schedule (driver_id, trip_id, service_start, service_end) VALUES (%s,%s,%s,%s)", (driver_id, row[0], departure, arrival))
        return jsonify({"trip_id": row[0]}), 201
    except (KeyError, TypeError, ValueError) as exc:
        return error(exc)
    except Exception as exc:
        return error(exc, 500)


@app.get("/api/trips")
def trips():
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute("""
            SELECT t.trip_id, t.origin, t.destination, b.plate, d.full_name,
                   b.seat_capacity, t.seats_booked, b.seat_capacity-t.seats_booked AS available_seats,
                   t.departure_time, t.arrival_time, t.route_distance_m, t.route_duration_s,
                   ST_AsGeoJSON(t.route_geometry)
            FROM trip t JOIN bus b USING(bus_id) JOIN driver d USING(driver_id)
            ORDER BY t.departure_time DESC
        """).fetchall()
    keys = ["trip_id", "origin", "destination", "plate", "driver_name", "seat_capacity", "seats_booked",
            "available_seats", "departure_time", "arrival_time", "route_distance_m", "route_duration_s", "route_geometry"]
    result = []
    for row in rows:
        item = dict(zip(keys, row))
        if item["route_geometry"]:
            item["route_geometry"] = json.loads(item["route_geometry"])
        result.append(item)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
