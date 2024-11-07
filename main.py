from datetime import datetime
START_TIME = datetime.now()
images_start_time = None
images_end_time = None

import json, os, logging, sys, humanize
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import pillow_heif

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

feedback = {"total": 0,"processed": 0,"has_exif": 0,"has_timestamp": 0,"has_gps": 0,"failed": 0}

def get_exif_data(image_path:str,heic:bool=False) -> dict | None:
    try:
        if heic:
            image_data:np.ndarray = imageio.imread(image_path)
            image = Image.fromarray(image_data)
            exif_data = image.getexif()
        else:
            image = Image.open(image_path)
            exif_data = image._getexif()
        
        if exif_data == None: 
            LOGGER.warning(f"Error reading {image_path}: No exif data found in file")
            return None
        
        # return exif data as a dict
        return {TAGS.get(tag): value for tag, value in exif_data.items() if tag in TAGS}
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info(); fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        LOGGER.error(f"Error reading {image_path} on: {exc_type} in {fname} at line {exc_tb.tb_lineno}: {e}")
        return None


def convert_to_degrees(value: int|float) -> float:
    d, m, s = value
    return d + (m / 60.0) + (s / 3600.0)


def get_lat_lon(gps_info: dict) -> tuple[float]:
    if not gps_info: return None, None

    lat, lon = None, None
    if 2 in gps_info and 4 in gps_info:
        lat = convert_to_degrees(gps_info[2])
        lon = convert_to_degrees(gps_info[4])
        if gps_info[1] == "S": lat = -lat
        if gps_info[3] == "W": lon = -lon

    return lat, lon


def format_timestamp(timestamp_str: str) -> str:
    if not timestamp_str: return
    
    try:
        dt = datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info(); fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        LOGGER.warning(f"Error formatting timestamp '{timestamp_str}': {exc_type} in {fname} at line {exc_tb.tb_lineno}: {e}")
        return None


def count_files(directory) -> int:
    total_files = 0
    for _, _, filenames in os.walk(directory): total_files += len(filenames)
    return total_files


def extract_metadata(photo_dir: str) -> list[dict]:
    global images_start_time, images_end_time
    
    data = []
    LOGGER.info(f"Starting metadata extraction from photos in {photo_dir}")
    
    total_files = count_files(photo_dir)
    feedback["total"] = total_files
    idx = 0 # counter for console feedback every 100 files, can't use enumerate because of the nested for loops
    
    images_start_time = datetime.now()
    
    for root, _, files in os.walk(photo_dir):
        for file in files:
            file_path = os.path.join(root, file)
            idx += 1 # increment counter
            
            if idx % 100 == 0 or idx == 1:
                s = f"Processing file {idx}/{total_files}: {file_path}"
                print(s); LOGGER.info(s)
            
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')) and not file.startswith("._"):
                feedback["processed"]+=1
                filename = file_path.split('/')[-1]
                
                exif = get_exif_data(file_path,file.lower().endswith(('.heic')))
                
                if not exif:
                    data.append({"filename": filename, "error": "no exif data"})
                    continue
                
                feedback["has_exif"]+=1
                
                gps_info: dict|None = exif.get("GPSInfo") # TODO: property doesn't exist?
                timestamp = exif.get("DateTimeOriginal") or exif.get("DateTime")
                
                lat, lon = get_lat_lon(gps_info)
                timestamp = format_timestamp(timestamp)
                
                entry = {"filename": filename}
                
                if timestamp: entry["timestamp"] = timestamp; feedback["has_timestamp"]+=1
                else: entry["error"] = "missing data: time"
                
                if lat and lon:
                    entry["latitude"] = lat
                    entry["longitude"] = lon
                    feedback["has_gps"]+=1
                else: entry["error"] = "missing data: gps"; continue
                
                if entry == {}: entry["error"] = "missing data"; continue
                
                data.append(entry)

    images_end_time = datetime.now()

    return data

# Set path to your local photo directory
PHOTO_DIR = "/Volumes/EXTERNAL2/Images/CAMERA ROLL/"
OUTPUT_FILE = "./output/photo_metadata.json"

metadata = extract_metadata(PHOTO_DIR)

with open(OUTPUT_FILE, "w") as f:
    json.dump(metadata, f, indent=4)
    LOGGER.info(f"Metadata saved to {OUTPUT_FILE}")

END_TIME = datetime.now()
DURATION = END_TIME - START_TIME
image_duration = images_end_time - images_start_time

print(f"------------------------\nMetadata saved to {OUTPUT_FILE}\nCompleted in {humanize.precisedelta(DURATION, minimum_unit="microseconds", suppress=["days"])}\nAverage time per image: {humanize.precisedelta((image_duration/feedback['processed']) if feedback["processed"] > 0 else 0, minimum_unit="microseconds", suppress=["days"])}")
print(f"------------------------\nTotal files in directory: {feedback['total']}\nImages processed: {feedback['processed']}\nImages without exif data: {feedback['processed'] - feedback['has_exif']}\nImages without gps: {feedback['processed'] - feedback['has_gps']}\nFailed: {feedback['failed']}")
print(f"------------------------")

with open("./output/history.json", "r") as f:
    try: history = json.load(f)
    except json.JSONDecodeError as e: history = {}
    history[str(START_TIME)] = feedback

with open("./output/history.json", "w") as f: json.dump(history, f, indent=4)

import map