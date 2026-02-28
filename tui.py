from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, Button, DataTable
from textual.binding import Binding
from textual import work
from textual.events import Key

import main


class SearchPanel(Static):
    """Search input panel."""

    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="Enter callsign, name, or city and click Search",
            id="search_input",
        )
        yield Horizontal(
            Button("Callsign", id="btn_call", variant="primary"),
            Button("First Name", id="btn_fnamn"),
            Button("Last Name", id="btn_enamn"),
            Button("City", id="btn_ort"),
            Button("Search", id="btn_search", variant="success"),
            id="search_buttons",
        )


class ResultPanel(Static):
    """Results display panel."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="results_table")


class CallbookApp(App):
    """SSA Callbook TUI Application."""

    CSS = """
    Screen {
        background: $surface;
    }
    #search_input {
        margin: 1 1 1 1;
        height: 3;
    }
    #search_buttons {
        margin: 1 1 1 1;
        height: auto;
    }
    #search_buttons > Button {
        margin-right: 1;
    }
    #results_table {
        height: 100%;
        margin: 1 1 1 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("c", "search_call", "Callsign", show=True),
        Binding("f", "search_fnamn", "First Name", show=True),
        Binding("e", "search_enamn", "Last Name", show=True),
        Binding("o", "search_ort", "City", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("d", "distance", "Distance", show=True),
        Binding("enter", "do_search", "Search", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.current_search_type = "call"
        self.last_results = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            SearchPanel(id="search_panel"),
            ResultPanel(id="result_panel"),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app."""
        self.query_one("#search_input", Input).focus()
        table = self.query_one("#results_table", DataTable)
        table.add_columns("Callsign", "Name", "City", "Status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        button_id = event.button.id
        if button_id == "btn_call":
            self.current_search_type = "call"
        elif button_id == "btn_fnamn":
            self.current_search_type = "fnamn"
        elif button_id == "btn_enamn":
            self.current_search_type = "enamn"
        elif button_id == "btn_ort":
            self.current_search_type = "ort"
        elif button_id == "btn_search":
            pass  # Just do search with current type
        self.perform_search()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input change - just to make sure events are working."""
        pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        self.perform_search()

    def action_do_search(self) -> None:
        """Explicit search action bound to Enter."""
        self.perform_search()

    def perform_search(self) -> None:
        """Perform the search."""
        search_input = self.query_one("#search_input", Input)
        query = search_input.value.strip()

        if not query:
            self.notify("Please enter a search term", severity="warning")
            return

        # Convert to uppercase for callsign searches
        if self.current_search_type == "call":
            query = query.upper()

        try:
            table = self.query_one("#results_table", DataTable)
            table.clear()

            self.last_results = []

            if self.current_search_type == "call":
                results = main.search(call=query)
            elif self.current_search_type == "fnamn":
                results = main.search(fnamn=query)
            elif self.current_search_type == "enamn":
                results = main.search(enamn=query)
            elif self.current_search_type == "ort":
                results = main.search(ort=query)
            else:
                results = []

            self.last_results = results

            for result in results:
                callsign = result.get("callsign", "")
                name = result.get("name", "")
                city = result.get("city", "")
                status = result.get("member_status", "Unknown")
                table.add_row(callsign, name, city, status)

            if not results:
                self.notify("No results found", severity="warning")

        except main.NoResultsError:
            self.notify("No results found", severity="warning")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_search_call(self) -> None:
        """Search by callsign."""
        self.current_search_type = "call"
        self.query_one("#search_input", Input).focus()

    def action_search_fnamn(self) -> None:
        """Search by first name."""
        self.current_search_type = "fnamn"
        self.query_one("#search_input", Input).focus()

    def action_search_enamn(self) -> None:
        """Search by last name."""
        self.current_search_type = "enamn"
        self.query_one("#search_input", Input).focus()

    def action_search_ort(self) -> None:
        """Search by city."""
        self.current_search_type = "ort"
        self.query_one("#search_input", Input).focus()

    def action_refresh(self) -> None:
        """Refresh results."""
        self.perform_search()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_distance(self) -> None:
        """Calculate distance between two callsigns."""
        if len(self.last_results) < 2:
            self.notify(
                "Need at least 2 results for distance calculation", severity="warning"
            )
            return
        # For now, just show a notification - could implement a dialog later
        self.notify("Distance feature: Use CLI with -d option", severity="information")


def run_tui():
    """Run the TUI application."""
    app = CallbookApp()
    app.run()


if __name__ == "__main__":
    run_tui()
