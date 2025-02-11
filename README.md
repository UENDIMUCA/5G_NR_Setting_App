# 5G NR Setting Application

# Clone the repository from GitHub
git clone <https://github.com/UENDIMUCA/5G_NR_Setting_App.git>
cd 5G_NR_SETTING_APP

## Overview
This project is a 5G network configuration tool that uses OpenStreetMap (OSM) data to estimate 5G parameters based on road and building data. The application determines configuration parameters such as subcarrier spacing, frequency, and cyclic prefix mode based on estimated population density, average road speed, and building data.

## Dependencies
- Python 3.11
- flask
- requests
- osm2geojson
- numpy (if needed by your code)
- shapely (if needed by your code)

These dependencies are listed in the `requirements.txt` file.


## Docker Instructions

### Prerequisites
- Docker must be installed on your machine. [Download Docker Desktop](https://www.docker.com/products/docker-desktop) if needed.

### Build the Docker Image
Open a terminal in the project root directory (where the Dockerfile is located) and run:
```bash

# Build the Docker image
docker build -t 5g-nr-app .

# Run the container and expose port 5000
docker run -p 5000:5000 5g-nr-app

#Access the webpage
http://localhost:5000
http://127.0.0.1:5000/