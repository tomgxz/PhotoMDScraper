import json
import os
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def get_exif_data(image_path:str) -> dict | None:
    try:
        image = Image.open(image_path)
        
        exif_data = image._getexif()
        if not exif_data: return None
        
        # return exif data as a dict
        return {TAGS.get(tag): value for tag, value in exif_data.items() if tag in TAGS}
    
    except Exception as e:
        print(f"Error reading {image_path}: {e}")
        return None


def convert_to_degrees(value):
    d, m, s = value
    return d + (m / 60.0) + (s / 3600.0)


def get_lat_lon(gps_info):
    if not gps_info: return None, None

    lat, lon = None, None
    if 2 in gps_info and 4 in gps_info:
        lat = convert_to_degrees(gps_info[2])
        lon = convert_to_degrees(gps_info[4])
        if gps_info[1] == "S": lat = -lat
        if gps_info[3] == "W": lon = -lon

    return lat, lon


def format_timestamp(timestamp_str):
    try:
        dt = datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except:
        return None


def extract_metadata(photo_dir):
    data = []
    for root, _, files in os.walk(photo_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')): # TODO: heic?
                image_path = os.path.join(root, file)
                filename = image_path.split('/')[-1]
                
                exif = get_exif_data(image_path)
                
                gps_info = exif.get("GPSInfo") # TODO: property doesn't exist?
                timestamp = exif.get("DateTimeOriginal") or exif.get("DateTime")
                
                lat, lon = get_lat_lon(gps_info)
                timestamp = format_timestamp(timestamp)

                entry = {"filename": filename}
                
                if timestamp: entry["timestamp"] = timestamp
                else: entry["error"] = "missing data: time"
                
                if lat: entry["latitude"] = lat
                else: entry["error"] = "missing data: gps"
                
                if lon: entry["longitude"] = lon
                else: entry["error"] = "missing data: gps"
                
                if entry == {}: entry["error"] = "missing data"
                    
                data.append(entry)

    return data

# Set path to your local photo directory
photo_directory = "./example/"

metadata = extract_metadata(photo_directory)
with open("./output/photo_metadata.json", "w") as f:
    json.dump(metadata, f, indent=4)

print("Metadata extraction complete. Saved as photo_metadata.json")