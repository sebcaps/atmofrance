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
    CONF_INCLUDE_POLLEN,
    CONF_INCLUDE_POLLUTION,
    CONF_INCLUDE_POLLEN_FORECAST,
    CONF_INCLUDE_POLLUTION_FORECAST,
    CONF_POLLUTION_COORDINATOR,
    CONF_POLLEN_COORDINATOR,
    URL_CODE
)

_LOGGER = logging.getLogger(__name__)

PLATFORM: list[Platform] = [Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Migrate old entry."""

    _LOGGER.debug("Migrating configuration from version %s.%s",
                  entry.version, entry.minor_version)

    if entry.version == 1:  # Migrate from version 1 to version 2
        new = {**entry.options}
        new[CONF_INCLUDE_POLLUTION] = True
        new[CONF_INCLUDE_POLLEN] = False
        hass.config_entries.async_update_entry(
            entry, options=new, version=2)
        return True
    # Migrate to  version 3  (support for forecast)
    if entry.version == 2:
        _LOGGER.debug("Migrating configuration from version %s.%s to version 3",
                      entry.version, entry.minor_version)
        new = {**entry.options}
        new[CONF_INCLUDE_POLLEN_FORECAST] = False
        new[CONF_INCLUDE_POLLUTION_FORECAST] = False
        hass.config_entries.async_update_entry(
            entry, options=new, version=3)
        return True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Initialisation from a config entry."""
    _LOGGER.info(
        "Initializing %s integration with plaforms: %s with config: %s",
        DOMAIN,
        PLATFORMS,
        entry,
    )
    hass.data.setdefault(DOMAIN, {})

    if entry.entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][entry.entry_id] = {}
        source = None
        if entry.options[CONF_INCLUDE_POLLUTION] or entry.options[CONF_INCLUDE_POLLUTION_FORECAST]:
            pollutionapi = AtmoFranceDataApi(entry.data, hass=hass)
            # Get pollution data for city
            _LOGGER.info("Getting Pollution data")
            databycity = await pollutionapi.get_data(entry.data[CONF_INSEE_CODE], URL_CODE.POLLUTION)
            if (
                databycity is not None and len(databycity) > 0
            ):  # data exist for city, use it
                _LOGGER.info("Use City code: %s as  source",
                             entry.data[CONF_INSEE_CODE])
                source = CONF_INSEE_CODE
            else:  # Get data for EPCI (communauté de commune)
                databyepci = await pollutionapi.get_data(entry.data[CONF_INSEE_EPCI], URL_CODE.POLLUTION)
                if databyepci is not None and len(databyepci) > 0:
                    source = CONF_INSEE_EPCI
                    _LOGGER.info("Use EPCI code: %s as source",
                                 entry.data[CONF_INSEE_EPCI])
                else:
                    _LOGGER.error(
                        "Impossible de récupérer les données pour la ville %s ou l'EPCI %s",
                        entry.data[CONF_INSEE_CODE],
                        entry.data[CONF_INSEE_EPCI],
                    )
            if not (source is None):
                hass.data[DOMAIN][entry.entry_id][
                    CONF_POLLUTION_COORDINATOR
                ] = AtmoFrancePollutionApiCoordinator(hass=hass, config=entry, api=pollutionapi, source=source)

        if entry.options[CONF_INCLUDE_POLLEN] or entry.options[CONF_INCLUDE_POLLEN_FORECAST]:
            _LOGGER.info("Getting Pollen data")
            pollenapi = AtmoFranceDataApi(entry.data, hass=hass)

            databycity = await pollenapi.get_data(entry.data[CONF_INSEE_CODE], URL_CODE.POLLEN)
            if (
                databycity is not None and len(databycity) > 0
            ):  # data exist for city, use it
                _LOGGER.info("Use City code: %s as  source",
                             entry.data[CONF_INSEE_CODE])
                source = CONF_INSEE_CODE
            else:  # Get data for EPCI (communauté de commune)
                databyepci = await pollenapi.get_data(entry.data[CONF_INSEE_EPCI], URL_CODE.POLLEN)
                if databyepci is not None and len(databyepci) > 0:
                    source = CONF_INSEE_EPCI
                    _LOGGER.info("Use EPCI code: %s as source",
                                 entry.data[CONF_INSEE_EPCI])
                else:
                    _LOGGER.error(
                        "Impossible de récupérer les données pour la ville %s ou l'EPCI %s",
                        entry.data[CONF_INSEE_CODE],
                        entry.data[CONF_INSEE_EPCI],
                    )
            if not (source is None):
                hass.data[DOMAIN][entry.entry_id][
                    CONF_POLLEN_COORDINATOR
                ] = AtmoFrancePollenApiCoordinator(hass=hass, config=entry, api=pollenapi, source=source)

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    _LOGGER.debug("Setup of %s successful", entry.title)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """This method is called to clean all sensors before re-adding them"""
    _LOGGER.debug("async_unload_entry method called")
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Remove config entry from domain.
        entry = hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class AtmoFranceApiCoordinator(DataUpdateCoordinator):
    """A coordinator to fetch data from the api only once"""

    def __init__(self, hass, config: ConfigType, api, source, update_method):
        super().__init__(
            hass,
            _LOGGER,
            name=NAME,  # for logging purpose

            update_interval=timedelta(minutes=REFRESH_INTERVALL),
        )
        self.config = config
        self.hass = hass
        self.api = api
        self._source = source
        self.update_method = update_method

    async def async_unload_entry(self, hass: HomeAssistant, entry: ConfigEntry) -> bool:
        """This method is called to clean all sensors before re-adding them"""
        _LOGGER.debug("async_unload_entry method called")
        await hass.config_entries.async_unload_platforms(
            entry, [Platform.SENSOR]
        )


class AtmoFrancePollutionApiCoordinator (AtmoFranceApiCoordinator):
    """A coordinator to fetch pollution data from the api only once"""

    def __init__(self, hass, config, api, source):
        super().__init__(hass, config, api, source,  update_method=self._update_method)

    async def _update_method(self):
        data = await self.api.get_data(self.config.data[self._source], URL_CODE.POLLUTION)
        if data is not None and len(data) > 0:
            return True
        else:
            self.async_set_update_error(
                f'No Data from Atmo France for INSEE code {
                    self.config.data[self._source]} and date {date.today().strftime("%Y-%m-%d")}'
            )
        return False


class AtmoFrancePollenApiCoordinator (AtmoFranceApiCoordinator):
    """A coordinator to fetch pollen data from the api only once"""

    def __init__(self, hass, config, api, source):
        super().__init__(hass, config, api, source,  update_method=self._update_method)

    async def _update_method(self):
        data = await self.api.get_data(self.config.data[self._source], URL_CODE.POLLEN)
        if data is not None and len(data) > 0:
            return True
        else:
            self.async_set_update_error(
                f'No Data from Atmo France for INSEE code {
                    self.config.data[self._source]} and date {date.today().strftime("%Y-%m-%d")}'
            )
        return False
