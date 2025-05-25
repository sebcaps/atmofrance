""" Les constantes pour l'intégration Atmo France """
from dataclasses import dataclass
from enum import Enum
from homeassistant.const import Platform, CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
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
DATA_URL = f"{BASE_URL}/api/data"  # 112 : pollution ; 122 : pollen


class URL_CODE(Enum):
    POLLUTION = 112
    POLLEN = 122


API_GOUV_URL = "https://geo.api.gouv.fr/communes?"

CONF_CODE_POSTAL = "Code postal"
ATTRIBUTION = "Atmo France"
MODEL = "Atmo France API"
CONF_INSEE_CODE = "INSEE"
CONF_INSEE_EPCI = "INSEE EPCI"
CONF_INCLUDE_POLLUTION = "include_pollution"
CONF_INCLUDE_POLLEN = "include_pollen"
CONF_INCLUDE_POLLEN_FORECAST = "include_pollen_forecast"
CONF_INCLUDE_POLLUTION_FORECAST = "include_pollution_forecast"
CONF_POLLUTION_COORDINATOR = "atmofrancecoordinatorpollution"
CONF_POLLEN_COORDINATOR = "atmofrancecoordinatorpollen"
CONF_CITY = "city"
TITLE = "Atmo France"

POLLUTION_LEVEL = {
    0: "Indisponible",
    1: "Bon",
    2: "Moyen",
    3: "Dégradé",
    4: "Mauvais",
    5: "Trés Mauvais",
    6: "Extrêmement mauvais",
    7: "Évènement",
}

POLLEN_LEVEL = {
    0: "Indisponible",
    1: "Très faible",
    2: "Faible",
    3: "Modéré",
    4: "Elevé",
    5: "Trés Elevé",
    6: "Extrêmement élevé",
}

LEVEL_COLOR = {
    0: "#ddd",
    1: "#50f0e6",
    2: "#50ccaa",
    3: "#f0e641",
    4: "#ff5050",
    5: "#960032",
    6: "#872181",
    7: "#888",
}

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

POLLEN_ALERT_SENSORS: tuple[AtmoFranceSensorEntityDescription, ...] = (
    AtmoFranceSensorEntityDescription(
        key="code_ambr",
        name="Niveau Ambroisie",
        device_class=SensorDeviceClass.AQI,
        icon="mdi:alert",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="code_ambr",),
    AtmoFranceSensorEntityDescription(
        key="code_arm",
        name="Niveau Armoise",
        device_class=SensorDeviceClass.AQI,
        icon="mdi:alert",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="code_arm",),
    AtmoFranceSensorEntityDescription(
        key="code_aul",
        name="Niveau Aulne",
        device_class=SensorDeviceClass.AQI,
        icon="mdi:alert",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="code_aul",),
    AtmoFranceSensorEntityDescription(
        key="code_boul",
        name="Niveau Bouleau",
        device_class=SensorDeviceClass.AQI,
        icon="mdi:alert",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="code_boul",),
    AtmoFranceSensorEntityDescription(
        key="code_gram",
        name="Niveau Graminé",
        device_class=SensorDeviceClass.AQI,
        icon="mdi:alert",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="code_gram",),
    AtmoFranceSensorEntityDescription(
        key="code_oliv",
        name="Niveau Olivier",
        device_class=SensorDeviceClass.AQI,
        icon="mdi:alert",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="code_oliv",),
    AtmoFranceSensorEntityDescription(
        key="code_qual", name="Qualité globale Pollen", icon="mdi:gauge", json_key="code_qual"
    ),
)

POLLEN_CONC_SENSORS: tuple[AtmoFranceSensorEntityDescription, ...] = (
    AtmoFranceSensorEntityDescription(
        key="conc_ambr",
        name="Concentration Ambroisie",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        icon="mdi:tree",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        json_key="conc_ambr",),
    AtmoFranceSensorEntityDescription(
        key="conc_arm",
        name="Concentration Armoise",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        icon="mdi:tree",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        json_key="conc_arm",),
    AtmoFranceSensorEntityDescription(
        key="conc_aul",
        name="Concentration Aulne",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        icon="mdi:tree",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        json_key="conc_aul",),
    AtmoFranceSensorEntityDescription(
        key="conc_gram",
        name="Concentration Graminé",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        icon="mdi:grass",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        json_key="conc_gram",),
    AtmoFranceSensorEntityDescription(
        key="conc_boul",
        name="Concentration Bouleau",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        icon="mdi:tree",
        state_class=SensorStateClass.MEASUREMENT,
        json_key="conc_boul",),
    AtmoFranceSensorEntityDescription(
        key="conc_oliv",
        name="Concentration Olivier",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        icon="mdi:tree",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        json_key="conc_oliv",),
)
