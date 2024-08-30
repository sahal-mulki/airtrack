from __future__ import annotations


import asyncio
import time
import winsdk.windows.devices.geolocation as wdg
from FlightRadar24 import FlightRadar24API
from textual.app import App, ComposeResult
from textual.widgets import Button, Footer, Header, Static, OptionList
from textual.containers import Vertical
from textual.containers import ScrollableContainer
from rich.table import Table
from geopy import distance
from textual.screen import Screen
from textual.reactive import Reactive
import math
from geopy import distance
import logging

# Configure logging to write to a file
logging.basicConfig(
    filename='airtrack.log',  # Log file name
    filemode='w',             # Overwrite the file each run ('a' to append)
    level=logging.DEBUG,      # Set the logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log format
)

# Example usage in the app
logging.debug("Debug message")
logging.info("Informational message")
logging.warning("Warning message")
logging.error("Error message")
logging.critical("Critical message")

async def get_real_time_angles(user_location, plane_location, altitude):
    while True:
        horizontal_angle = calculate_horizontal_angle(user_location, plane_location)
        vertical_angle = calculate_vertical_angle(user_location, plane_location, altitude)
        
        yield horizontal_angle, vertical_angle
        
        await asyncio.sleep(1)  # Update every 1 second


def calculate_horizontal_angle(user_location, plane_location):
    lat1, lon1 = user_location
    lat2, lon2 = plane_location
    
    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1

    logging.debug(f"Calculating horizontal angle:")
    logging.debug(f"User Location: {user_location}, Plane Location: {plane_location}")
    logging.debug(f"Delta Longitude: {delta_lon}, Delta Latitude: {delta_lat}")

    # Calculate angle in degrees
    angle = math.degrees(math.atan2(delta_lon, delta_lat))
    if angle < 0:
        angle += 360  # Normalize to 0-360 degrees

    logging.debug(f"Calculated Horizontal Angle: {angle} degrees")
    return angle


def calculate_vertical_angle(user_location, plane_location, plane_altitude):
    lat1, lon1 = user_location
    lat2, lon2 = plane_location
    
    # Calculate the horizontal distance
    horizontal_distance = distance.distance(user_location, plane_location).km
    vertical_distance = plane_altitude  # Assume altitude is in kilometers

    logging.debug(f"Calculating vertical angle:")
    logging.debug(f"Horizontal Distance: {horizontal_distance} km, Vertical Distance: {vertical_distance} km")

    # Calculate the vertical angle in degrees
    angle = math.degrees(math.atan2(vertical_distance, horizontal_distance))

    logging.debug(f"Calculated Vertical Angle: {angle} degrees")
    return angle

async def getCoords():
    locator = wdg.Geolocator()
    await locator.request_access_async()
    pos = await locator.get_geoposition_async()
    return [pos.coordinate.latitude, pos.coordinate.longitude]


async def getLoc():
    try:
        return await getCoords()
    except PermissionError:
        print("ERROR: You need to allow applications to access you location in Windows settings")

fr_api = FlightRadar24API()

#bounds = fr_api.get_bounds_by_point(location[0], location[1], 2000)


class AngleDisplay(Static):
    """Display angles in real time."""

    horizontal_angle = Reactive(0.0)
    vertical_angle = Reactive(0.0)

    def __init__(self, user_location, plane_location, altitude) -> None:
        super().__init__()
        self.user_location = user_location
        self.plane_location = plane_location
        self.altitude = altitude

    async def on_mount(self) -> None:
        """Start updating angles when the widget is mounted."""
        async for horizontal, vertical in get_real_time_angles(self.user_location, self.plane_location, self.altitude):
            self.horizontal_angle = horizontal
            self.vertical_angle = vertical

    def watch_horizontal_angle(self, value: float) -> None:
        """Update the displayed horizontal angle."""
        self.update_display()

    def watch_vertical_angle(self, value: float) -> None:
        """Update the displayed vertical angle."""
        self.update_display()

    def update_display(self) -> None:
        """Update the angle display."""
        angle_info = (
            f"Horizontal Angle: {self.horizontal_angle:.2f} degrees\n"
            f"Vertical Angle: {self.vertical_angle:.2f} degrees"
        )
        self.update(angle_info)


class GetLocation(Static):
    """Display a greeting."""

    def on_mount(self) -> None:
        self.update("Get user location for tracking nearby planes:")
        pass
    
    async def on_click(self) -> None:
        self.update(f"Getting Location.... (may take up to a minute, so relax)")
        global location
        location = await getLoc()
        self.notify("Got Location!")
        self.notify("User Location: " + str(location[0]) + ", " + str(location[1]))
        self.remove()  # Remove the widget after the delay
        await self.show_table()

    @staticmethod
    def colony(callsign: str, dest: str, dist: str) -> Table:
        table = Table(expand=True)
        table.add_column("Plane Callsign")
        table.add_column("Destination")
        table.add_column("Distance to You (km)")
        table.add_row(callsign, dest, dist)
        return table
    
    async def show_table(self) -> None:

        title = Static("Nearby Flights", id="title")
        self.notify("Finding nearby aircraft.")
        
        bounds = fr_api.get_bounds_by_point(location[0], location[1], 20000)

        global flights
        flights = fr_api.get_flights(bounds = bounds)

        self.notify("Finding nearby aircraft information.")
        
        for flight in flights:
            flight_details = fr_api.get_flight_details(flight)
            flight.set_flight_details(flight_details)
            
        global table
        table = []
        
        for flight in flights:
            table.append((flight.callsign, flight.destination_airport_name, str(distance.distance(tuple(location), [flight.latitude, flight.longitude]).km)))
        
        # Yield the OptionList after removing the button
        parent = self.parent  # Get the parent container
        parent.mount(OptionList(*[self.colony(*row) for row in table]), title)  # Mount the table in the UI
        
class Airtrack(App):
    """A Textual app to track flights."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode."), ("Ctrl+C", "quit", "Quit the program.")]

    CSS_PATH = "hello03.tcss"

    
        
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield GetLocation()
        yield Static(id="output")  # Placeholder for output
        yield Footer()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle an option being selected."""
        selected_option = str(table[event.option_index])  # Correct attribute to use

        # Update the output based on the selection
        output = self.query_one("#output", Static)
        output.update(f"Selected Option: {selected_option}")

        # Remove the OptionList widget after selection
        option_list = self.query_one(OptionList)
        title = self.query_one("#title", Static)
        if option_list:
            option_list.remove()
            title.remove()

        asyncio.sleep(2)

        selected_flight = flights[event.option_index]  # Get the selected flight data

        # Extract flight details (for simplicity, assuming `table` contains complete data)
        # Switch to the AngleScreen with the selected flight data
        self.push_screen(AngleScreen(location, (selected_flight.latitude, selected_flight.longitude), selected_flight.altitude))
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    app = Airtrack()
    app.run()
