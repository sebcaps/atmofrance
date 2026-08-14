"""Tests unitaires de AtmoFranceDataApi.

La session HTTP est simulée plutôt que mockée au niveau du transport : ces
tests portent sur le comportement de l'API, pas sur le format de la requête.
"""
from datetime import datetime
from types import SimpleNamespace

import pytest

from custom_components.atmofrance.api import (
    AtmoFranceDataApi,
    INSEEAPI,
    TooManyRequestsError,
)
from custom_components.atmofrance.const import URL_CODE

from .const import ENTRY_DATA, feature

FAKE_HASS = SimpleNamespace(config=SimpleNamespace(time_zone="Europe/Paris"))
TODAY = datetime.now().strftime("%Y-%m-%d")


class Response:
    def __init__(self, status, body, headers=None):
        self.status = status
        self._body = body
        self.headers = headers or {}

    async def json(self):
        return self._body


class FakeSession:
    def __init__(self, login=None, get=None):
        self._login = login or Response(200, {"token": "un-token"})
        self._get = get or Response(200, {"features": [feature(TODAY)]})
        self.posts = 0
        self.gets = 0

    async def post(self, url, json=None, **kwargs):
        self.posts += 1
        return self._login

    async def get(self, url, headers=None, **kwargs):
        self.gets += 1
        return self._get


def build(login=None, get=None):
    session = FakeSession(login, get)
    return AtmoFranceDataApi(ENTRY_DATA, session, hass=FAKE_HASS), session


# ----------------------------------------------------- authentification ----
async def test_le_token_est_recupere_et_conserve():
    api, session = build()
    await api.async_get_token()
    assert api._token == "un-token"
    assert session.posts == 1


async def test_un_429_leve_too_many_requests():
    api, _ = build(login=Response(429, {}, {"Retry-After": "60"}))
    with pytest.raises(TooManyRequestsError):
        await api.async_get_token()


@pytest.mark.parametrize("status", [401, 403, 500, 503])
async def test_un_login_refuse_leve_connection_refused(status):
    api, _ = build(login=Response(status, {}))
    with pytest.raises(ConnectionRefusedError):
        await api.async_get_token()


# ------------------------------------------------ recuperation des donnees ----
async def test_une_reponse_nominale_renvoie_les_features():
    api, _ = build()
    data = await api.get_data("33063", URL_CODE.POLLUTION)
    assert isinstance(data, list)
    assert len(data) == 1


async def test_les_metadonnees_sont_exposees():
    api, _ = build()
    await api.get_data("33063", URL_CODE.POLLUTION)
    assert api.source == "ATMO Nouvelle-Aquitaine"
    assert api.nom_zone == "Bordeaux"
    assert api.type_zone == "commune"
    assert api.last_update


async def test_un_jeu_de_resultats_vide_renvoie_une_liste_vide():
    api, _ = build(get=Response(200, {"features": []}))
    assert await api.get_data("33063", URL_CODE.POLLUTION) == []


async def test_les_metadonnees_sont_vides_avant_toute_requete():
    api, _ = build()
    assert api.source == ""
    assert api.nom_zone == ""


# ------------------------------------------------------- get_key_value ----
async def test_get_key_value_lit_la_valeur_du_jour():
    api, _ = build()
    await api.get_data("33063", URL_CODE.POLLUTION)
    assert api.get_key_value("code_pm10") == 2
    assert api.get_key_value("code_qual") == 2


async def test_get_key_value_renvoie_vide_pour_une_date_absente():
    """Le J+1 n'est publie qu'en cours de journee."""
    api, _ = build()
    await api.get_data("33063", URL_CODE.POLLUTION)
    assert api.get_key_value("code_pm10", 1) == ""


async def test_get_key_value_renvoie_vide_sans_donnees():
    api, _ = build()
    assert api.get_key_value("code_pm10") == ""


# --------------------------------------------------------------- INSEE ----
async def test_insee_renvoie_les_communes():
    communes = [{"code": "33063", "nom": "Bordeaux", "codeEpci": "243300316"}]
    api = INSEEAPI(FakeSession(get=Response(200, communes)))
    assert await api.get_data("33000") == communes


async def test_insee_leve_sur_un_code_postal_inconnu():
    api = INSEEAPI(FakeSession(get=Response(200, [])))
    with pytest.raises(ValueError):
        await api.get_data("00000")


async def test_insee_leve_sur_une_erreur_http():
    api = INSEEAPI(FakeSession(get=Response(500, {})))
    with pytest.raises(ValueError):
        await api.get_data("33000")
