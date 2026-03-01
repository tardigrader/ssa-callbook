from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Input, DataTable
from textual.binding import Binding

import main


class CallbookApp(App):
    """SSA Callbook TUI Application."""

    CSS = """
    Screen { layout: vertical; }
    #search_bar { height: 3; margin: 1; }
    #results { height: 100%; margin: 1; }
    DataTable { height: 100%; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "set_call", "Call"),
        Binding("f", "set_first", "First"),
        Binding("l", "set_last", "Last"),
        Binding("y", "set_city", "City"),
    ]

    SEARCH_LABELS = {
        "call": "callsign",
        "first": "first name",
        "last": "last name",
        "city": "city",
    }

    def __init__(self):
        super().__init__()
        self.search_type = "call"

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="search_bar"):
            yield Input(
                placeholder=f"Search ({self.search_type_label()}) - Press Enter",
                id="the_input",
            )
        with Container(id="results"):
            yield DataTable(id="results_table")
        yield Footer()

    def search_type_label(self) -> str:
        """Get human-readable label for current search type."""
        return self.SEARCH_LABELS.get(self.search_type, self.search_type)

    def on_mount(self) -> None:
        input_widget = self.query_one("#the_input", Input)
        input_widget.focus()
        table = self.query_one("#results_table", DataTable)
        table.add_columns("Callsign", "Name", "City", "Status")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.do_search()

    def do_search(self) -> None:
        input_widget = self.query_one("#the_input", Input)
        query = input_widget.value.strip()

        if not query:
            self.notify("Please enter a search term")
            return

        if self.search_type == "call":
            query = query.upper()

        try:
            if self.search_type == "call":
                results = main.search(call=query)
            elif self.search_type == "first":
                results = main.search(fnamn=query)
            elif self.search_type == "last":
                results = main.search(enamn=query)
            elif self.search_type == "city":
                results = main.search(ort=query)
            else:
                results = []

            table = self.query_one("#results_table", DataTable)
            table.clear()

            for result in results:
                callsign = result.get("callsign", "")
                name = result.get("name", "")
                postal = result.get("postal_code", "")
                city = result.get("city", "")
                if postal and city:
                    city_display = f"{postal} {city}"
                else:
                    city_display = city
                status = result.get("member_status", "Unknown")
                table.add_row(callsign, name, city_display, status)

            if not results:
                self.notify("No results found")

        except main.NoResultsError:
            self.notify("No results found")
        except Exception as e:
            self.notify(f"Error: {e}")

    def set_search_type(self, search_type: str) -> None:
        self.search_type = search_type
        self.update_placeholder()
        self.query_one("#the_input", Input).focus()

    def action_set_call(self) -> None:
        self.set_search_type("call")

    def action_set_first(self) -> None:
        self.set_search_type("first")

    def action_set_last(self) -> None:
        self.set_search_type("last")

    def action_set_city(self) -> None:
        self.set_search_type("city")

    def update_placeholder(self) -> None:
        input_widget = self.query_one("#the_input", Input)
        input_widget.placeholder = f"Search ({self.search_type_label()}) - Press Enter"

    async def action_quit(self) -> None:
        """Exit the application."""
        self.exit()


def run_tui():
    """Launch the interactive TUI application."""
    app = CallbookApp()
    app.run()


if __name__ == "__main__":
    run_tui()
