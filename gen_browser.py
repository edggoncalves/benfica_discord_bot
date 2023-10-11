import selenium.webdriver.firefox.webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from selenium.webdriver import Firefox
from selenium.common.exceptions import WebDriverException
from webdriver_manager.firefox import GeckoDriverManager

from shutil import which
from os.path import getctime
from datetime import datetime, timedelta
import configuration


def gen_browser() -> selenium.webdriver.firefox.webdriver.WebDriver:
    driver_age = None
    driver_path = ""
    config = configuration.read()
    if not config.has_section("selenium"):
        driver_path = GeckoDriverManager().install()
        configuration.write({"selenium": {"path": driver_path}})
    else:
        driver_age = getctime(config["selenium"]["path"])

    # Update driver if older than 5 days and save new path if that would be the case
    if driver_age is not None and datetime.now() - datetime.fromtimestamp(
        driver_age
    ) > timedelta(days=5):
        driver_path = GeckoDriverManager().install()
        configuration.write({"selenium": {"path": driver_path}})

    FirefoxService(executable_path=driver_path)
    opts = Options()
    opts.headless = True
    opts.binary_location = which("firefox")
    try:
        browser = Firefox(options=opts)
    except WebDriverException as e:
        raise Exception(f"Could not create browser instance: \n\n{e}")
    return browser
