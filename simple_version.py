import csv
import math

def read_csv(file_path):
    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # skip the headers
        data = list(reader)
    return data

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r

def closest_mangrove(lat, lon):
    data = read_csv('North_South_America_tree_measurements.csv')
    min_distance = float('inf')
    closest_row = None

    for row in data:
        try:
            date = row[4]
            lat1 = float(row[18])
            lon1 = float(row[19])
            genus = row[7]
            species = row[8]
        except ValueError:
            # Skip this row if we can't convert lat1 or lon1 to float
            continue

        distance = haversine(lat, lon, lat1, lon1)

        if distance < min_distance:
            min_distance = distance
            closest_row = {'distance (km)': min_distance, 'date': date, 'genus': genus, 'species': species}

    return closest_row

if __name__ == '__main__':
    print(closest_mangrove(21, -90))
