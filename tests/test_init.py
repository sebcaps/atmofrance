"""Tests de mise en place de l'entrée de configuration."""
from unittest.mock import patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.update_coordinator import UpdateFailed
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


# ------------------------------------- absence totale de données ----
async def test_sans_aucune_donnee_le_setup_demande_une_nouvelle_tentative(hass):
    """La plateforme sensor plantait sur un KeyError, sans jamais réessayer."""
    entry = await setup_entry(hass, {}, POLLUTION_ONLY)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_un_setup_echoue_ne_laisse_rien_derriere_lui(hass):
    """Sinon la garde sur entry_id ferait sauter la reconstruction."""
    entry = await setup_entry(hass, {}, POLLUTION_ONLY)

    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_la_nouvelle_tentative_aboutit_quand_l_api_repond(hass):
    entry = await setup_entry(hass, {}, POLLUTION_ONLY)
    assert entry.state is ConfigEntryState.SETUP_RETRY

    with patch_api({(CITY_CODE, URL_CODE.POLLUTION): FEATURES}):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED


# ----------------------------------- indépendance pollution / pollen ----
async def test_le_pollen_n_herite_jamais_de_la_zone_pollution(hass):
    """La pollution résout sur l'EPCI, le pollen n'a de données nulle part.

    La variable source étant partagée, le pollen réutilisait silencieusement
    la zone pollution et bâtissait un coordinateur sur une API vide.
    """
    entry = await setup_entry(
        hass, {(EPCI_CODE, URL_CODE.POLLUTION): FEATURES},
        POLLUTION_AND_POLLEN)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert CONF_POLLEN_COORDINATOR not in coordinators(hass, entry)


async def test_chaque_indicateur_resout_sa_propre_zone(hass):
    """La pollution n'est couverte que par l'EPCI, le pollen que par la commune."""
    coverage = {
        (EPCI_CODE, URL_CODE.POLLUTION): FEATURES,
        (CITY_CODE, URL_CODE.POLLEN): FEATURES,
    }
    entry = await setup_entry(hass, coverage, POLLUTION_AND_POLLEN)
    construits = coordinators(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert construits[CONF_POLLUTION_COORDINATOR]._source == CONF_INSEE_EPCI
    assert construits[CONF_POLLEN_COORDINATOR]._source == CONF_INSEE_CODE


# ------------------------------------------ échec réel ou absence de données ----
class FailingApi(FakeApi):
    """La requête elle-même échoue : get_data renvoie None."""

    async def get_data(self, code, url_code):
        return None


class EmptyApi(FakeApi):
    """L'API répond correctement et n'a aucune ligne à donner."""

    async def get_data(self, code, url_code):
        return []


async def test_une_requete_echouee_marque_la_mise_a_jour_en_echec(hass):
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)
    coordinator = coordinators(hass, entry)[CONF_POLLUTION_COORDINATOR]

    coordinator.api = FailingApi({})
    with pytest.raises(UpdateFailed):
        await coordinator._update_method()


async def test_une_reponse_vide_n_est_pas_un_echec(hass):
    """Entre la purge nocturne d'Atmo et sa republication de la mi-journée."""
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)
    coordinator = coordinators(hass, entry)[CONF_POLLUTION_COORDINATOR]

    coordinator.api = EmptyApi({})

    assert await coordinator._update_method() == []


async def test_une_reponse_vide_laisse_le_coordinateur_sain(hass):
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)
    coordinator = coordinators(hass, entry)[CONF_POLLUTION_COORDINATOR]

    coordinator.api = EmptyApi({})
    await coordinator.async_refresh()

    assert coordinator.last_update_success is True


async def test_un_echec_atteint_last_update_success(hass):
    """Le retour False précédent laissait last_update_success à True."""
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)
    coordinator = coordinators(hass, entry)[CONF_POLLUTION_COORDINATOR]

    coordinator.api = FailingApi({})
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    assert isinstance(coordinator.last_exception, UpdateFailed)


async def test_le_coordinateur_renvoie_la_charge_utile(hass):
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_ONLY)
    coordinator = coordinators(hass, entry)[CONF_POLLUTION_COORDINATOR]

    assert await coordinator._update_method() == FEATURES
