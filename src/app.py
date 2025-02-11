from flask import Flask, request, jsonify, render_template
import requests
import json
import osm2geojson  # Imported, but not used in this snippet
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
    """
    Extracts the building levels (number of floors) from a list of building elements.
    Returns a list of int values.
    """
    levels = []
    for element in elements:
        if "tags" in element:
            # The key may be "building:levels" or sometimes "levels"
            level_value = element["tags"].get("building:levels") or element["tags"].get("levels")
            if level_value:
                try:
                    levels.append(int(level_value))
                except ValueError:
                    pass  # Skip if conversion fails
    return levels

def estimate_population_density(building_count, avg_floors, radius=5000, occupants_per_floor=30):
    """
    Estimates population density (people per km²) based on:
      - building_count: number of buildings in the queried area
      - avg_floors: average number of floors per building
      - occupants_per_floor: assumed average occupants per floor (default is 30)
      - radius: radius (in meters) of the queried area (default is 5000)
    
    Calculation:
      - Estimated population = building_count * avg_floors * occupants_per_floor
      - Area (in km²) = π * (radius_in_km)^2
      - Density = Estimated population / Area
    """
    area_km2 = math.pi * ((radius / 1000) ** 2)
    estimated_population = building_count * avg_floors * occupants_per_floor
    return estimated_population / area_km2

def determine_5g_config(avg_speed, population_density, avg_floors):
    """
    Determines the 5G configuration based on:
      - avg_speed: average road speed (km/h)
      - population_density: people per km² (estimated)
      - avg_floors: average number of floors from building data
      
    Thresholds:
      - Big Capital: population_density >= 1000 per km²
      - Urban (Non‑Capital): population_density between 200 and 999 per km²
      - Rural/Mountain: population_density < 200 per km²
      
    Mobility:
      - High speed: >70 km/h
      - Moderate speed: >50 km/h
      - Low speed: <=50 km/h
      
    Building influence:
      - If avg_floors < 3, use standard parameters.
      - If avg_floors >= 3, adjust configuration (e.g., slightly lower subcarrier spacing or frequency).
    """


    if population_density >= 5000:  # Big Capital
        area_type = "Big Capital"
        if avg_floors < 3:
            frequency = "3.5 GHz"
            if avg_speed >= 70:
                subcarrier = "60 kHz"
            elif avg_speed < 50:
                subcarrier = "30 kHz"
            else:
                subcarrier = "15 kHz"
            cyclic_prefix = "Normal"
        else:
            frequency = "3.0 GHz"
            if avg_speed > 70:
                subcarrier = "30 kHz"
            elif avg_speed > 50:
                subcarrier = "15 kHz"
            else:
                subcarrier = "15 kHz"
            cyclic_prefix = "Normal"
    elif 1000 <= population_density < 5000:  # Urban (Non‑Capital)
        area_type = "Urban"
        frequency = "700 MHz"
        cyclic_prefix = "Extended"
        if avg_floors < 3:
            if avg_speed > 70:
                subcarrier = "120 kHz"
            elif avg_speed > 50:
                subcarrier = "60 kHz"
            else:
                subcarrier = "30 kHz"
        else:
            if avg_speed > 70:
                subcarrier = "60 kHz"
            elif avg_speed > 50:
                subcarrier = "30 kHz"
            else:
                subcarrier = "30 kHz"
    else:  # Rural/Mountain
        area_type = "Rural/Mountain"
        frequency = "500 MHz"
        cyclic_prefix = "Extended"
        if avg_speed > 70:
            subcarrier = "120 kHz"
        elif avg_speed > 50:
            subcarrier = "60 kHz"
        else:
            subcarrier = "30 kHz"
    
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
        # Extract building floors from each element
        floor_list = get_building_levels(building_data["elements"])
        avg_floors = sum(floor_list) / len(floor_list) if floor_list else 1  # Default to 1 floor if no data
    else:
        building_count = 0
        avg_floors = 1

    # Estimate population density based on building count and average floors.
    # Adjust the 'occupants_per_floor' parameter as needed for your use case.
    population_density = estimate_population_density(building_count, avg_floors, radius=5000, occupants_per_floor=30)
    
    config = determine_5g_config(avg_speed, population_density, avg_floors)
    
    # Log details for debugging
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
