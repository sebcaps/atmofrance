import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import callback

from .const import (
    DOMAIN,
    TITLE,
    CONF_INSEE_CODE,
    CONF_CODE_POSTAL,
    CONF_CITY,
    CONF_INSEE_EPCI,
    CONF_INCLUDE_POLLEN,
    CONF_INCLUDE_POLLEN_FORECAST,
    CONF_INCLUDE_POLLUTION,
    CONF_INCLUDE_POLLUTION_FORECAST,
)
from .api import AtmoFranceDataApi, INSEEAPI

_LOGGER = logging.getLogger(__name__)

AUTHENT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME, default=""): cv.string,
        vol.Required(CONF_PASSWORD, default=""): cv.string,
    }
)
ZIPCODE_SCHEMA = vol.Schema(
    {vol.Required(CONF_CODE_POSTAL, default=""): cv.string})


INCLUDED_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_INCLUDE_POLLUTION): selector.BooleanSelector(),
        vol.Optional(CONF_INCLUDE_POLLEN): selector.BooleanSelector(),
    }
)

INCLUDED_FORECAST_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_INCLUDE_POLLUTION_FORECAST): selector.BooleanSelector(),
        vol.Optional(CONF_INCLUDE_POLLEN_FORECAST): selector.BooleanSelector(),
    }
)


async def validate_credentials(hass: HomeAssistant, data: dict) -> None:
    """Validate user credential to access API"""
    session = async_get_clientsession(hass)
    try:
        client = AtmoFranceDataApi(data, session, hass=hass)
        await client.async_get_token()
    except ValueError as exc:
        raise exc


async def get_insee_code(hass: HomeAssistant, data: dict) -> None:
    """Get Insee code from zip code"""
    session = async_get_clientsession(hass)
    try:
        client = INSEEAPI(session)
        return await client.get_data(data)
    except ValueError as exc:
        raise exc


def _build_place_key(city) -> str:
    return f"{city['code']};{city['nom']};{city['codeEpci']}"


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AirAtmo."""
    VERSION = 3

    def __init__(self):
        """Initialize"""
        self.data = None
        self.option = {}
        self._init_info = {}
        self.city_insee = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Return Option handler."""
        return ConfigOptionFlowHandler(config_entry)

    @callback
    def _show_setup_form(self, step_id=None, user_input=None, schema=None, errors=None):
        """Show the setup form to the user."""

        if user_input is None:
            user_input = {}

        return self.async_show_form(
            step_id=step_id,
            data_schema=schema,
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        _LOGGER.debug("in async_step_user !!")
        if user_input is not None:
            try:
                await validate_credentials(self.hass, user_input)
            except ValueError:
                errors["base"] = "auth"
            if not errors:
                self.data = user_input
                return await self.async_step_location()
        return self._show_setup_form("user", user_input, AUTHENT_SCHEMA, errors)

    async def async_step_location(self, user_input=None):
        """Handle location step"""
        errors = {}
        _LOGGER.debug("in async_step_location !!")
        if user_input is not None:
            city_insee = user_input.get(CONF_INSEE_CODE)
            if not city_insee:
                # get INSEE Code
                try:
                    self.city_insee = await get_insee_code(
                        self.hass, user_input[CONF_CODE_POSTAL]
                    )
                except ValueError:
                    errors["base"] = "noinsee"
                if not errors:
                    return await self.async_step_multilocation()
                else:
                    return self._show_setup_form(
                        "location", user_input, ZIPCODE_SCHEMA, errors
                    )
            return await self.async_step_sensors_type()
        return self._show_setup_form("location", None, ZIPCODE_SCHEMA, errors)

    async def async_step_multilocation(self, user_input=None):
        """Handle location step"""
        errors = {}
        locations_for_form = {}
        for city in self.city_insee:
            locations_for_form[_build_place_key(city)] = f"{city['nom']}"

        if not user_input:
            if len(self.city_insee) > 1:
                return self.async_show_form(
                    step_id="multilocation",
                    data_schema=vol.Schema(
                        {
                            vol.Required("city", default=[]): vol.In(
                                locations_for_form
                            ),
                        }
                    ),
                    errors=errors,
                )
            user_input = {CONF_CITY: _build_place_key(self.city_insee[0])}

        city_infos = user_input[CONF_CITY].split(";")
        self.data[CONF_INSEE_CODE] = city_infos[0]
        self.data[CONF_CITY] = city_infos[1]
        self.data[CONF_INSEE_EPCI] = city_infos[2]
        return await self.async_step_location(self.data)

    async def async_step_sensors_type(self, user_input=None):
        """Handle sensor step"""
        errors = {}
        if user_input is not None:
            if not (user_input.get(CONF_INCLUDE_POLLUTION) or user_input.get(CONF_INCLUDE_POLLEN)):
                errors["base"] = "need_one_option"
            else:
                self.option[CONF_INCLUDE_POLLUTION] = True if user_input.get(
                    CONF_INCLUDE_POLLUTION) is not None else False
                self.option[CONF_INCLUDE_POLLEN] = True if user_input.get(
                    CONF_INCLUDE_POLLEN) is not None else False
                return await self.async_step_forecast_sensor_type()
        return self._show_setup_form("sensors_type", user_input, INCLUDED_SENSOR_SCHEMA, errors)

    async def async_step_forecast_sensor_type(self, user_input=None):
        """Handle forecat sensor step"""
        errors = {}
        if user_input is not None:
            self.option[CONF_INCLUDE_POLLUTION_FORECAST] = True if user_input.get(
                CONF_INCLUDE_POLLUTION_FORECAST) is not None else False
            self.option[CONF_INCLUDE_POLLEN_FORECAST] = True if user_input.get(
                CONF_INCLUDE_POLLEN_FORECAST) is not None else False
            return self.async_create_entry(
                title=f"{TITLE} - {self.data.get(CONF_CITY)}", data=self.data, options=self.option
            )
        return self._show_setup_form("forecast_sensor_type", user_input, INCLUDED_FORECAST_SENSOR_SCHEMA, errors)


class ConfigOptionFlowHandler(OptionsFlow):
    """Handle a update flow for AirAtmo."""

    def __init__(self, config_entry):
        """Initialize"""
        self.newOption = {}

    async def async_step_init(self, user_input) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            if not (user_input.get(CONF_INCLUDE_POLLUTION) or user_input.get(CONF_INCLUDE_POLLEN)):
                errors["base"] = "need_one_option"
            else:
                self.newOption[CONF_INCLUDE_POLLUTION] = user_input.get(
                    CONF_INCLUDE_POLLUTION)
                self.newOption[CONF_INCLUDE_POLLEN] = user_input.get(
                    CONF_INCLUDE_POLLEN)
                return await self.async_step_forecast()

        return self.async_show_form(step_id="init", data_schema=self.add_suggested_values_to_schema(INCLUDED_SENSOR_SCHEMA, self.config_entry.options), errors={})

    async def async_step_forecast(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            self.newOption[CONF_INCLUDE_POLLUTION_FORECAST] = user_input.get(
                CONF_INCLUDE_POLLUTION_FORECAST)
            self.newOption[CONF_INCLUDE_POLLEN_FORECAST] = user_input.get(
                CONF_INCLUDE_POLLEN_FORECAST)
            return self.async_create_entry(title=self.config_entry.title, data=self.newOption)

        return self.async_show_form(step_id="forecast", data_schema=self.add_suggested_values_to_schema(INCLUDED_FORECAST_SENSOR_SCHEMA, self.config_entry.options), errors={})
