import json, os, logging, pillow_heif, sys, datetime
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

LOG_PATH = "./log"
LOG_CONSOLE_LEVEL = 50

logger_console = logging.StreamHandler(sys.stdout)
logger_console.setLevel(LOG_CONSOLE_LEVEL)
logger_fh = logging.FileHandler(f"{LOG_PATH}/{datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logger_fh,
        logger_console
    ]
)

LOGGER = logging.getLogger()

pillow_heif.register_heif_opener() # Register HEIF support with Pillow


def get_exif_data(image_path:str) -> dict | None:
    try:
        image = Image.open(image_path)
        
        exif_data = image._getexif()
        
        if not exif_data: 
            LOGGER.warning(f"Error reading {image_path}: No exif data found in file")
            return None
        
        # return exif data as a dict
        return {TAGS.get(tag): value for tag, value in exif_data.items() if tag in TAGS}
    
    except Exception as e:
        LOGGER.error(f"Error reading {image_path}: {e}")
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
    if not timestamp_str: return
    
    try:
        dt = datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except Exception as e:
        LOGGER.warning(f"Error formatting timestamp '{timestamp_str}': {e}")
        return None


def extract_metadata(photo_dir):
    data = []
    LOGGER.info(f"Starting metadata extraction from photos in {photo_dir}")

    for root, _, files in os.walk(photo_dir):
        for idx, file in enumerate(files):
            file_path = os.path.join(root, file)
            
            if idx % 100 == 0:
                s = f"Processing file {idx}/{len(files)} in current directory: {file_path}"
                print(s); LOGGER.info(s)
            
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')) and not file.startswith("._"):
                filename = file_path.split('/')[-1]
                
                exif = get_exif_data(file_path)
                
                if not exif:
                    data.append({"filename": filename, "error": "no exif data"})
                    continue
                    
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
PHOTO_DIR = "/Volumes/EXTERNAL2/Images/CAMERA ROLL"
OUTPUT_FILE = "./output/photo_metadata.json"

metadata = extract_metadata(PHOTO_DIR)

with open(OUTPUT_FILE, "w") as f:
    json.dump(metadata, f, indent=4)
    LOGGER.info(f"Metadata saved to {OUTPUT_FILE}")

print(f"Metadata saved to {OUTPUT_FILE}")