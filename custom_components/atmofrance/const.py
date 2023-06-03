""" Les constantes pour l'intégration Atmo France """
from dataclasses import dataclass
from homeassistant.const import Platform
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)


DOMAIN = "atmofrance"
NAME = "Atmo France"
PLATFORMS: list[Platform] = [Platform.SENSOR]
CLIENT_TIMEOUT = 10
BASE_URL = "https://admindata.atmo-france.org"
AUTH_URL = f"{BASE_URL}/api/login"
DATA_URL = f"{BASE_URL}/api/data/112"
API_GOUV_URL = "https://geo.api.gouv.fr/communes?"

CONF_CODE_POSTAL = "Code postal"
ATTRIBUTION = "Atmo France"
MODEL = "Atmo France API"
CONF_INSEE_CODE = "INSEE"
CONF_CITY = "city"
TITLE = "Atmo France"
QUALITY_LEVEL = {1: "Bon", 2: "Moyen", 3: "Dégradé", 4: "Mauvais", 5: "Trés Mauvais"}
REFRESH_INTERVALL = 60


@dataclass
class AtmoFranceRequiredKeysMixin:
    """Mixin for required keys."""

    json_key: str


@dataclass
class AtmoFranceSensorEntityDescription(
    SensorEntityDescription, AtmoFranceRequiredKeysMixin
):
    """Describes AirAtmo sensor entity."""


POLLUTION_SENSORS: tuple[AtmoFranceSensorEntityDescription, ...] = (
    AtmoFranceSensorEntityDescription(
        key="code_no2",
        name="Dioxyde d'azote",
        device_class=SensorDeviceClass.AQI,
        icon="mdi:molecule",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="code_no2",
    ),
    AtmoFranceSensorEntityDescription(
        key="code_o3",
        name="Ozone",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:molecule",
        json_key="code_o3",
    ),
    AtmoFranceSensorEntityDescription(
        key="code_pm10",
        name="PM10",
        device_class=SensorDeviceClass.AQI,
        icon="mdi:blur",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="code_pm10",
    ),
    AtmoFranceSensorEntityDescription(
        key="code_pm25",
        name="PM25",
        device_class=SensorDeviceClass.AQI,
        icon="mdi:blur",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="code_pm25",
    ),
    AtmoFranceSensorEntityDescription(
        key="code_so2",
        name="Dioxyde de soufre",
        device_class=SensorDeviceClass.AQI,
        icon="mdi:molecule",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="code_so2",
    ),
    AtmoFranceSensorEntityDescription(
        key="code_qual", name="Qualité globale", icon="mdi:gauge", json_key="code_qual"
    ),
)
