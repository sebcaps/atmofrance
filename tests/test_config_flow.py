"""Tests du parcours de configuration."""
from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.atmofrance.const import (
    CONF_CODE_POSTAL,
    CONF_INCLUDE_POLLEN,
    CONF_INCLUDE_POLLUTION,
    DOMAIN,
)

CREDENTIALS = {CONF_USERNAME: "utilisateur", CONF_PASSWORD: "motdepasse"}
BORDEAUX = [{"code": "33063", "nom": "Bordeaux", "codeEpci": "243300316"}]
GIRONDE = BORDEAUX + [
    {"code": "33281", "nom": "Merignac", "codeEpci": "243300316"}]


def patch_token():
    return patch(
        "custom_components.atmofrance.config_flow."
        "AtmoFranceDataApi.async_get_token")


def patch_insee(communes=BORDEAUX):
    return patch(
        "custom_components.atmofrance.config_flow.INSEEAPI.get_data",
        return_value=communes)


async def start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER})


async def jusqu_aux_indicateurs(hass, communes=BORDEAUX):
    """Déroule authentification puis code postal."""
    result = await start(hass)
    with patch_token():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], CREDENTIALS)
    with patch_insee(communes):
        return await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CODE_POSTAL: "33000"})


# ------------------------------------------------------ enchaînement ----
async def test_le_parcours_demarre_sur_l_authentification(hass):
    result = await start(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_des_identifiants_valides_menent_a_la_localisation(hass):
    result = await start(hass)
    with patch_token():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], CREDENTIALS)

    assert result["step_id"] == "location"


async def test_un_code_postal_a_une_commune_saute_la_selection(hass):
    result = await jusqu_aux_indicateurs(hass)

    assert result["step_id"] == "sensors_type"


async def test_plusieurs_communes_ouvrent_la_selection(hass):
    result = await jusqu_aux_indicateurs(hass, GIRONDE)

    assert result["step_id"] == "multilocation"


# --------------------------------------------------------- création ----
async def test_le_parcours_complet_cree_une_entree(hass):
    result = await jusqu_aux_indicateurs(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_INCLUDE_POLLUTION: True})
    assert result["step_id"] == "forecast_sensor_type"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["INSEE"] == "33063"
    assert result["data"]["INSEE EPCI"] == "243300316"
    assert result["data"]["city"] == "Bordeaux"
    assert result["options"][CONF_INCLUDE_POLLUTION] is True
    assert result["options"][CONF_INCLUDE_POLLEN] is False


async def test_le_titre_de_l_entree_porte_la_commune(hass):
    result = await jusqu_aux_indicateurs(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_INCLUDE_POLLEN: True})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {})

    assert "Bordeaux" in result["title"]


async def test_aucun_indicateur_selectionne_est_refuse(hass):
    result = await jusqu_aux_indicateurs(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "need_one_option"}
