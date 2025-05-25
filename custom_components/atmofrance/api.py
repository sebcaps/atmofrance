import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiohttp
from aiohttp.client import ClientTimeout, ClientError
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from .const import AUTH_URL, DATA_URL, API_GOUV_URL, URL_CODE

DEFAULT_TIMEOUT = 120
CLIENT_TIMEOUT = ClientTimeout(total=DEFAULT_TIMEOUT)

_LOGGER = logging.getLogger(__name__)


class TooManyRequestsError(Exception):
    """Exception to handle too many requests error."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AtmoFranceDataApi:
    """Api to get AirAtmo data"""

    def __init__(
        self,
        config,
        session: aiohttp.ClientSession = None,
        timeout=CLIENT_TIMEOUT,
        hass: HomeAssistant = None,
    ) -> None:
        self._timeout = timeout
        if session is not None:
            self._session = session
        else:
            self._session = aiohttp.ClientSession()
        self._config = config
        self._token = None
        self._data = None
        self._hass = hass

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
        elif request.status == 429:
            raise TooManyRequestsError(
                f"Too many requests response from the server, please retry in {request.headers.get("Retry-After")} seconds")
        else:
            raise ConnectionRefusedError(
                f"Failed to get authent token, with error status : {request.status}"
            )

    async def get_data(self, insee_code, type: URL_CODE) -> dict:
        """Get Data from AtmoFrance API"""
        try:
            await self.async_get_token()  # Always called to be sure to have a valid token
        except ConnectionRefusedError as err:
            _LOGGER.error(
                "Failed to get token with status error %s ", err),
            return None
        except TooManyRequestsError as err:
            _LOGGER.error(
                "Too many request error from the server. Try again in %s ", err),
            return None
        headers = {"Authorization": f"Bearer {self._token}"}
        today = datetime.now(
            ZoneInfo(self._hass.config.time_zone)).strftime("%Y-%m-%d")
        url = f'{DATA_URL}/{type.value}/{{"code_zone":{{"operator":"=","value":"{
            insee_code}"}},"date_ech":{{"operator":">=","value":"{today}"}}}}?withGeom=false'
        _LOGGER.debug("Getting data from %s", url)
        try:
            result = await self._session.get(url, headers=headers)
            json = await result.json()
            _LOGGER.debug("Got response %s ", json)
            _LOGGER.debug(
                "Extracting data for INSEE %s and date %s", insee_code, today)
            if len(json["features"]) > 0:  # At least one result
                self._data = json
                _LOGGER.debug(
                    "Got data for INSEE %s and date > %s: %s",
                    insee_code,
                    today,
                    self._data,
                )
            else:  # no result
                self._data = None
                _LOGGER.warning(
                    "No data for INSEE %s and date %s", insee_code, today)
            return json["features"]
        except ClientError as err:
            return err

    def get_key_value(self, key, shift: int = 0):
        """Get value for the given key in JSON Data for a given date based on shift from today"""
        extractDate = (datetime.now(
            ZoneInfo(self._hass.config.time_zone))+timedelta(days=shift)).strftime("%Y-%m-%d")
        if self._data is not None:
            extractedData = next(
                filter(
                    lambda feat: feat["properties"]["date_ech"] == extractDate,
                    self._data["features"],
                ), {"properties": {key: ""}})  # If not found return ''
            return extractedData.get("properties")[key]
        else:
            return ""

    @property
    def source(self):
        """Get value for source of data"""
        if self._data is not None:
            # Take the first value, we have multiple ones for forecast
            return self._data["features"][0]["properties"]["source"]
        return ""

    @property
    def last_update(self):
        """Get value of data update"""
        if self._data is not None:
            # Take the first value, we have multiple ones for forecast
            return self._data["features"][0]["properties"]["date_maj"]
        return ""

    @property
    def type_zone(self):
        """Get type of zone"""
        if self._data is not None:
            # Take the first value, we have multiple ones for forecast
            return self._data["features"][0]["properties"]["type_zone"]
        return ""

    @property
    def nom_zone(self):
        """Get Name of Zone"""
        if self._data is not None:
            # Take the first value, we have multiple ones for forecast
            return self._data["features"][0]["properties"]["lib_zone"]
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
        url = f"{API_GOUV_URL}codePostal={
            zipcode}&fields=code,nom,codeEpci&format=json&geometry=centre"
        result = await self._session.get(url)
        if result.status == 200:
            json = await result.json()
            _LOGGER.debug("Got response for INSEE Code %s ", json)
            if len(json) == 0:
                _LOGGER.error("No INSEE value fetched for %s ", zipcode)
                raise ValueError
            return json
        else:
            _LOGGER.error(
                "Failed to get INSEE data, with status %s ", result.status)
            raise ValueError
