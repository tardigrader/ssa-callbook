from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Input, Button, DataTable
from textual.binding import Binding

import main


class CallbookApp(App):
    """SSA Callbook TUI Application."""

    CSS = """
    Screen { layout: grid; grid-size: 1; }
    #search_bar { height: auto; margin: 1; }
    #results { margin: 1; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "set_call", "Call"),
        Binding("f", "set_fnamn", "First"),
        Binding("e", "set_enamn", "Last"),
        Binding("o", "set_ort", "City"),
    ]

    def __init__(self):
        super().__init__()
        self.search_type = "call"

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="search_bar"):
            yield Input(
                placeholder=f"Search (Press Enter) - Type: {self.search_type}",
                id="the_input",
            )
            yield Horizontal(
                Button("Search", variant="primary", id="do_search"),
            )
        with Container(id="results"):
            yield DataTable(id="results_table")
        yield Footer()

    def on_mount(self) -> None:
        input_widget = self.query_one("#the_input", Input)
        input_widget.focus()
        table = self.query_one("#results_table", DataTable)
        table.add_columns("Callsign", "Name", "City", "Status")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.do_search()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "do_search":
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
            elif self.search_type == "fnamn":
                results = main.search(fnamn=query)
            elif self.search_type == "enamn":
                results = main.search(enamn=query)
            elif self.search_type == "ort":
                results = main.search(ort=query)
            else:
                results = []

            table = self.query_one("#results_table", DataTable)
            table.clear()

            for result in results:
                callsign = result.get("callsign", "")
                name = result.get("name", "")
                city = result.get("city", "")
                status = result.get("member_status", "Unknown")
                table.add_row(callsign, name, city, status)

            if not results:
                self.notify("No results found")

        except main.NoResultsError:
            self.notify("No results found")
        except Exception as e:
            self.notify(f"Error: {e}")

    def action_set_call(self) -> None:
        self.search_type = "call"
        self.update_placeholder()

    def action_set_fnamn(self) -> None:
        self.search_type = "fnamn"
        self.update_placeholder()

    def action_set_enamn(self) -> None:
        self.search_type = "enamn"
        self.update_placeholder()

    def action_set_ort(self) -> None:
        self.search_type = "ort"
        self.update_placeholder()

    def update_placeholder(self) -> None:
        input_widget = self.query_one("#the_input", Input)
        input_widget.placeholder = f"Search (Press Enter) - Type: {self.search_type}"
        self.notify(f"Search type: {self.search_type}")

    def action_quit(self) -> None:
        self.exit()


def run_tui():
    app = CallbookApp()
    app.run()


if __name__ == "__main__":
    run_tui()
