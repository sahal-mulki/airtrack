import asyncio
import time
import winsdk.windows.devices.geolocation as wdg
from FlightRadar24 import FlightRadar24API
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

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

from textual.containers import ScrollableContainer
from textual.widgets import Button, Footer, Header, Static


class GetLocation(Static):
    """Display a greeting."""

    def on_mount(self) -> None:
        self.update("Get user location for tracking nearby planes:")
        pass
    
    async def on_click(self) -> None:
        self.update(f"Getting Location....")
        global location
        location = await getLoc()
        self.update("Got location!!!\n\n" + str(location[0]) + ", " + str(location[1]))
        self.update("Proceeding....")

class Airtrack(App):
    """A Textual app to track flights."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode."), ("Ctrl+C", "quit", "Quit the program.")]

    CSS_PATH = "hello03.tcss"
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield GetLocation()
        yield Footer()  
        
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    app = Airtrack()
    app.run()
