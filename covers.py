import requests
from requests.exceptions import RequestException
from io import BytesIO
from os import getenv
from sys import platform
from bs4 import BeautifulSoup, element
from PIL import Image

URL = "https://24.sapo.pt/jornais/desporto"


def _get_pictures() -> element.ResultSet:
    # Grab html
    r = _request_with_retry(URL)
    if r is None:
        raise Exception("Could not get pictures")

    # Parse to something edible
    soup = BeautifulSoup(r.content, features='html.parser')

    # Find all elements tagged with picture
    pictures = soup.findAll('picture')

    return pictures


def _request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5.0)
            response.raise_for_status()
            return response
        except RequestException as e:
            if attempt < max_retries - 1:
                print("Retrying...")
            else:
                print(f"Max retries exceeded. Giving up.\n\n{e}")
                return None


def _filter_pictures(pictures, jornais) -> list:
    # Return the covers we want
    covers = [
        cover['data-original-src'] for cover in pictures if cover.get('data-title', '').startswith(jornais)
    ]
    return covers


def sports_covers():
    """
    This script should return links to the covers of the newspapers in jornais tuple
    :return: https://ia.imgs.sapo.pt/...
    """
    jornais = ('A Bola', 'O Jogo', 'Record')

    pictures = _get_pictures()

    covers = _filter_pictures(pictures, jornais)

    return create_collage(covers)


def create_collage(_urls: list[str]) -> str:
    images = []
    max_width = 0
    for url in _urls:
        resp = requests.get(url, timeout=5.0)
        aux = Image.open(BytesIO(resp.content))
        images.append(aux)
        if aux.width > max_width:
            max_width = aux.width
    
    # scale the smaller images to all have the same width
    max_height = 0
    for i, img in enumerate(images):
        w, h = images[i].size
        if w == max_width:
            continue
        new_h = (h*max_width) // w
        images[i] = images[i].resize((max_width, new_h), Image.Resampling.BICUBIC)

        if images[i].height > max_height:
            max_height = images[i].height

    # create the blank collage, with dimensions being 3*width and the biggest height of
    # the three images
    
    collage = Image.new('RGB', (3*max_width, max_height), "#FFF")
    
    for i, img in enumerate(images):
        collage.paste(img, (max_width*i, 0))

    if platform == 'win32':
        _path = f"{getenv('TMP')}\\collage.jpg"
    else:
        _path = '/tmp/collage.jpg'

    collage.save(_path, 'JPEG')

    return _path
