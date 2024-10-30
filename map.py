import json, folium
import pandas as pd
from folium.plugins import HeatMap

# Load JSON data
with open('./output/photo_metadata.json', 'r') as f:
    data = json.load(f)

# Convert JSON to a Pandas DataFrame for easier manipulation
df = pd.DataFrame(data)

# Filter out entries with missing latitude or longitude
df = df.dropna(subset=['latitude', 'longitude'])

# Extract latitude and longitude pairs
heat_data = [[row['latitude'], row['longitude']] for _, row in df.iterrows()]

# Calculate the average location for the initial map center
avg_lat = df['latitude'].mean()
avg_lon = df['longitude'].mean()

# Create a Folium map centered on the average coordinates
m = folium.Map(location=[avg_lat, avg_lon], zoom_start=10)

# Add the heat map layer
HeatMap(heat_data, radius=8, blur=15, max_zoom=1).add_to(m)

# Save map as an HTML file
m.save('./output/map.html')
print("Map saved to /output/map.html")
