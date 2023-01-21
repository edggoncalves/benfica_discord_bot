from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver import Firefox
from webdriver_manager.firefox import GeckoDriverManager

from shutil import which
from datetime import datetime
import pytz


URL = 'https://www.slbenfica.pt/pt-pt/futebol/calendario'
TZ = 'Europe/Lisbon'

service = FirefoxService(executable_path=GeckoDriverManager().install())

opts = Options()
opts.headless = True
opts.binary_location = which('firefox')
browser = Firefox(options=opts)

browser.get(URL)
next_match = browser.find_element(By.CLASS_NAME, 'highlight-event-center')
browser.close()
