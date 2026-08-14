"""Tests de mise en place de l'entrée de configuration."""
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.atmofrance.const import (
    CONF_INSEE_CODE,
    CONF_INSEE_EPCI,
    CONF_POLLEN_COORDINATOR,
    CONF_POLLUTION_COORDINATOR,
    DOMAIN,
    URL_CODE,
)

from .const import (
    CITY_CODE,
    ENTRY_DATA,
    EPCI_CODE,
    POLLUTION_AND_POLLEN,
    POLLUTION_ONLY,
    feature,
)

FEATURES = [feature("2026-07-30")]


class FakeApi:
    """Remplace AtmoFranceDataApi, piloté par une table de couverture."""

    def __init__(self, coverage):
        self._coverage = coverage
        self.calls = []

    async def get_data(self, code, url_code):
        self.calls.append((code, url_code))
        return self._coverage.get((code, url_code))

    def get_key_value(self, key, shift=0):
        return 2

    source = "ATMO Nouvelle-Aquitaine"
    last_update = "2026-07-30 09:00:00"
    type_zone = "commune"
    nom_zone = "Bordeaux"


def patch_api(coverage):
    return patch(
        "custom_components.atmofrance.AtmoFranceDataApi",
        side_effect=lambda *args, **kwargs: FakeApi(coverage),
    )


async def setup_entry(hass, coverage, options):
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, options=options, version=3)
    entry.add_to_hass(hass)
    with patch_api(coverage):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def coordinators(hass, entry):
    return hass.data.get(DOMAIN, {}).get(entry.entry_id, {})


# --------------------------------------------------- résolution de zone ----
async def test_les_donnees_de_la_commune_sont_prioritaires(hass):
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)

    assert entry.state is ConfigEntryState.LOADED
    assert coordinators(hass, entry)[
        CONF_POLLUTION_COORDINATOR]._source == CONF_INSEE_CODE


async def test_repli_sur_l_epci_sans_donnees_communales(hass):
    entry = await setup_entry(
        hass, {(EPCI_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)

    assert entry.state is ConfigEntryState.LOADED
    assert coordinators(hass, entry)[
        CONF_POLLUTION_COORDINATOR]._source == CONF_INSEE_EPCI


async def test_la_commune_est_interrogee_avant_l_epci(hass):
    entry = await setup_entry(
        hass, {(EPCI_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)
    api = coordinators(hass, entry)[CONF_POLLUTION_COORDINATOR].api

    assert api.calls[0][0] == CITY_CODE
    assert api.calls[1][0] == EPCI_CODE


# ------------------------------------------------------ coordinateurs ----
async def test_un_coordinateur_par_indicateur_active(hass):
    coverage = {
        (CITY_CODE, URL_CODE.POLLUTION): FEATURES,
        (CITY_CODE, URL_CODE.POLLEN): FEATURES,
    }
    entry = await setup_entry(hass, coverage, POLLUTION_AND_POLLEN)
    construits = coordinators(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert CONF_POLLUTION_COORDINATOR in construits
    assert CONF_POLLEN_COORDINATOR in construits


async def test_aucun_coordinateur_pollen_si_l_option_est_absente(hass):
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)

    assert CONF_POLLEN_COORDINATOR not in coordinators(hass, entry)


async def test_le_coordinateur_interroge_le_bon_flux(hass):
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)
    api = coordinators(hass, entry)[CONF_POLLUTION_COORDINATOR].api

    assert all(appel[1] is URL_CODE.POLLUTION for appel in api.calls)


# ------------------------------------------------------------ entités ----
async def test_les_capteurs_de_pollution_sont_crees(hass):
    await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)

    assert len(hass.states.async_all("sensor")) == 6


# ---------------------------------------------------------- unload ----
async def test_le_dechargement_libere_l_entree(hass):
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
