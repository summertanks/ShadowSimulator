import json
import math
import argparse
from pysolar.solar import get_altitude, get_azimuth
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pytz

config_file_path = "config.json"

# Global variables
site_name:str = ""
latitude:int = 0
longitude:int = 0
date = "2023-1-1"
pole_height:int = 0
pole_width:int = 0

def calculate_irradiance(sun_data, E_clear=1361):
    """
    Calculate irradiance (solar energy per unit area) outside and inside the shadow at different times.

    :param sun_data: List of dicts containing 'time', 'altitude' of the Sun
    :param E_clear: Clear-sky solar irradiance outside Earth's atmosphere (W/m², default: 1361 W/m²)
    :return: List of dicts with irradiance values outside and within the shadow
    """
    irradiance_data = []

    for entry in sun_data:
        time = entry["time"]
        altitude = entry["altitude"]

        if altitude > 0:  # Sun is above the horizon
            # Calculate direct irradiance (Direct irradiance projection depends on altitude)
            E_direct = E_clear * math.sin(math.radians(altitude))

            # Estimate diffuse irradiance (~15% of E_clear)
            E_diffuse = 0.15 * E_clear

            # Total irradiance outside the shadow
            E_outside_shadow = E_direct + E_diffuse

            # Irradiance within the shadow (only diffuse irradiance)
            E_inside_shadow = E_diffuse

            irradiance_data.append({
                "time": time,
                "E_outside_shadow": E_outside_shadow,
                "E_inside_shadow": E_inside_shadow
            })
        else:
            # At night or when Sun is below the horizon, no irradiance
            irradiance_data.append({
                "time": time,
                "E_outside_shadow": 0,
                "E_inside_shadow": 0
            })

    return irradiance_data

def calculate_sun_positions(latitude, longitude, date):
    """
    Calculate the position of the Sun (altitude, azimuth) from sunrise to sunset
    at 10-minute intervals for a given location and date.

    :param latitude: Latitude of the location
    :param longitude: Longitude of the location
    :param date: Date of interest (in YYYY-MM-DD format)
    :return: List of dictionaries containing time, altitude, and azimuth of the Sun
    """
    try:
        # Define the timezone as UTC
        utc = pytz.UTC

        # Convert the input date string to a datetime.date object
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()

        # Approximate sunrise and sunset (editable if you need accurate times from another source)
        sunrise_time = datetime.combine(date_obj, datetime.min.time()) + timedelta(hours=6)
        sunset_time = datetime.combine(date_obj, datetime.min.time()) + timedelta(hours=18)

        # Ensure times are timezone-aware (UTC will be used here)
        sunrise_time = utc.localize(sunrise_time)
        sunset_time = utc.localize(sunset_time)

        # Array to store Sun positions (time, altitude, azimuth)
        sun_positions = []

        # Loop through times at 10-minute intervals between sunrise and sunset
        current_time = sunrise_time
        while current_time <= sunset_time:
            # Calculate Sun's altitude and azimuth
            altitude = get_altitude(latitude, longitude, current_time)
            azimuth = get_azimuth(latitude, longitude, current_time)

            # Append the Sun's position to the array
            sun_positions.append({
                "time": current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "altitude": altitude,
                "azimuth": azimuth
            })

            # Increment time by 10 minutes
            current_time += timedelta(minutes=10)

        return sun_positions

    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def plot_shadow_pattern(shadow_coordinates):
    """
    Plot the pole and its shadow pattern on a 2D graph.

    :param shadow_coordinates: List of dictionaries containing 'time', 'x1', 'y1', 'x2', 'y2'
                               Shadow starts at (x1, y1) and ends at (x2, y2)
    """
    # Initialize the plot
    plt.figure(figsize=(80, 80))
    plt.title("Pole and Shadow Pattern", fontsize=14)
    plt.xlabel("X Coordinate (meters)", fontsize=12)
    plt.ylabel("Y Coordinate (meters)", fontsize=12)
    plt.axhline(0, color='black', linewidth=0.5, linestyle='--')
    plt.axvline(0, color='black', linewidth=0.5, linestyle='--')

    for entry in shadow_coordinates:
        time = entry['time']
        x1, y1 = entry['x1'], entry['y1']
        x2, y2 = entry['x2'], entry['y2']

        if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
            # Plot shadow line
            plt.plot(
                [x1, x2],
                [y1, y2],
                marker='o'
            )
            # Mark the shadow end point
            plt.text(
                x2, y2, f"({x2:.2f}, {y2:.2f})", fontsize=9, color='red', ha='right'
            )

    # Plot the pole origin (0, 0)
    plt.scatter(0, 0, color='blue', s=100, label="Pole (0, 0)", zorder=5)
    plt.text(0, 0, "Pole (0, 0)", fontsize=10, color="blue", ha='right', va='bottom')

    # Add legend and grid
    plt.legend(fontsize=10, loc='upper left')
    plt.grid(color='grey', linestyle='--', linewidth=0.5)
    plt.axis('equal')  # Equal scaling for x and y axes to maintain perspective

    # Show the plot
    plt.show()

def calculate_shadow(sun_data):
    """
    Calculate the size and direction of the shadow cast by a pole given azimuth, altitude, and pole dimensions.

    :param sun_data: List of dicts containing 'altitude' and 'azimuth' of Sun at the location
    :return: List of dicts containing shadow length, shadow direction (angle), and time for each input row
    """
    global pole_height, pole_width

    shadow_data = []

    for entry in sun_data:
        altitude = entry["altitude"]
        azimuth = entry["azimuth"]
        time = entry["time"]

        if altitude > 0:  # Sun is above the horizon
            # Calculate shadow length (L = h / tan(altitude))
            shadow_length = pole_height / math.tan(math.radians(altitude))

            # Shadow direction (opposite of Sun's azimuth)
            shadow_direction = (azimuth + 180) % 360

            shadow_data.append({
                "time": time,
                "shadow_length": shadow_length,
                "shadow_direction": shadow_direction
            })
        else:
            # No shadow when Sun is below the horizon
            shadow_data.append({
                "time": time,
                "shadow_length": None,
                "shadow_direction": None
            })

    return shadow_data

def initialize_configuration(config_file):
    """
    Reads configuration from a JSON file and initializes global variables.

    The JSON file should have the following structure:
    {
        "place_name": "Sample Place",
        "latitude": 12.345,
        "longitude": 67.890,
        "date": "2024-01-01"
    }

    :param config_file: Path to the JSON configuration
    :return: True if able to load configuration from file, False otherwise
    """
    global site_name, latitude, longitude, date
    global pole_height, pole_width

    try:
        with open(config_file, 'r') as file:
            config = json.load(file)

        # Extract and assign configuration values
        print("Loaded configuration:", config)
        site_name = config.get("site_name", "Khavada")
        latitude = config.get("latitude", 23.8443)
        longitude = config.get("longitude", 69.7317)
        date = config.get("date", "2025-01-01")
        pole_height = config.get("pole_height", 10)
        pole_width = config.get("pole_width", 0.5)

        print("Configuration initialized successfully.")
        return True

    except FileNotFoundError:
        print(f"Error: The file '{config_file}' was not found.")
        return False
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON configuration. Please check the file format.")
        return False
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")
        return False


def calculate_shadow_coordinates(shadow_data):
    """
    Calculate shadow coordinates (x1, y1, x2, y2) based on shadow length and direction.

    :param shadow_data: List of dictionaries with 'shadow_length' and 'shadow_direction'
    :return: List of dictionaries with shadow coordinates (x1, y1, x2, y2) and corresponding time
    """
    shadow_coordinates = []

    for entry in shadow_data:
        if entry['shadow_length'] is not None:  # Sun is above the horizon
            shadow_length = entry['shadow_length']
            shadow_direction = entry['shadow_direction']

            # Calculate x2 and y2 using trigonometry
            x2 = shadow_length * math.cos(math.radians(shadow_direction))
            y2 = shadow_length * math.sin(math.radians(shadow_direction))

            shadow_coordinates.append({
                "time": entry["time"],
                "x1": 0,
                "y1": 0,
                "x2": x2,
                "y2": y2
            })
        else:
            # No shadow case
            shadow_coordinates.append({
                "time": entry["time"],
                "x1": None,
                "y1": None,
                "x2": None,
                "y2": None
            })

    return shadow_coordinates

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print('Starting Shadow Simulator')

    parser = argparse.ArgumentParser(description="Shadow Simulator")
    parser.add_argument("--config-file", "-c",
                        type=str,
                        default="config.json",
                        help="Path to the configuration file")
    parser.add_argument("--verbose", "-v",
                        action="store_true",
                        help="Enable verbose output")

    args = parser.parse_args()
    config_file_path = args.config_file
    print(f"Using config file: {config_file_path}")

    result = initialize_configuration(config_file_path)
    if not result:
        exit(1)

    print(f"Place Name: {site_name}")
    print(f"Latitude: {latitude}")
    print(f"Longitude: {longitude}")
    print(f"Date: {date}")
    print(f"Pole Height: {pole_height}")
    print(f"Pole Width: {pole_width}")

    sun_data = calculate_sun_positions(latitude, longitude, date)

    # Print the results
    if sun_data:
        print("Sun positions from sunrise to sunset:")
        for entry in sun_data:
            print(f"Time: {entry['time']}, Altitude: {entry['altitude']:.2f}, Azimuth: {entry['azimuth']:.2f}")


    shadow_data = calculate_shadow(sun_data)
    if shadow_data:
        print("Shadow data:")
        for entry in shadow_data:
            print(f"Time: {entry['time']}, "
                  f"Shadow Length: {entry['shadow_length']:.2f}, "
                  f"Shadow Direction: {entry['shadow_direction']:.2f}")

    shadow_coordinates = calculate_shadow_coordinates(shadow_data)
    if shadow_coordinates:
        print("Shadow coordinates:")
        for entry in shadow_coordinates:
            print(f"Time: {entry['time']}, "
                  f"x1: {entry['x1']:.2f}, y1: {entry['y1']:.2f}, x2: {entry['x2']:.2f}, y2: {entry['y2']:.2f}")

    # Calculate irradiance
    irradiance = calculate_irradiance(sun_data)
    if irradiance:
        print("Irradiance:")
        for entry in irradiance:
            print(f"Time: {entry['time']}, "
                  f"E_outside_shadow: {entry['E_outside_shadow']:.2f}, "
                  f"E_inside_shadow: {entry['E_inside_shadow']:.2f}")


    plot_shadow_pattern(shadow_coordinates)
