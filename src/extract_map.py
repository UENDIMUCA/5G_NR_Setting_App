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

if __name__ == "__main__":
    # Define Overpass API queries
    # This example uses "Paris" as the area of interest.
    
    # Query for the road network (highways, streets, etc.)
    road_query = """
    [out:json][timeout:25];
    area["name"="Paris"]->.searchArea;
    (
      way["highway"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """

    # Query for building footprints
    building_query = """
    [out:json][timeout:25];
    area["name"="Paris"]->.searchArea;
    (
      way["building"](area.searchArea);
      relation["building"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """

fetch_osm_data(road_query, "output/road_network.json")
fetch_osm_data(building_query, "output/buildings.json")

convert_to_geojson("output/road_network.json", "output/road_network.geojson")
convert_to_geojson("output/buildings.json", "output/buildings.geojson")
