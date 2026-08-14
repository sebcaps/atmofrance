"""Fixtures shared by the atmofrance tests."""
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.atmofrance.const import (
    CONF_CITY,
    CONF_INCLUDE_POLLEN,
    CONF_INCLUDE_POLLEN_FORECAST,
    CONF_INCLUDE_POLLUTION,
    CONF_INCLUDE_POLLUTION_FORECAST,
    CONF_INSEE_CODE,
    CONF_INSEE_EPCI,
)

CITY_CODE = "33063"
EPCI_CODE = "243300316"

ENTRY_DATA = {
    CONF_USERNAME: "user@example.com",
    CONF_PASSWORD: "hunter2",
    CONF_INSEE_CODE: CITY_CODE,
    CONF_INSEE_EPCI: EPCI_CODE,
    CONF_CITY: "Bordeaux",
}

POLLUTION_ONLY = {
    CONF_INCLUDE_POLLUTION: True,
    CONF_INCLUDE_POLLEN: False,
    CONF_INCLUDE_POLLUTION_FORECAST: False,
    CONF_INCLUDE_POLLEN_FORECAST: False,
}

POLLUTION_AND_POLLEN = {
    CONF_INCLUDE_POLLUTION: True,
    CONF_INCLUDE_POLLEN: True,
    CONF_INCLUDE_POLLUTION_FORECAST: False,
    CONF_INCLUDE_POLLEN_FORECAST: False,
}


def feature(date_ech, **properties):
    """Build one GeoJSON feature as the Atmo France API returns it."""
    props = {
        "date_ech": date_ech,
        "source": "ATMO Nouvelle-Aquitaine",
        "date_maj": f"{date_ech} 09:00:00",
        "type_zone": "commune",
        "lib_zone": "Bordeaux",
        "code_qual": 2,
        "code_no2": 1,
        "code_o3": 2,
        "code_pm10": 2,
        "code_pm25": 3,
        "code_so2": 1,
    }
    props.update(properties)
    return {"properties": props}
