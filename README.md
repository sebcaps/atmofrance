# Atmo France pour Home Assistant

Composant pour exposer les niveaux de pollution prévu pour le jour même.

Données fournies par Atmo France et les agences régionales.
Voir https://www.atmo-france.org/ pour l'accès web.

L'intégration expose les données d'Atmo France pour une commune donnée.
Les données exposés sont :
- Niveau de pollution Dioxide d'Azote (NO<sub>2</sub>)
- Niveau de pollution Ozone (O<sub>3</sub>)
- Niveau de pollution Dioxide de Souffre (SO<sub>2</sub>)
- Niveau de pollution Particules fines <2.5 µm (Pm25)
- Niveau de pollution Particules fines <10 µm (Pm10)
- Niveau global de qualité de l'air.

## Installation

Utilisez [hacs](https://hacs.xyz/).
[![Ouvrez votre instance Home Assistant et ouvrez un référentiel dans la boutique communautaire Home Assistant.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sebcaps&repository=atmofrance&category=integration)

## Configuration

### Obtenir un accès pour les API Atmo France

- Faire une demande de compte sur le [site Atmo France](https://admindata.atmo-france.org/inscription-api),
- Une fois le compte créé, initialiser le mot de passe via le lien envoyé par mail.
- Ces identifiants (login / mot de passe) sont ceux à utiliser pour la configuration du composant dans Home Assistant.

### Configuration dans Home Assistant

La méthode de configuration consiste à utiliser l'interface utilisateur.

Il faut tout d'abord saisir ces [identifiants d'accés](#obtenir-un-accès-pour-les-api-atmo-france) à l'API.

![image info](/img/authent.png)

Puis selectionner le code postal de la commune dont on souhaite obtenir les données.

![image info](/img/location.png)
>**Note:**
>L'API se base sur le code INSEE. La récupération du code INSEE se fait via l'intégration, mais il peut y avoir plusieur communes (donc plusieurs code INSEE) pour un même code postal. Dans ce cas, une étape supplémentaire demande de préciser la commune (sélectionnable dans une liste) pour ne récupérer qu'un code INSEE.

![image info](/img/multiloc.png)

### Données

Les informations présentées sont les niveaux de pollution sur une échelle de 1 (Bon) à 5 (Trés Mauvais).

Le libellé du niveau est présent sous forme d'attribut du sensor. Est également présent dans les attributs, la date et heure (UTC) de la mise à jour des données par AtmoFrance. **Les données sont mise à jour une fois par jour par AtmoFrance**

![image info](/img/attributs.png)