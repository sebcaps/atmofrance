""" Les constantes pour l'intégration Tuto HACS """
import logging
from datetime import timedelta, date
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AtmoFranceDataApi
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_INSEE_CODE,
    REFRESH_INTERVALL,
    NAME,
    CONF_INSEE_EPCI,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Initialisation from a config entry."""
    _LOGGER.info(
        "Initializing %s integration with plaforms: %s with config: %s",
        DOMAIN,
        PLATFORMS,
        entry,
    )
    hass.data.setdefault(DOMAIN, {})
    api = AtmoFranceDataApi(entry.data, hass=hass)
    if entry.entry_id not in hass.data[DOMAIN]:
        # Get data for city
        databycity = await api.get_data(entry.data[CONF_INSEE_CODE])
        if (
            databycity is not None and len(databycity) > 0
        ):  # data exist for city, use it
            _LOGGER.info("Use City code: %s as  source", entry.data[CONF_INSEE_CODE])
            source = CONF_INSEE_CODE
        else:  # Get data for EPCI (communauté de commune)
            databyepci = await api.get_data(entry.data[CONF_INSEE_EPCI])
            if databyepci is not None and len(databyepci) > 0:
                source = CONF_INSEE_EPCI
                _LOGGER.info("Use EPCI code: %s as source", entry.data[CONF_INSEE_EPCI])
            else:
                _LOGGER.error(
                    "Impossible de récupérer les données pour la ville %s ou l'EPCI %s",
                    entry.data[CONF_INSEE_CODE],
                    entry.data[CONF_INSEE_EPCI],
                )

        hass.data[DOMAIN][entry.entry_id] = {}
        hass.data[DOMAIN][entry.entry_id][
            "atmofrancecoordinator"
        ] = AtmoFranceApiCoordinator(hass=hass, config=entry, api=api, source=source)
    await hass.data[DOMAIN][entry.entry_id][
        "atmofrancecoordinator"
    ].async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    _LOGGER.debug("Setup of %s successful", entry.title)

    return True


class AtmoFranceApiCoordinator(DataUpdateCoordinator):
    """A coordinator to fetch data from the api only once"""

    def __init__(self, hass, config: ConfigType, api, source):
        super().__init__(
            hass,
            _LOGGER,
            name=NAME,  # for logging purpose
            update_method=self._update_method,
            update_interval=timedelta(minutes=REFRESH_INTERVALL),
        )
        self.config = config
        self.hass = hass
        self.api = api
        self._source = source

    async def _update_method(self):
        data = await self.api.get_data(self.config.data[self._source])
        if data is not None and len(data) > 0:
            return True
        else:
            self.async_set_update_error(
                f'No Data from Atmo France for INSEE code {self.config.data[self._source]} and date {date.today().strftime("%Y-%m-%d")}'
            )
            return False

    async def async_unload_entry(self, hass: HomeAssistant, entry: ConfigEntry) -> bool:
        """This method is called to clean all sensors before re-adding them"""
        _LOGGER.debug("async_unload_entry method called")
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, [Platform.SENSOR]
        )
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)
        return unload_ok
