"""Calendar API client for SL Benfica website.

This module provides an alternative approach to fetching match data
via the Benfica website's API instead of web scraping.

Note: This is experimental and not currently integrated with the main bot.
"""

import logging
from typing import Any

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from immutables import CALENDAR_API_URL, CALENDAR_URL

logger = logging.getLogger(__name__)

# Note: This season should be updated annually
CURRENT_SEASON = "2024/25"


class Calendar:
    """Client for interacting with SL Benfica calendar API."""

    def __init__(self):
        """Initialize Calendar client and fetch verification token."""
        self.session = requests.Session()
        self.ua = UserAgent()
        self.user_agent = self.ua.firefox
        self.first_headers = {
            "Host": "www.slbenfica.pt",
            "User-Agent": self.user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        self.first_response = self.session.get(
            CALENDAR_URL,
            headers=self.first_headers,
            timeout=30
        )
        self.soup = BeautifulSoup(
            self.first_response.content,
            features="html.parser"
        )
        token_input = self.soup.find(
            name="input",
            attrs={"name": "__RequestVerificationToken", "type": "hidden"}
        )
        self.request_verification_token = token_input["value"]
        logger.debug("Calendar client initialized")

    def _create_cookies(self) -> str:
        """Create cookie string from session cookies.

        Returns:
            Formatted cookie string for request headers.
        """
        cookies_dict = self.first_response.cookies.get_dict()
        cookies = "; ".join([
            f"benficadp#{cookies_dict['benficadp#lang']}",
            f"ASP.NET_SessionId={cookies_dict['ASP.NET_SessionId']}",
            f"SC_ANALYTICS_GLOBAL_COOKIE="
            f"{cookies_dict['SC_ANALYTICS_GLOBAL_COOKIE']}",
            f"__RequestVerificationToken="
            f"{cookies_dict['__RequestVerificationToken']}",
            f"TS01810e8d={cookies_dict['TS01810e8d']}",
            f"TSbc7b53c7027={cookies_dict['TSbc7b53c7027']}",
        ])
        return cookies

    def _create_payload(self) -> dict[str, Any]:
        """Create API request payload.

        Returns:
            Dictionary with filters for calendar API.
        """
        modality = self.soup.find("div", attrs={"class": "modality"})["id"]
        payload = {
            "filters": {
                "Menu": "next",
                "Modality": f"{modality}",
                "IsMaleTeam": "true",
                "Rank": "16094ecf-9e78-4e3e-bcdf-28e4f765de9f",
                "Tournaments": [
                    "sr:tournament:853",
                    "sr:tournament:7",
                    "sr:tournament:679",
                    "sr:tournament:238",
                    "sr:tournament:345",
                    "sr:tournament:327",
                    "sr:tournament:336"
                ],
                "Seasons": [CURRENT_SEASON],
                "PageNumber": 0
            }
        }
        return payload

    def _create_headers(self) -> dict[str, str]:
        """Create request headers for API call.

        Returns:
            Dictionary with HTTP headers.
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,pt-PT;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.slbenfica.pt/pt-pt/futebol/calendario",
            "Content-Type": "application/json",
            "__RequestVerificationToken": self.request_verification_token,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Length": "0",
            "Origin": "https://www.slbenfica.pt",
            "DNT": "1",
            "Connection": "keep-alive",
            "Cookie": self._create_cookies(),
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
        }
        return headers

    def get_events(self) -> dict[str, Any]:
        """Fetch calendar events from API.

        Returns:
            Dictionary with calendar event data.

        Raises:
            requests.HTTPError: If API request fails.
        """
        headers = self._create_headers()
        logger.debug("Fetching calendar events from API")
        response = self.session.post(
            CALENDAR_API_URL,
            headers=headers,
            timeout=30,
            allow_redirects=True
        )
        response.raise_for_status()
        logger.info("Calendar events fetched successfully")
        return response.json()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    calendar = Calendar()
    events = calendar.get_events()
    print(events)
