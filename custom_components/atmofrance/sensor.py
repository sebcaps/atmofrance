""" Implements the sensors component """
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import DeviceEntryType

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from .const import (
    DOMAIN,
    ATTRIBUTION,
    POLLUTION_SENSORS,
    POLLEN_ALERT_SENSORS,
    POLLEN_CONC_SENSORS,
    CONF_CITY,
    CONF_INSEE_CODE,
    CONF_INCLUDE_POLLEN,
    CONF_INCLUDE_POLLUTION,
    CONF_POLLUTION_COORDINATOR,
    CONF_POLLEN_COORDINATOR,
    QUALITY_LEVEL,
    QUALITY_LEVEL_COLOR,
    MODEL,
    TITLE,
    AtmoFranceSensorEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Configuration"""
    config = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if entry.options[CONF_INCLUDE_POLLUTION]:
        coordinatorpollution = config[CONF_POLLUTION_COORDINATOR]
        for sensor_description in POLLUTION_SENSORS:
            entities.append(
                AtmoFranceAlertEntity(hass, entry, sensor_description,
                                      coordinatorpollution))

    if entry.options[CONF_INCLUDE_POLLEN]:
        coordinatorpollen = config[CONF_POLLEN_COORDINATOR]
        for sensor_description in POLLEN_ALERT_SENSORS:
            entities.append(AtmoFranceAlertEntity(
                hass, entry, sensor_description, coordinatorpollen))
        for sensor_description in POLLEN_CONC_SENSORS:
            entities.append(AtmoFrancePollenEntity(
                hass, entry, sensor_description, coordinatorpollen))

    async_add_entities(entities, True)


class AtmoFranceEntity(CoordinatorEntity, SensorEntity):
    """La classe de l'entité Air Atmo"""

    entity_description: AtmoFranceSensorEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        entry_infos,
        description: SensorEntityDescription,
        coordinator,
    ) -> None:
        """Initisalisation de l'entité"""
        super().__init__(coordinator)

        self._hass = hass
        self.entity_description = description
        self._attr_name = f"{
            description.name}-{entry_infos.data.get(CONF_CITY)}"
        self._attr_unique_id = f"{
            entry_infos.entry_id}-{entry_infos.data.get(CONF_INSEE_CODE)}-{description.name}"
        self._device_id = entry_infos.entry_id
        self._coordinator = coordinator
        self._attr_attribution = f"{
            ATTRIBUTION}- {self._coordinator.api.source}"
        self._attr_device_class = description.device_class

        self._attr_device_info = DeviceInfo(
            name=TITLE,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"{coordinator.api.source}-{entry_infos.data.get(CONF_CITY)}")
                         },
            manufacturer=f"{ATTRIBUTION}-{coordinator.api.source}",
            model=MODEL,
        )
        _LOGGER.debug("Creating an atmo France sensor, named %s",
                      self._attr_name)

    @property
    def native_value(self):
        if self._coordinator.api.get_key(self.entity_description.json_key):
            value = self._coordinator.api.get_key(
                self.entity_description.json_key)
        else:
            value = 0
            _LOGGER.warning(
                "Unable to get value for %s. Force value to 0", self._attr_name
            )
        _LOGGER.debug("Value for sensor %s is now %s", self._attr_name, value)
        return value

    def _level2string(self, value):
        return QUALITY_LEVEL[value]

    def _level2color(self, value):
        return QUALITY_LEVEL_COLOR[value]


class AtmoFranceAlertEntity(AtmoFranceEntity):
    def __init__(self, hass, entry_infos, description, coordinator):
        super().__init__(hass, entry_infos, description, coordinator)

    @property
    def extra_state_attributes(self):
        return {
            "Date de mise à jour": self._coordinator.api.last_update,
            "Libellé": self._level2string(self.native_value),
            "Couleur": self._level2color(self.native_value),
            "Type de zone": self._coordinator.api.type_zone,
            "Nom de la zone": self._coordinator.api.nom_zone,
        }


class AtmoFrancePollenEntity(AtmoFranceEntity):
    def __init__(self, hass, entry_infos, description, coordinator):
        super().__init__(hass, entry_infos, description, coordinator)

    @property
    def extra_state_attributes(self):
        return {
            "Date de mise à jour": self._coordinator.api.last_update,
            "Libellé": "libelle",
            "Type de zone": self._coordinator.api.type_zone,
            "Nom de la zone": self._coordinator.api.nom_zone,
        }
