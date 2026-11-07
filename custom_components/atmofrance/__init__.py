""" Les constantes pour l'intégration Tuto HACS """
import logging
from datetime import timedelta, date
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
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


async def _async_resolve_source(entry: ConfigEntry, api, url_code: URL_CODE) -> str | None:
    """Find which zone code actually returns data for the given indicator.

    Returns CONF_INSEE_CODE (city), CONF_INSEE_EPCI (fallback) or None when
    neither answers. Must be called once per indicator: a city may be covered
    for pollution but not for pollen, and vice versa.
    """
    databycity = await api.get_data(entry.data[CONF_INSEE_CODE], url_code)
    if databycity is not None and len(databycity) > 0:
        # data exist for city, use it
        _LOGGER.info("Use City code: %s as source", entry.data[CONF_INSEE_CODE])
        return CONF_INSEE_CODE

    # Get data for EPCI (communauté de communes)
    databyepci = await api.get_data(entry.data[CONF_INSEE_EPCI], url_code)
    if databyepci is not None and len(databyepci) > 0:
        _LOGGER.info("Use EPCI code: %s as source", entry.data[CONF_INSEE_EPCI])
        return CONF_INSEE_EPCI

    _LOGGER.error(
        "Impossible de récupérer les données pour la ville %s ou l'EPCI %s",
        entry.data[CONF_INSEE_CODE],
        entry.data[CONF_INSEE_EPCI],
    )
    return None


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
        try:
            if entry.options[CONF_INCLUDE_POLLUTION] or entry.options[CONF_INCLUDE_POLLUTION_FORECAST]:
                pollutionapi = AtmoFranceDataApi(entry.data, hass=hass)
                # Get pollution data for city
                _LOGGER.info("Getting Pollution data")
                source = await _async_resolve_source(entry, pollutionapi, URL_CODE.POLLUTION)
                if source is None:
                    raise ConfigEntryNotReady(
                        f"No pollution data available for city {entry.data[CONF_INSEE_CODE]} "
                        f"nor EPCI {entry.data[CONF_INSEE_EPCI]}"
                    )
                hass.data[DOMAIN][entry.entry_id][
                    CONF_POLLUTION_COORDINATOR
                ] = AtmoFrancePollutionApiCoordinator(hass=hass, config=entry, api=pollutionapi, source=source)

            if entry.options[CONF_INCLUDE_POLLEN] or entry.options[CONF_INCLUDE_POLLEN_FORECAST]:
                _LOGGER.info("Getting Pollen data")
                pollenapi = AtmoFranceDataApi(entry.data, hass=hass)
                # `source` is resolved again for pollen: pollution and pollen
                # zones are independent and must never be inherited.
                source = await _async_resolve_source(entry, pollenapi, URL_CODE.POLLEN)
                if source is None:
                    raise ConfigEntryNotReady(
                        f"No pollen data available for city {entry.data[CONF_INSEE_CODE]} "
                        f"nor EPCI {entry.data[CONF_INSEE_EPCI]}"
                    )
                hass.data[DOMAIN][entry.entry_id][
                    CONF_POLLEN_COORDINATOR
                ] = AtmoFrancePollenApiCoordinator(hass=hass, config=entry, api=pollenapi, source=source)
        except ConfigEntryNotReady:
            # Drop the partially built entry so the automatic retry rebuilds it
            hass.data[DOMAIN].pop(entry.entry_id, None)
            raise

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

    async def _fetch(self, url_code: URL_CODE):
        """Récupère un indicateur et traduit l'échec dans ce qu'attend HA.

        Une requête qui échoue devient UpdateFailed : les entités passent en
        indisponible, ce qui est le signal correct.

        Une requête qui aboutit et ne renvoie aucune ligne n'en est pas une.
        Atmo France purge son jeu de données pendant la nuit et le republie
        vers midi ; entre les deux l'API répond parfaitement et n'a rien à
        donner. Traiter ça comme un échec produit une erreur quotidienne dans
        le journal et rend toutes les entités indisponibles jusqu'à midi. La
        mise à jour réussit donc avec une charge utile vide, et chaque capteur
        rapporte sa propre valeur comme inconnue.
        """
        data = await self.api.get_data(
            self.config.data[self._source], url_code)
        if data is None:  # la requête elle-même a échoué
            raise UpdateFailed(
                f'No Data from Atmo France for INSEE code {
                    self.config.data[self._source]} and date {date.today().strftime("%Y-%m-%d")}'
            )
        return data


class AtmoFrancePollutionApiCoordinator (AtmoFranceApiCoordinator):
    """A coordinator to fetch pollution data from the api only once"""

    def __init__(self, hass, config, api, source):
        super().__init__(hass, config, api, source,  update_method=self._update_method)

    async def _update_method(self):
        return await self._fetch(URL_CODE.POLLUTION)


class AtmoFrancePollenApiCoordinator (AtmoFranceApiCoordinator):
    """A coordinator to fetch pollen data from the api only once"""

    def __init__(self, hass, config, api, source):
        super().__init__(hass, config, api, source,  update_method=self._update_method)

    async def _update_method(self):
        return await self._fetch(URL_CODE.POLLEN)
