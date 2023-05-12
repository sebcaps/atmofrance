import logging
from datetime import date
import aiohttp
from aiohttp.client import ClientTimeout, ClientError
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from .const import AUTH_URL, DATA_URL, API_GOUV_URL

DEFAULT_TIMEOUT = 120
CLIENT_TIMEOUT = ClientTimeout(total=DEFAULT_TIMEOUT)

_LOGGER = logging.getLogger(__name__)


class AtmoFranceDataApi:
    """Api to get AirAtmo data"""

    def __init__(
        self, config, session: aiohttp.ClientSession = None, timeout=CLIENT_TIMEOUT
    ) -> None:
        self._timeout = timeout
        if session is not None:
            self._session = session
        else:
            self._session = aiohttp.ClientSession()
        self._config = config
        self._token = None
        self._data = None

    async def async_get_token(self):
        """Get user token to allow request"""

        request = await self._session.post(
            AUTH_URL,
            json={
                "username": self._config[CONF_USERNAME],
                "password": self._config[CONF_PASSWORD],
            },
        )
        if request.status == 200:
            resp = await request.json()
            self._token = resp["token"]
            _LOGGER.debug("got response %s ", resp)
        else:
            _LOGGER.error(
                "Failed to get authent token, with status %s ", request.status
            )
            raise ValueError

    async def get_data(self, insee_code) -> dict:
        """Get Data from AtmoFrance API"""
        await self.async_get_token()  # Always called to be sure to have a valid token
        headers = {"Authorization": f"Bearer {self._token}"}
        today = date.today().strftime("%Y-%m-%d")
        url = f'{DATA_URL}/{{"code_zone":{{"operator":"=","value":"{insee_code}"}},"date_ech":{{"operator":">=","value":"{today}"}}}}?withGeom=false'
        _LOGGER.debug("Getting data from %s", url)
        try:
            result = await self._session.get(url, headers=headers)
            json = await result.json()
            _LOGGER.debug("Got response %s ", json)
            _LOGGER.debug("Extracting data for INSEE %s and date %s", insee_code, today)
            if len(json["features"]) > 0:  # At least one result
                # Extract data for current day
                self._data = next(
                    filter(
                        lambda feat: feat["properties"]["date_ech"] == today,
                        json["features"],
                    )
                )
                _LOGGER.debug(
                    "Extracted data for INSEE %s and date %s: %s",
                    insee_code,
                    today,
                    self._data,
                )
            else:  # no result
                self._data = None
                _LOGGER.warning("No data for INSEE %s and date %s", insee_code, today)
            return json["features"]
        except ClientError as err:
            return err

    def get_key(self, key):
        """Get value for the given key in JSON Data"""
        if self._data is not None:
            return self._data.get("properties")[key]
        else:
            return ""

    @property
    def source(self):
        """Get value for source of data"""
        if self._data is not None:
            return self._data.get("properties")["source"]
        return ""

    @property
    def last_update(self):
        """Get value of data update"""
        if self._data is not None:
            return self._data["properties"]["date_maj"]
        return ""


class INSEEAPI:
    """Api to get INSEE data"""

    def __init__(
        self, session: aiohttp.ClientSession = None, timeout=CLIENT_TIMEOUT
    ) -> None:
        self._timeout = timeout
        if session is not None:
            self._session = session
        else:
            self._session = aiohttp.ClientSession()

    async def get_data(self, zipcode) -> dict:
        """Get INSEE code for a given zip code"""
        url = f"{API_GOUV_URL}codePostal={zipcode}&fields=s=code,nom&format=json&geometry=centre"
        result = await self._session.get(url)
        if result.status == 200:
            json = await result.json()
            _LOGGER.debug("Got response for INSEE Code %s ", json)
            if len(json) == 0:
                _LOGGER.error("No INSEE value fetched for %s ", zipcode)
                raise ValueError
            return json
        else:
            _LOGGER.error("Failed to get INSEE data, with status %s ", result.status)
            raise ValueError
