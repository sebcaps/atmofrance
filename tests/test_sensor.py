"""Tests des entites capteur."""
import logging

import pytest
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.atmofrance.const import (
    DOMAIN,
    POLLEN_ALERT_SENSORS,
    POLLEN_CONC_SENSORS,
    POLLUTION_LEVEL,
    POLLUTION_SENSORS,
)
from custom_components.atmofrance.sensor import (
    AtmoFrancePollenConcentrationEntity,
    AtmoFrancePollenLevelEntity,
    AtmoFrancePollutionEntity,
)

from .const import ENTRY_DATA, POLLUTION_ONLY

_LOGGER = logging.getLogger(__name__)

PM10 = next(d for d in POLLUTION_SENSORS if d.key == "code_pm10")
AMBROISIE = next(d for d in POLLEN_ALERT_SENSORS if d.key == "code_ambr")
CONC_GRAM = next(d for d in POLLEN_CONC_SENSORS if d.key == "conc_gram")


class StubApi:
    """Renvoie ce qu'on lui a demande de renvoyer."""

    def __init__(self, values):
        self._values = values

    def get_key_value(self, key, shift=0):
        return self._values.get((key, shift), "")

    source = "ATMO Nouvelle-Aquitaine"
    last_update = "2026-07-30 09:00:00"
    type_zone = "commune"
    nom_zone = "Bordeaux"


def make_entity(hass, entity_class, description, values, shift=0):
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, options=POLLUTION_ONLY, version=3)
    entry.add_to_hass(hass)
    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name="test", config_entry=entry)
    coordinator.api = StubApi(values)
    return entity_class(hass, entry, description, coordinator, shift)


# ------------------------------------------------------ valeurs lues ----
@pytest.mark.parametrize("raw", [2, "2", 2.0])
async def test_un_niveau_de_pollution_est_converti_en_entier(hass, raw):
    entity = make_entity(
        hass, AtmoFrancePollutionEntity, PM10, {("code_pm10", 0): raw})
    assert entity.native_value == 2


async def test_un_niveau_de_pollen_flottant_est_converti_en_entier(hass):
    """L'API renvoie les niveaux de pollen en flottants : code_gram = 2.0."""
    entity = make_entity(
        hass, AtmoFrancePollenLevelEntity, AMBROISIE, {("code_ambr", 0): 3.0})
    assert entity.native_value == 3


async def test_une_concentration_garde_sa_precision(hass):
    entity = make_entity(
        hass, AtmoFrancePollenConcentrationEntity, CONC_GRAM,
        {("conc_gram", 0): 8.2})
    assert entity.native_value == 8.2


# --------------------------------------------------------- attributs ----
async def test_les_attributs_traduisent_le_niveau(hass):
    entity = make_entity(
        hass, AtmoFrancePollutionEntity, PM10, {("code_pm10", 0): 4})

    attributs = entity.extra_state_attributes

    assert attributs["Libellé"] == POLLUTION_LEVEL[4]
    assert attributs["Couleur"] == "#ff5050"
    assert attributs["Nom de la zone"] == "Bordeaux"
    assert attributs["Type de zone"] == "commune"


# --------------------------------------------------- identite entites ----
async def test_une_entite_de_prevision_est_distincte_du_jour(hass):
    aujourdhui = make_entity(
        hass, AtmoFrancePollutionEntity, PM10, {("code_pm10", 0): 2})
    demain = make_entity(
        hass, AtmoFrancePollutionEntity, PM10, {("code_pm10", 1): 3}, shift=1)

    assert aujourdhui._attr_unique_id != demain._attr_unique_id
    assert aujourdhui._attr_name != demain._attr_name
    assert demain._attr_name.endswith("J+1")


async def test_le_decalage_selectionne_le_bon_jour(hass):
    entity = make_entity(
        hass, AtmoFrancePollutionEntity, PM10,
        {("code_pm10", 0): 2, ("code_pm10", 1): 5}, shift=1)
    assert entity.native_value == 5


async def test_le_nom_porte_le_libelle_du_capteur(hass):
    entity = make_entity(hass, AtmoFrancePollutionEntity, PM10, {})
    assert PM10.name in entity._attr_name


async def test_l_appareil_est_un_service_attribue_a_atmo(hass):
    entity = make_entity(hass, AtmoFrancePollutionEntity, PM10, {})

    assert entity._attr_device_info["model"] == "Atmo France API"
    assert "Atmo France" in entity._attr_attribution
