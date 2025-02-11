import argparse
import os
import requests
import json
import osm2geojson

def fetch_osm_data(query, filename):
    """
    Sends a query to the Overpass API and saves the returned JSON to a file.
    """
    overpass_url = "http://overpass-api.de/api/interpreter"
    print(f"Fetching data and saving to {filename}...")
    response = requests.get(overpass_url, params={'data': query})
    if response.status_code == 200:
        data = response.json()
        # Ensure output directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Data successfully saved as {filename}")
    else:
        print(f"Error fetching data: HTTP {response.status_code}")

def convert_to_geojson(input_filename, output_filename):
    """
    Reads an Overpass JSON file, converts it to GeoJSON, and saves the result.
    """
    print(f"Converting {input_filename} to GeoJSON...")
    with open(input_filename, "r", encoding="utf-8") as f:
        osm_data = json.load(f)
    geojson_data = osm2geojson.json2geojson(osm_data)
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=2)
    print(f"GeoJSON successfully saved as {output_filename}")

def build_static_query(area_name, query_type):
    """
    Build a static Overpass query using an area name.
    
    query_type: "road" or "building"
    """
    if query_type == "road":
        query = f"""
        [out:json][timeout:25];
        area["name"="{area_name}"]->.searchArea;
        (
          way["highway"](area.searchArea);
        );
        out body;
        >;
        out skel qt;
        """
    elif query_type == "building":
        query = f"""
        [out:json][timeout:25];
        area["name"="{area_name}"]->.searchArea;
        (
          way["building"](area.searchArea);
          relation["building"](area.searchArea);
        );
        out body;
        >;
        out skel qt;
        """
    else:
        raise ValueError("Invalid query_type. Use 'road' or 'building'.")
    return query

def build_dynamic_query(lat, lon, radius, query_type):
    """
    Build a dynamic Overpass query based on a center coordinate and search radius.
    
    query_type: "road" or "building"
    """
    if query_type == "road":
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"](around:{radius},{lat},{lon});
        );
        out body;
        >;
        out skel qt;
        """
    elif query_type == "building":
        query = f"""
        [out:json][timeout:25];
        (
          way["building"](around:{radius},{lat},{lon});
          relation["building"](around:{radius},{lat},{lon});
        );
        out body;
        >;
        out skel qt;
        """
    else:
        raise ValueError("Invalid query_type. Use 'road' or 'building'.")
    return query

def main():
    parser = argparse.ArgumentParser(description="Fetch OSM data from Overpass API and convert to GeoJSON.")
    parser.add_argument("--mode", choices=["static", "dynamic"], default="static", 
                        help="Query mode: 'static' uses a named area, 'dynamic' uses coordinates.")
    parser.add_argument("--area", type=str, default="Paris", 
                        help="Area name for static mode (default: Paris)")
    parser.add_argument("--lat", type=float, 
                        help="Latitude for dynamic mode")
    parser.add_argument("--lon", type=float, 
                        help="Longitude for dynamic mode")
    parser.add_argument("--radius", type=int, default=500, 
                        help="Search radius in meters for dynamic mode (default: 500)")
    args = parser.parse_args()

    if args.mode == "static":
        area_name = args.area
        # Build queries for the specified area name
        road_query = build_static_query(area_name, "road")
        building_query = build_static_query(area_name, "building")
        
        # Define file names for static queries
        road_json = "output/road_network.json"
        building_json = "output/buildings.json"
        road_geojson = "output/road_network.geojson"
        building_geojson = "output/buildings.geojson"
    else:
        # In dynamic mode, require lat and lon arguments.
        if args.lat is None or args.lon is None:
            parser.error("Dynamic mode requires --lat and --lon arguments.")
        lat = args.lat
        lon = args.lon
        radius = args.radius
        
        # Build queries using the dynamic parameters
        road_query = build_dynamic_query(lat, lon, radius, "road")
        building_query = build_dynamic_query(lat, lon, radius, "building")
        
        # Create filenames that include the coordinates for clarity
        road_json = f"output/road_network_{lat}_{lon}.json"
        building_json = f"output/buildings_{lat}_{lon}.json"
        road_geojson = f"output/road_network_{lat}_{lon}.geojson"
        building_geojson = f"output/buildings_{lat}_{lon}.geojson"

    # Fetch data and convert to GeoJSON
    fetch_osm_data(road_query, road_json)
    fetch_osm_data(building_query, building_json)
    convert_to_geojson(road_json, road_geojson)
    convert_to_geojson(building_json, building_geojson)

if __name__ == "__main__":
    main()
