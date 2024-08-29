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




class GetLocation(Static):
    """Display a greeting."""

    def on_mount(self) -> None:
        self.update("Get user location for tracking nearby planes:")
        pass
    
    async def on_click(self) -> None:
        self.update(f"Getting Location....")
        global location
        location = await getLoc()
        self.notify("Got Location!")
        self.notify("User Location: " + str(location[0]) + ", " + str(location[1]))
        self.remove()  # Remove the widget after the delay
        await self.show_table()

    @staticmethod
    def colony(callsign: str, dest: str, speed: str) -> Table:
        table = Table(expand=True)
        table.add_column("Plane Callsign")
        table.add_column("Destination")
        table.add_column("Speed")
        table.add_row(callsign, dest, speed)
        return table
    
    async def show_table(self) -> None:


        title = Static("Nearby Flights")
        self.notify("Finding nearby aircraft.")
        
        bounds = fr_api.get_bounds_by_point(location[0], location[1], 20000)
        flights = fr_api.get_flights(bounds = bounds)

        self.notify("Finding nearby aircraft information.")
        
        for flight in flights:
            flight_details = fr_api.get_flight_details(flight)
            flight.set_flight_details(flight_details)

        table = []
        
        for flight in flights:
            table.append((flight.callsign, flight.destination_airport_name, str(flight.ground_speed)))
        
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
        selected_option = event.option.prompt  # Correct attribute to use

        # Update the output based on the selection
        output = self.query_one("#output", Static)
        output.update(f"Selected Option: {selected_option} (Index:)")

        # Remove the OptionList widget after selection
        option_list = self.query_one(OptionList)
        if option_list:
            option_list.remove()

            
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    app = Airtrack()
    app.run()
