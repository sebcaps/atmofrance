"""Tests de mise en place de l'entrée de configuration."""
from unittest.mock import patch

import aiohttp
import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.atmofrance.const import (
    CONF_INSEE_CODE,
    CONF_INSEE_EPCI,
    CONF_POLLEN_COORDINATOR,
    CONF_POLLUTION_COORDINATOR,
    DOMAIN,
    POLLEN_ALERT_SENSORS,
    POLLEN_CONC_SENSORS,
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
    """Remplace AtmoFranceDataApi, piloté par une table de couverture.

    Une zone absente de la table répond par une liste vide (aucune donnée
    publiée) ; une erreur d'API se simule avec la valeur None, comme le fait
    AtmoFranceDataApi.get_data.
    """

    def __init__(self, coverage):
        self._coverage = coverage
        self.calls = []
        self.has_data = False

    async def get_data(self, code, url_code):
        self.calls.append((code, url_code))
        if isinstance(self._coverage, Exception):
            raise self._coverage
        val = self._coverage.get((code, url_code))
        if isinstance(val, Exception):
            raise val
        return val

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


# ------------------------------------- pollen vide et erreurs d'API ----
async def test_un_flux_pollen_vide_ne_bloque_pas_l_integration(hass):
    """Hors saison, l'API renvoie features: [] pour le pollen (issue #67)."""
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_AND_POLLEN)
    construits = coordinators(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert construits[CONF_POLLUTION_COORDINATOR]._source == CONF_INSEE_CODE
    assert CONF_POLLEN_COORDINATOR in construits


async def test_un_flux_pollen_vide_donne_des_capteurs_pollen_inconnus(hass):
    await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): FEATURES}, POLLUTION_AND_POLLEN)

    etats = hass.states.async_all("sensor")
    nb_pollen = len(POLLEN_ALERT_SENSORS) + len(POLLEN_CONC_SENSORS)
    inconnus = [e for e in etats if e.state == STATE_UNKNOWN]

    assert len(etats) == 6 + nb_pollen
    assert len(inconnus) == nb_pollen
    # Les capteurs de qualité de l'air restent fonctionnels (pas 0 ni unknown).
    assert all(e.state == "2" for e in etats if e.state != STATE_UNKNOWN)


async def test_une_erreur_api_sur_le_pollen_relance_l_initialisation(hass):
    entry = await setup_entry(
        hass,
        {(CITY_CODE, URL_CODE.POLLUTION): FEATURES,
         (CITY_CODE, URL_CODE.POLLEN): None},
        POLLUTION_AND_POLLEN)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_une_erreur_api_sur_la_pollution_relance_l_initialisation(hass):
    entry = await setup_entry(
        hass, {(CITY_CODE, URL_CODE.POLLUTION): None}, POLLUTION_ONLY)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_une_erreur_communale_ne_bascule_pas_sur_l_epci(hass):
    """Une erreur transitoire n'est pas une absence de données."""
    entry = await setup_entry(
        hass,
        {(CITY_CODE, URL_CODE.POLLUTION): None,
         (EPCI_CODE, URL_CODE.POLLUTION): FEATURES},
        POLLUTION_ONLY)

    assert entry.state is ConfigEntryState.SETUP_RETRY


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


async def test_erreur_reseau_declenche_une_nouvelle_tentative(hass):
    """Une coupure réseau ou DNS lors du setup doit demander une nouvelle tentative et nettoyer hass.data."""
    entry = await setup_entry(
        hass, aiohttp.ClientError("DNS failure"), POLLUTION_ONLY)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_la_nouvelle_tentative_apres_erreur_reseau_reussit(hass):
    """Après une erreur réseau, la reconnexion reconstruit bien les coordinateurs sans KeyError."""
    entry = await setup_entry(
        hass, aiohttp.ClientError("DNS failure"), POLLUTION_ONLY)
    assert entry.state is ConfigEntryState.SETUP_RETRY

    with patch_api({(CITY_CODE, URL_CODE.POLLUTION): FEATURES}):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert CONF_POLLUTION_COORDINATOR in coordinators(hass, entry)


# ----------------------------------- indépendance pollution / pollen ----
async def test_le_pollen_n_herite_jamais_de_la_zone_pollution(hass):
    """La pollution résout sur l'EPCI, le pollen n'a de données nulle part.

    La variable source étant partagée, le pollen réutilisait silencieusement
    la zone pollution. Sans données pollen l'intégration reste chargée, et le
    coordinateur pollen se rabat sur la commune, jamais sur la zone pollution.
    """
    entry = await setup_entry(
        hass, {(EPCI_CODE, URL_CODE.POLLUTION): FEATURES},
        POLLUTION_AND_POLLEN)
    construits = coordinators(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert construits[CONF_POLLUTION_COORDINATOR]._source == CONF_INSEE_EPCI
    assert construits[CONF_POLLEN_COORDINATOR]._source == CONF_INSEE_CODE


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

# ---------------------------------------------------------- session ----
async def test_les_clients_partagent_la_session_de_home_assistant(hass):
    """Une session propre au client n'est jamais fermee : elle fuit a chaque
    nouvel essai ConfigEntryNotReady."""
    coverage = {
        (CITY_CODE, URL_CODE.POLLUTION): FEATURES,
        (CITY_CODE, URL_CODE.POLLEN): FEATURES,
    }
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, options=POLLUTION_AND_POLLEN, version=3)
    entry.add_to_hass(hass)
    with patch_api(coverage) as api_class:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    session = async_get_clientsession(hass)
    assert api_class.call_count == 2
    for call in api_class.call_args_list:
        assert call.args[1] is session

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
