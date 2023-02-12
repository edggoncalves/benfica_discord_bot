from bs4 import BeautifulSoup, element
import requests


def _get_pictures() -> element.ResultSet:
    # Grab html
    r = requests.get("https://24.sapo.pt/jornais/desporto")

    # Parse to something edible
    soup = BeautifulSoup(r.content, features="html.parser")

    # Find all elements tagged with picture
    pictures = soup.findAll("picture")

    return pictures


def _filter_pictures(pictures, jornais) -> list:
    # Return the covers we want
    covers = [
        cover["data-original-src"]
        for cover in pictures
        if cover.get("data-title", "").startswith(jornais)
    ]
    return covers


def sports_covers():
    """
    This script should return links to the covers of the newspapers in jornais tuple
    :return: https://ia.imgs.sapo.pt/...
    """
    jornais = ("A Bola", "O Jogo", "Record")

    pictures = _get_pictures()

    covers = _filter_pictures(pictures, jornais)

    return covers


if __name__ == "__main__":
    sports_covers()
