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
    CONF_CITY,
    CONF_INSEE_CODE,
    QUALITY_LEVEL,
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
    coordinator = config["atmofrancecoordinator"]
    entities = [
        AtmoFranceEntity(hass, entry, sensor_description, coordinator)
        for sensor_description in POLLUTION_SENSORS
    ]
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
        self._attr_name = f"{description.name}-{entry_infos.data.get(CONF_CITY)}"
        self._attr_unique_id = f"{entry_infos.entry_id}-{entry_infos.data.get(CONF_INSEE_CODE)}-{description.name}"
        self._coordinator = coordinator
        self._attr_attribution = f"{ATTRIBUTION}- {self._coordinator.api.source}"
        self._attr_device_class = description.device_class
        self._attr_extra_state_attributes = {
            "Date de mise à jour": self._coordinator.api.last_update,
            "Libellé": self._level2string(self.native_value),
        }
        self._attr_device_info = DeviceInfo(
            name=TITLE,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={
                (DOMAIN, f"{coordinator.api.source}-{entry_infos.data.get(CONF_CITY)}")
            },
            manufacturer=f"{ATTRIBUTION}-{coordinator.api.source}",
            model=MODEL,
        )
        _LOGGER.debug("Creating an atmo France sensor, named %s", self.name)

    @property
    def native_value(self):
        value = self._coordinator.api.get_key(self.entity_description.json_key)
        return value

    def _level2string(self, value):
        if value != "":
            return QUALITY_LEVEL[value]
        else:
            return ""