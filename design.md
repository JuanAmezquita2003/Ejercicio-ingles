# Taller 2: SIG para transporte intermunicipal

## 1. Propósito
El sistema permite administrar buses y parqueaderos de una empresa de transporte intermunicipal en Cundinamarca, Colombia. Muestra la ubicación de los parqueaderos, los espacios disponibles, los buses estacionados, las salidas previstas y los horarios de servicio de los conductores. La ubicación de cada bus se actualiza cuando el administrador registra su llegada o salida; el sistema no realiza seguimiento GPS en tiempo real.

## 2. Requisitos funcionales
- Registrar buses, conductores, viajes, parqueaderos, llegadas, salidas y horarios de servicio desde la aplicación.
- Guardar el origen, el destino, la hora de salida y la hora de llegada de cada viaje, además de la hora prevista de salida del parqueadero.
- Mostrar los parqueaderos sobre un mapa dinámico basado en OpenStreetMap.
- Mostrar capacidad, espacios disponibles, placas de buses estacionados, salidas previstas y los horarios de conductores asignados a buses estacionados.
- Calcular los asientos disponibles de cada viaje a partir de la capacidad del bus y los asientos ocupados.
- Calcular y dibujar rutas viales entre ubicaciones seleccionadas.
- Rechazar llegadas cuando el parqueadero está lleno o el bus ya tiene una estadía activa.

## 3. Modelo de vistas arquitectónicas 4+1

### Vista lógica
Las entidades principales son Bus, Conductor, Viaje, Parqueadero, Estadía de parqueo y Horario de servicio. Un viaje relaciona un bus y un conductor con un origen, un destino y sus horarios. Una estadía registra la llegada del bus a un parqueadero, su hora prevista de salida y la salida real. La estadía abierta más reciente indica la ubicación registrada del bus.

### Vista de desarrollo
La solución incluye una aplicación web, una API REST en Flask y una base de datos PostgreSQL con PostGIS. El navegador muestra el mapa con Leaflet y los mosaicos de OpenStreetMap. Para cada viaje, la aplicación solicita a OSRM una ruta de conducción y guarda su geometría GeoJSON en la base de datos.

### Vista de procesos
El administrador registra un bus y un conductor, crea un viaje y registra la llegada del bus al parqueadero elegido. El sistema comprueba que haya espacio y guarda la estadía. Al registrar la salida, cierra la estadía y actualiza la disponibilidad del parqueadero. La ubicación es por eventos registrados, no por seguimiento GPS.

### Vista física
Un servidor aloja la aplicación Flask y PostgreSQL/PostGIS. Los usuarios acceden desde un navegador. OpenStreetMap proporciona el mapa base y OSRM calcula las rutas; para usar ambos servicios se necesita conexión a internet.

### Escenario (+1)
Un bus llega al parqueadero de Villeta. El administrador selecciona el bus y registra la llegada y la hora prevista de salida. El sistema verifica la capacidad, actualiza los espacios disponibles y muestra la placa en el marcador de Villeta. Al registrar un viaje entre dos puntos, el sistema obtiene y dibuja la ruta vial, muestra su distancia estimada y crea el horario de servicio del conductor asociado.

## 4. Base de datos y datos geográficos
El esquema y los datos iniciales están en `database.sql`. Las coordenadas se guardan en EPSG:4326. PostGIS recibe primero longitud y luego latitud al usar `ST_MakePoint`; en el formulario del viaje se escriben por separado como latitud y longitud. El taller proporciona 21 parqueaderos con capacidad total para 60 buses.

## 5. Ejecución del prototipo
1. Crear una base de datos PostgreSQL con PostGIS y ejecutar todo `database.sql`. Si se creó la base con una versión anterior del proyecto, volver a ejecutar el archivo actualizado para agregar los campos de ruta y asientos.
2. Instalar las dependencias con `pip install -r requirements.txt`.
3. Configurar `DATABASE_URL` con la conexión a PostgreSQL. En PowerShell: `$env:DATABASE_URL = "postgresql://postgres:TU_CLAVE@localhost:5432/transport_gis"`.
4. Ejecutar `python app.py` y abrir `http://127.0.0.1:5000`.

## 6. Uso y alcance
La interfaz está en español. Permite registrar buses y conductores, crear viajes seleccionando ciudades/parqueaderos de origen y destino de una lista, consultar la ruta vial en el mapa, y registrar las llegadas y salidas de buses en los parqueaderos. Al seleccionar el origen y destino del viaje, las coordenadas se completan automáticamente. Cada operación muestra una confirmación visible si se guardó correctamente o un aviso de error si no se pudo completar. La distancia y el tiempo estimado de una ruta se presentan en tarjetas destacadas. El formulario de viaje guarda la geometría y la distancia/tiempo estimados de OSRM. El mapa muestra buses estacionados, espacios disponibles, salidas próximas y horarios de conductores asociados a los buses estacionados. La lista de viajes y sus marcadores muestran los asientos disponibles.

La ruta y el tiempo son estimaciones basadas en la red vial de OpenStreetMap y no consideran tráfico en tiempo real. Los asientos disponibles se calculan con el número de asientos ocupados que se registra en cada viaje. Las coordenadas del viaje deben corresponder a ubicaciones de Cundinamarca.
