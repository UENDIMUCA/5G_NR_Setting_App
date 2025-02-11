from flask import Flask, request, jsonify, render_template
import requests
import json
import osm2geojson  
import os
import math

app = Flask(__name__, template_folder="../templates")

def fetch_osm_data(query):
    """Fetches data from the Overpass API using the provided query."""
    overpass_url = "http://overpass-api.de/api/interpreter"
    response = requests.get(overpass_url, params={'data': query})
    return response.json() if response.status_code == 200 else None

def get_speed_limit(value):
    """Converts a speed limit value to an integer; returns 50 if conversion fails."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 50  # Default speed if conversion fails

def get_building_levels(elements):
    """Extracts the building levels (number of floors) from a list of building elements."""
    levels = []
    for element in elements:
        if "tags" in element:
            level_value = element["tags"].get("building:levels") or element["tags"].get("levels")
            if level_value:
                try:
                    levels.append(int(level_value))
                except ValueError:
                    pass  # Skip if conversion fails
    return levels

def estimate_population_density(building_count, avg_floors, radius=5000, occupants_per_floor=30):
    """Estimates population density (people per km²) based on building and population data."""
    area_km2 = math.pi * ((radius / 1000) ** 2)
    estimated_population = building_count * avg_floors * occupants_per_floor
    return estimated_population / area_km2 if area_km2 > 0 else 0

def determine_5g_config(avg_speed, population_density, avg_floors, building_count):
    """Determines the 5G configuration based on speed, density, and building data, using only 24 GHz, 3.5 GHz, and 700 MHz."""

    # Classify area based on both population and building density
    if population_density >= 50000:
        area_type = "Big Capital"
    elif 10000 <= population_density < 50000:
        area_type = "Urban"
    else:
        area_type = "Rural/Mountain"

    # Assign frequency based on area type and building count
    if area_type == "Big Capital":
        frequency = "24 GHz" if building_count < 10000 else "3.5 GHz"  # High-band only if buildings are low in number
    elif area_type == "Urban":
        # In urban areas, choose frequency based on building count and average building floors.
        if 1000 < building_count <= 10000:
            if avg_floors > 5:
                frequency = "3.5 GHz"  # Dense urban core with high-rise buildings
            else:
                frequency = "700 MHz"  # Dense urban core but with lower-rise buildings
        elif building_count > 500:
            # check the average floors to adjust the frequency.
            if avg_floors > 5:
                frequency = "3.5 GHz"
            else:
                frequency = "700 MHz"
        else:
            frequency = "24 GHz"   # Less dense urban areas
    elif area_type == "Rural/Mountain":
        # In rural areas, decide based on the presence of clustered buildings.
        if building_count > 50:
            # Adjust frequency based on average speed,
            # which might indicate vehicular density or road conditions.
            if avg_speed < 50:
                frequency = "3.5 GHz"  # When speeds are lower, a higher frequency might be acceptable
            else:
                frequency = "700 MHz"  # For higher speeds, extended coverage with 700 MHz is preferred
        else:
            frequency = "700 MHz"  # Very sparse rural regions for extended coverage

    # Cyclic prefix assignment
    cyclic_prefix = "Normal" if area_type in ["Big Capital", "Urban"] else "Extended"

    # Adjust subcarrier spacing based on area type
    if avg_speed <= 45:
        subcarrier = "15 kHz"
    elif 45 < avg_speed > 70:
        subcarrier = "30 kHz"
    elif avg_speed > 70:
        subcarrier = "120 kHz"
    else:
        subcarrier = "30 kHz"  # Default value 

    return {
        "subcarrier": subcarrier,
        "frequency": frequency,
        "cyclic_prefix": cyclic_prefix,
        "area_type": area_type
    }






@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/5g_config", methods=["GET"])
def get_5g_config():
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if not lat or not lon:
        return jsonify({"error": "Missing lat/lon"}), 400

    # Query road data within a 5km radius
    road_query = f"""
    [out:json];
    way(around:5000,{lat},{lon})["highway"];
    out body;
    """
    road_data = fetch_osm_data(road_query)

    if road_data and "elements" in road_data:
        speed_values = [
            get_speed_limit(way["tags"].get("maxspeed", "50"))
            for way in road_data["elements"]
            if "tags" in way and "maxspeed" in way["tags"]
        ]
        avg_speed = sum(speed_values) / len(speed_values) if speed_values else 50
        road_count = len(road_data["elements"])
    else:
        avg_speed = 50
        road_count = 0

    # Query building data within a 5km radius
    building_query = f"""
    [out:json];
    way(around:5000,{lat},{lon})["building"];
    out body;
    """
    building_data = fetch_osm_data(building_query)

    if building_data and "elements" in building_data:
        building_count = len(building_data["elements"])
        floor_list = get_building_levels(building_data["elements"])
        avg_floors = sum(floor_list) / len(floor_list) if floor_list else 1  # Default to 1 floor if no data
    else:
        building_count = 0
        avg_floors = 1

    # Estimate population density
    population_density = estimate_population_density(building_count, avg_floors, radius=5000, occupants_per_floor=30)

    # Corrected function call by passing `building_count`
    config = determine_5g_config(avg_speed, population_density, avg_floors, building_count)

    # Debugging logs
    print(f"lat: {lat}, lon: {lon}, avg_speed: {avg_speed}, road_count: {road_count}, building_count: {building_count}, avg_floors: {avg_floors}")
    print("Estimated Population Density:", population_density)
    print("Determined configuration:", config)

    return jsonify({
        "lat": lat,
        "lon": lon,
        "avg_speed": avg_speed,
        "road_count": road_count,
        "building_count": building_count,
        "avg_floors": avg_floors,
        "population_density": population_density,
        "config": config,
        "radius": 5000
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
