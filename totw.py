from io import BytesIO
from discord import File as DFile
from selenium.webdriver.common.by import By

from gen_browser import gen_browser

TEAM_URL = "https://www.sofascore.com/tournament/238/42655/8519/team-of-the-week/embed"


def fetch_team_week() -> DFile:
    _xpath = '/html/body/div[1]/div'
    browser = gen_browser()
    browser.get(TEAM_URL)
    team = browser.find_element(By.XPATH, _xpath)

    _img = BytesIO(team.screenshot_as_png)
    _img.seek(0)
    return DFile(_img, filename='image.png')
