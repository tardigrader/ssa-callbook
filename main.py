import argparse
import sys
import re
import math
from urllib.parse import urlencode, quote
from typing import Optional

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from gridtools.gridtools import Grid


BASE_URL = "https://www.ssa.se/ssa/smcb/"


class CallbookError(Exception):
    """Base exception for callbook errors."""

    pass


class NetworkError(CallbookError):
    """Raised when network request fails."""

    pass


class NoResultsError(CallbookError):
    """Raised when no results are found."""

    pass


class ParseError(CallbookError):
    """Raised when HTML parsing fails."""

    pass


def build_search_url(
    call: str | None = None,
    fnamn: str | None = None,
    enamn: str | None = None,
    ort: str | None = None,
) -> str:
    """Build search URL for SSA callbook.

    Args:
        call: Callsign to search for
        fnamn: First name to search for (Swedish: förnamn)
        enamn: Last name to search for (Swedish: efternamn)
        ort: City/location to search for (Swedish: ort)

    Returns:
        Full URL with query parameters for SSA callbook search

    Raises:
        ValueError: If no search parameters are provided
    """
    params = {}
    if call:
        params["call"] = call.upper()
    if fnamn:
        params["fnamn"] = fnamn.strip()
    if enamn:
        params["enamn"] = enamn.strip()
    if ort:
        params["ort"] = ort.strip()

    if not params:
        raise ValueError("At least one search parameter must be provided")

    return f"{BASE_URL}?{urlencode(params)}"


def fetch_results(url: str) -> str:
    """Fetch search results from SSA callbook.

    Args:
        url: Full URL to fetch

    Returns:
        HTML response text from SSA callbook

    Raises:
        NetworkError: If the request fails (timeout, connection error, HTTP error)
    """
    try:
        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "SSA-Callbook/1.0 (Contact: github.com/anomalyco/ssa_callbook)"
            },
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        raise NetworkError("Request timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        raise NetworkError("Connection error. Please check your internet connection.")
    except requests.exceptions.HTTPError as e:
        raise NetworkError(f"HTTP error: {e}")


def parse_results(html: str) -> list[dict]:
    """Parse HTML response from SSA callbook.

    Args:
        html: HTML content from SSA callbook search results

    Returns:
        List of dictionaries containing parsed callbook entries

    Raises:
        ParseError: If the HTML structure cannot be parsed
    """
    soup = BeautifulSoup(html, "html.parser")

    results = []

    content = soup.find("div", class_="entry-content")
    if not content:
        raise ParseError("Could not find entry content in response")

    # Swedish callsign pattern
    swedish_callsign_pattern = re.compile(
        r"^(?:[78]|SM|SA|S[FKHGJ-NP-R]|SF|SG|SH|SJ|SK|SS)\d?[A-Z0-9]{1,3}(?:-[A-Z0-9]+)?$",
        re.IGNORECASE,
    )

    # First try table format (search by name/ort)
    tables = content.find_all("table")
    for table in tables:
        if table.get("class") and "smcb-search" in table.get("class", []):
            continue

        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        header_row = rows[0]
        headers = [
            th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])
        ]

        if "call" not in headers:
            continue

        for row in rows[1:]:
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue

            entry = {}
            for i, col in enumerate(cols):
                text = col.get_text(strip=True)
                if i < len(headers):
                    header = headers[i]
                    if "medlem" in header or header == "m":
                        if text == "M":
                            entry["member_status"] = "Medlem"
                        elif text == "E":
                            entry["member_status"] = "Ej medlem"
                    elif "call" in header:
                        if swedish_callsign_pattern.match(text):
                            entry["callsign"] = text.upper()
                    elif "förnamn" in header:
                        entry["name"] = text
                    elif "efternamn" in header:
                        if "name" in entry:
                            entry["name"] = entry["name"] + " " + text
                        else:
                            entry["name"] = text
                    elif "adress" in header:
                        entry["address"] = text
                    elif "qth" in header or "ort" in header:
                        if "postal_code" in entry:
                            entry["city"] = text
                        else:
                            entry["city"] = text

            if entry:
                results.append(entry)

    # Then try block format (search by call)
    divs = content.find_all("div", align="center")
    for div in divs:
        blocks = div.find_all("span", class_="block")
        if not blocks:
            continue

        entry = {}

        for block in blocks:
            text = block.get_text(separator="|", strip=True)
            lines = [line.strip() for line in text.split("|") if line.strip()]

            i = 0
            while i < len(lines):
                line = lines[i]

                if swedish_callsign_pattern.match(line):
                    entry["callsign"] = line.upper()
                elif line == "Medlem":
                    entry["member_status"] = "Medlem"
                elif line == "Ej medlem":
                    entry["member_status"] = "Ej medlem"
                elif line == "Mob:" and i + 1 < len(lines):
                    entry["mobile"] = lines[i + 1]
                    i += 1
                elif "E-post:" in line and i + 1 < len(lines):
                    entry["email"] = lines[i + 1]
                    i += 1
                elif "QTH lokator:" in line and i + 1 < len(lines):
                    entry["qth_locator"] = lines[i + 1]
                    i += 1
                elif re.match(r"^\d{3}\s*\d{2}", line):
                    parts = line.split(None, 1)
                    entry["postal_code"] = parts[0]
                    if len(parts) > 1:
                        entry["city"] = parts[1]
                elif "name" not in entry and re.match(
                    r"^[A-ZÅÄÖ][a-zåäö]+\s+[A-ZÅÄÖ][a-zåäö]", line
                ):
                    entry["name"] = line
                elif (
                    "address" not in entry
                    and re.match(r"^[A-Za-zåäöÅÄÖ].+\d+", line)
                    and len(line) < 50
                ):
                    entry["address"] = line

                i += 1

        if entry:
            results.append(entry)

    return results


def has_results(html: str) -> bool:
    """Check if HTML response contains any search results.

    Args:
        html: HTML content from SSA callbook

    Returns:
        True if results are found, False otherwise
    """
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", class_="entry-content")
    if not content:
        return False

    if content.find("div", align="center"):
        return True

    tables = content.find_all("table")
    for table in tables:
        if table.get("class") and "smcb-search" in table.get("class", []):
            continue
        rows = table.find_all("tr")
        if len(rows) >= 2:
            return True

    return False


def is_limited(html: str) -> bool:
    """Check if SSA indicates results are limited to 50.

    Args:
        html: HTML content from SSA callbook

    Returns:
        True if SSA shows limit message, False otherwise
    """
    return "Fler än 50 träffar" in html or "sökning begränsad" in html


def search(
    call: str | None = None,
    fnamn: str | None = None,
    enamn: str | None = None,
    ort: str | None = None,
) -> tuple[list[dict], bool]:
    """Search SSA callbook for amateur radio callsigns.

    Args:
        call: Callsign to search for
        fnamn: First name to search for
        enamn: Last name to search for
        ort: City/location to search for

    Returns:
        Tuple of (list of callbook entries, bool indicating if results are limited)

    Raises:
        ValueError: If no search parameters are provided
        NoResultsError: If no results are found
        NetworkError: If the request fails
        ParseError: If the response cannot be parsed
    """
    if not any([call, fnamn, enamn, ort]):
        raise ValueError("At least one search parameter must be provided")

    url = build_search_url(call, fnamn, enamn, ort)
    html = fetch_results(url)

    if not has_results(html):
        raise NoResultsError("No results found for the given search criteria")

    return parse_results(html), is_limited(html)


def get_osm_link_from_qth(result: dict) -> Optional[str]:
    """Get map link from QTH locator (precise)."""
    if "qth_locator" in result and result["qth_locator"]:
        try:
            grid = Grid(result["qth_locator"])
            lat, lon = grid.lat, grid.long
            return f"https://www.openstreetmap.org/?mlat={lat:.4f}&mlon={lon:.4f}#map=12/{lat:.4f}/{lon:.4f}"
        except Exception:
            pass
    return None


def get_osm_link_from_address(result: dict) -> Optional[str]:
    """Get map link from address (approximate)."""
    if "address" in result and "city" in result:
        address = result.get("address", "")
        city = result.get("city", "")
        if address and city:
            city_clean = city.split()[-1] if city else city
            queries_to_try = [
                f"{address}, {city_clean}, Sweden",
                f"{city_clean}, Sweden",
            ]
            for query in queries_to_try:
                try:
                    geocode_url = f"https://nominatim.openstreetmap.org/search?format=json&q={quote(query)}"
                    response = requests.get(
                        geocode_url,
                        headers={"User-Agent": "SSA-Callbook/1.0"},
                        timeout=10,
                    )
                    data = response.json()
                    if data:
                        lat = data[0]["lat"]
                        lon = data[0]["lon"]
                        return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=12/{lat}/{lon}"
                except Exception:
                    pass
    return None


def calculate_distance(locator1: str, locator2: str) -> dict:
    """Calculate distance and bearing between two Maidenhead locators.

    Uses the haversine formula to calculate great-circle distance
    between two QTH locators.

    Args:
        locator1: First Maidenhead locator (e.g., "JP94vc")
        locator2: Second Maidenhead locator (e.g., "JP94vc")

    Returns:
        Dictionary with 'distance_km' and 'bearing' keys

    Raises:
        ValueError: If either locator is invalid
    """
    try:
        grid1 = Grid(locator1)
        grid2 = Grid(locator2)

        lat1, lon1 = grid1.lat, grid1.long
        lat2, lon2 = grid2.lat, grid2.long

        R = 6371

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance_km = R * c

        bearing = math.degrees(
            math.atan2(
                math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2)),
                math.cos(math.radians(lat1)) * math.sin(math.radians(lat2))
                - math.sin(math.radians(lat1))
                * math.cos(math.radians(lat2))
                * math.cos(math.radians(lon2 - lon1)),
            )
        )
        bearing = (bearing + 360) % 360

        return {
            "distance_km": round(distance_km),
            "bearing": round(bearing),
        }
    except Exception as e:
        raise ValueError(f"Invalid locator(s): {locator1}, {locator2}") from e


def format_result(
    result: dict,
    index: int = 0,
    console: Console | None = None,
) -> None:
    """Format and print a single callbook result.

    Args:
        result: Dictionary containing callbook entry data
        index: Result index (for display purposes)
        console: Rich Console instance (created if not provided)
    """
    if console is None:
        console = Console()

    status = result.get("member_status", "Unknown")
    callsign = result.get("callsign", "")

    if status == "Medlem":
        status_color = "green"
    elif status == "Ej medlem":
        status_color = "red"
    else:
        status_color = "yellow"

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    if callsign:
        table.add_row(
            "Callsign",
            f"[{status_color}]{callsign}[/{status_color}] [{status_color}]({status})[/{status_color}]",
        )

    if "name" in result:
        table.add_row("Name", result["name"])

    if "address" in result:
        table.add_row("Address", result["address"])

    if "postal_code" in result or "city" in result:
        postal = result.get("postal_code", "")
        city = result.get("city", "")
        if postal and city:
            table.add_row("City", f"{postal} {city}")
        elif city:
            table.add_row("City", city)

    if "mobile" in result:
        table.add_row("Mobile", result["mobile"])

    if "email" in result:
        table.add_row("Email", result["email"])

    if "qth_locator" in result:
        table.add_row("QTH Locator", result["qth_locator"])

    # Show map links
    qth_link = get_osm_link_from_qth(result)
    address_link = get_osm_link_from_address(result)

    if qth_link:
        table.add_row("Map (QTH)", f"{qth_link} [dim](precise)[/dim]")
    if address_link:
        if qth_link:
            table.add_row("Map (Address)", f"{address_link} [dim](approx.)[/dim]")
        else:
            table.add_row("Map", f"{address_link} [dim](approx.)[/dim]")

    console.print(table)


def main():
    """CLI entry point."""
    console = Console()

    parser = argparse.ArgumentParser(
        description="Search SSA SM-Callbook for amateur radio callsigns",
    )

    parser.add_argument("-c", "--call", help="Callsign to search for")
    parser.add_argument("-f", "--first", dest="first", help="First name to search for")
    parser.add_argument("-l", "--last", dest="last", help="Last name to search for")
    parser.add_argument("-y", "--city", dest="city", help="Location/city to search for")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show full search URL used"
    )
    parser.add_argument(
        "-d",
        "--distance",
        nargs=2,
        metavar=("LOC1", "LOC2"),
        help="Calculate distance between two callsigns or locators (e.g., SA2NTA SM2OAE or JP94VC KP03ER)",
    )
    parser.add_argument(
        "-t", "--tui", action="store_true", help="Launch interactive TUI"
    )

    args = parser.parse_args()

    if args.tui:
        from tui import run_tui

        run_tui()
        sys.exit(0)

    if args.distance:
        loc1, loc2 = args.distance

        def is_locator(loc: str) -> bool:
            return bool(re.match(r"^[A-Ra-r]{2}\d{2}([A-Xa-x]{2})?$", loc))

        def get_locator(loc: str) -> str | None:
            """Get QTH locator for a callsign or return the locator if already one."""
            loc_upper = loc.upper()
            if is_locator(loc_upper):
                return loc_upper
            try:
                results, _ = search(call=loc_upper)
                if results and results[0].get("qth_locator"):
                    return results[0]["qth_locator"]
            except Exception:
                pass
            return None

        try:
            locator1 = get_locator(loc1)
            locator2 = get_locator(loc2)

            if not locator1:
                console.print(f"[red]Could not find QTH locator for {loc1}[/red]")
                sys.exit(1)
            if not locator2:
                console.print(f"[red]Could not find QTH locator for {loc2}[/red]")
                sys.exit(1)

            result = calculate_distance(locator1, locator2)
            console.print(
                f"[cyan]Distance:[/cyan] {result['distance_km']} km (bearing: {result['bearing']}°)"
            )
            console.print(f"[dim]From {loc1.upper()} to {loc2.upper()}[/dim]")
            sys.exit(0)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

    if not any([args.call, args.first, args.last, args.city]):
        parser.print_help()
        sys.exit(1)

    try:
        if args.verbose:
            url = build_search_url(args.call, args.first, args.last, args.city)
            console.print(f"[dim]Searching: {url}[/dim]\n")

        results, is_limited = search(args.call, args.first, args.last, args.city)

        console.print(f"[dim]Found {len(results)} result(s)[/dim]\n")

        if is_limited:
            console.print(
                f"[yellow]Note: Results are limited to 50. There may be more.[/yellow]\n"
            )

        for i, result in enumerate(results):
            if i > 0:
                console.print()
            format_result(result, i, console)

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except NetworkError as e:
        console.print(f"[red]Network Error: {e}[/red]")
        sys.exit(2)
    except NoResultsError as e:
        console.print(f"[yellow]No Results: {e}[/yellow]")
        sys.exit(3)
    except ParseError as e:
        console.print(f"[red]Parse Error: {e}[/red]")
        sys.exit(4)
    except Exception as e:
        console.print(f"[red]Unexpected Error: {e}[/red]")
        sys.exit(5)


if __name__ == "__main__":
    main()
