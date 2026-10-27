CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS parking_lot (
    parking_lot_id SERIAL PRIMARY KEY,
    municipality VARCHAR(100) NOT NULL UNIQUE,
    capacity INTEGER NOT NULL CHECK (capacity >= 0),
    location GEOGRAPHY(POINT, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS bus (
    bus_id SERIAL PRIMARY KEY,
    plate VARCHAR(10) UNIQUE NOT NULL,
    seat_capacity INTEGER NOT NULL CHECK (seat_capacity > 0),
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS driver (
    driver_id SERIAL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    license_number VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS trip (
    trip_id SERIAL PRIMARY KEY,
    bus_id INTEGER NOT NULL REFERENCES bus(bus_id),
    driver_id INTEGER NOT NULL REFERENCES driver(driver_id),
    origin VARCHAR(120) NOT NULL,
    destination VARCHAR(120) NOT NULL,
    origin_location GEOGRAPHY(POINT, 4326),
    destination_location GEOGRAPHY(POINT, 4326),
    departure_time TIMESTAMP NOT NULL,
    arrival_time TIMESTAMP NOT NULL,
    seats_booked INTEGER NOT NULL DEFAULT 0 CHECK (seats_booked >= 0),
    route_geometry GEOMETRY(LINESTRING, 4326),
    route_distance_m DOUBLE PRECISION,
    route_duration_s DOUBLE PRECISION,
    CHECK (arrival_time > departure_time)
);

-- Actualiza bases creadas con una versión anterior del proyecto.
ALTER TABLE trip ADD COLUMN IF NOT EXISTS origin_location GEOGRAPHY(POINT, 4326);
ALTER TABLE trip ADD COLUMN IF NOT EXISTS destination_location GEOGRAPHY(POINT, 4326);
ALTER TABLE trip ADD COLUMN IF NOT EXISTS seats_booked INTEGER NOT NULL DEFAULT 0;
ALTER TABLE trip ADD COLUMN IF NOT EXISTS route_geometry GEOMETRY(LINESTRING, 4326);
ALTER TABLE trip ADD COLUMN IF NOT EXISTS route_distance_m DOUBLE PRECISION;
ALTER TABLE trip ADD COLUMN IF NOT EXISTS route_duration_s DOUBLE PRECISION;

CREATE TABLE IF NOT EXISTS parking_stay (
    parking_stay_id SERIAL PRIMARY KEY,
    bus_id INTEGER NOT NULL REFERENCES bus(bus_id),
    parking_lot_id INTEGER NOT NULL REFERENCES parking_lot(parking_lot_id),
    arrival_time TIMESTAMP NOT NULL,
    scheduled_departure_time TIMESTAMP,
    actual_departure_time TIMESTAMP,
    CHECK (scheduled_departure_time IS NULL OR scheduled_departure_time >= arrival_time),
    CHECK (actual_departure_time IS NULL OR actual_departure_time >= arrival_time)
);

-- Un bus solo puede tener una estadía de parqueo abierta a la vez.
CREATE UNIQUE INDEX IF NOT EXISTS one_open_stay_per_bus
    ON parking_stay (bus_id) WHERE actual_departure_time IS NULL;
CREATE INDEX IF NOT EXISTS parking_stay_lot_open_idx
    ON parking_stay (parking_lot_id) WHERE actual_departure_time IS NULL;

CREATE TABLE IF NOT EXISTS driver_schedule (
    schedule_id SERIAL PRIMARY KEY,
    driver_id INTEGER NOT NULL REFERENCES driver(driver_id),
    trip_id INTEGER REFERENCES trip(trip_id),
    service_start TIMESTAMP NOT NULL,
    service_end TIMESTAMP NOT NULL,
    CHECK (service_end > service_start)
);

-- La tabla fuente da latitud, longitud; PostGIS recibe primero longitud y luego latitud.
INSERT INTO parking_lot (municipality, capacity, location) VALUES
('Chocontá', 2, ST_SetSRID(ST_MakePoint(-73.687044, 5.146678),4326)::geography),
('Tibiritá', 3, ST_SetSRID(ST_MakePoint(-73.504577, 5.051490),4326)::geography),
('Jerusalén', 2, ST_SetSRID(ST_MakePoint(-74.695855, 4.562677),4326)::geography),
('Ricaurte', 3, ST_SetSRID(ST_MakePoint(-74.767717, 4.282114),4326)::geography),
('Puerto Salgar', 2, ST_SetSRID(ST_MakePoint(-74.654130, 5.466157),4326)::geography),
('La Vega', 3, ST_SetSRID(ST_MakePoint(-74.338211, 4.992574),4326)::geography),
('Útica', 2, ST_SetSRID(ST_MakePoint(-74.481177, 5.185815),4326)::geography),
('Villeta', 4, ST_SetSRID(ST_MakePoint(-74.470477, 5.013166),4326)::geography),
('Guasca', 3, ST_SetSRID(ST_MakePoint(-73.874693, 4.869582),4326)::geography),
('Choachí', 2, ST_SetSRID(ST_MakePoint(-73.924819, 4.526448),4326)::geography),
('Pacho', 2, ST_SetSRID(ST_MakePoint(-74.159068, 5.140074),4326)::geography),
('Yacopí', 2, ST_SetSRID(ST_MakePoint(-74.338550, 5.463235),4326)::geography),
('Cogua', 2, ST_SetSRID(ST_MakePoint(-73.979012, 5.066298),4326)::geography),
('Cota', 3, ST_SetSRID(ST_MakePoint(-74.109258, 4.807059),4326)::geography),
('Sopó', 4, ST_SetSRID(ST_MakePoint(-73.941829, 4.913516),4326)::geography),
('Tocancipá', 4, ST_SetSRID(ST_MakePoint(-73.905176, 4.967864),4326)::geography),
('Facatativá', 4, ST_SetSRID(ST_MakePoint(-74.366498, 4.819769),4326)::geography),
('El Colegio', 2, ST_SetSRID(ST_MakePoint(-74.443732, 4.582815),4326)::geography),
('Simijaca', 2, ST_SetSRID(ST_MakePoint(-73.848055, 5.507497),4326)::geography),
('Ubaté', 3, ST_SetSRID(ST_MakePoint(-73.819161, 5.310340),4326)::geography),
('Bogotá D.C.', 8, ST_SetSRID(ST_MakePoint(-74.147794, 4.677584),4326)::geography)
ON CONFLICT (municipality) DO UPDATE SET
    capacity = EXCLUDED.capacity,
    location = EXCLUDED.location;

-- Consulta de espacios disponibles por parqueadero:
-- SELECT p.parking_lot_id, p.municipality, p.capacity - COUNT(s.*) AS available_spaces
-- FROM parking_lot p LEFT JOIN parking_stay s
--   ON s.parking_lot_id = p.parking_lot_id AND s.actual_departure_time IS NULL
-- GROUP BY p.parking_lot_id, p.municipality, p.capacity;

