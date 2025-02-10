from flask import Flask, request, jsonify, render_template
import requests
import json
import osm2geojson
import os

app = Flask(__name__, template_folder="../templates")  # Ensure Flask looks in the correct folder

def fetch_osm_data(query):
    overpass_url = "http://overpass-api.de/api/interpreter"
    response = requests.get(overpass_url, params={'data': query})
    return response.json() if response.status_code == 200 else None

def get_speed_limit(value):
    try:
        return int(value)
    except ValueError:
        return 50  # Default speed if conversion fails (e.g., 'walk')

def determine_5g_config(avg_speed, population_density):
    if avg_speed > 70:
        return {"subcarrier": "120 kHz", "band": "mmWave (24GHz+)", "cyclic_prefix": "Normal"}
    elif avg_speed > 50:
        return {"subcarrier": "60 kHz", "band": "C-Band (3.5GHz)", "cyclic_prefix": "Normal"}
    elif population_density > 5000:
        return {"subcarrier": "30 kHz", "band": "Sub-6GHz", "cyclic_prefix": "Extended"}
    else:
        return {"subcarrier": "15 kHz", "band": "Sub-1GHz", "cyclic_prefix": "Extended"}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/5g_config", methods=["GET"])
def get_5g_config():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    
    if not lat or not lon:
        return jsonify({"error": "Missing lat/lon"}), 400
    
    # Fetch OSM road data
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
    else:
        avg_speed = 50  # Default if no road data found
    
    # Mocked Population Density API (replace with real API)
    population_density = 3000
    
    config = determine_5g_config(avg_speed, population_density)
    
    return jsonify({"lat": lat, "lon": lon, "avg_speed": avg_speed, "config": config})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
