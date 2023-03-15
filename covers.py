from io import BytesIO
from os import getenv
from sys import platform

import requests

from bs4 import BeautifulSoup, element
from PIL import Image

def _get_pictures() -> element.ResultSet:
    # Grab html
    r = requests.get('https://24.sapo.pt/jornais/desporto')

    # Parse to something edible
    soup = BeautifulSoup(r.content, features='html.parser')

    # Find all elements tagged with picture
    pictures = soup.findAll('picture')

    return pictures


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
    for i,img in enumerate(images):
        w, h = images[i].size
        if w == max_width:
            continue
        new_h = (h*max_width) // w
        images[i] = images[i].resize( (max_width, new_h), Image.Resampling.BICUBIC)

        if images[i].height > max_height:
            max_height = images[i].height

    # create the blank collage, with dimentions being 3*width and the biggest height of
    # the three images
    
    collage = Image.new('RGB', (3*max_width, max_height), "#FFF" )
    
    for i, img in enumerate(images):
        collage.paste(img, (max_width*i,0))
    

    if platform == 'win32':
        _path = f"{getenv('TMP')}\\collage.jpg"
    else:
        _path = '/tmp/collage.jpg'

    collage.save(_path, 'JPEG')

    return _path

