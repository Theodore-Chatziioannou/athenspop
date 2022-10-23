import pandas as pd
from athenspop import mappings
import numpy as np
import geopandas as gp
from shapely.geometry import box


person_attribute_cols = [
    'gender', 'age', 'education', 'employment', 'income',
    'car_own', 'home']


def read_survey(path: str) -> pd.DataFrame:
    """
    Read the raw travel survey data
    """
    survey_raw = pd.read_csv(path)
    print(len(survey_raw))
    survey_raw = survey_raw.dropna(subset=['home', 'age'])
    survey_raw['home'] = survey_raw['home'].map(int)
    survey_raw['age'] = survey_raw['age'].map(int)
    print(len(survey_raw))

    return survey_raw


def get_person_attributes(survey_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Extract the person attributes table from the survey
    """
    person_attributes = survey_raw[['pid']+person_attribute_cols].copy()

    # mappings
    person_attributes['gender'] = person_attributes['gender'].map(
        mappings.gender)
    person_attributes['education'] = person_attributes['education'].map(
        mappings.education)
    person_attributes['employment'] = person_attributes['employment'].map(
        mappings.employment)
    person_attributes['income'] = person_attributes['income'].map(
        mappings.income)
    person_attributes['car_own'] = person_attributes['car_own'].map(
        mappings.car_own)
    person_attributes['freq'] = 1

    # rename
    person_attributes.rename(
        columns={
            'home': 'hzone'
        },
        inplace=True
    )

    # zone 29 (Papagou-Cholargos) is missing from the shapefile
    # -> use zone 35 instead
    #    (Chalandri, Agia Paraskeyi, Gerakas, Cholargos, Papagou, ...)
    person_attributes['hzone'] = np.where(
        person_attributes['hzone'] == 29, 35,
        person_attributes['hzone']
    )

    return person_attributes


def get_trips_table(survey_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Create the trips table from the raw survey data
    """
    trips = survey_raw[
        [x for x in survey_raw if x not in person_attribute_cols]
    ].set_index('pid')

    trips.columns = pd.MultiIndex.from_tuples([
        (int(x[-1]), x[:-1]) for x in trips.columns
    ], names=['seq', ''])
    trips = trips.stack(level=0).reset_index().sort_values(['pid', 'seq'])
    trips['hid'] = trips['pid']
    trips['hzone'] = trips.pid.map(survey_raw.set_index('pid')['home'])
    trips['dest'] = trips['dest'].apply(int)
    trips['time'] = trips['time'].apply(int)
    trips['tst'] = trips['time'] * 60
    trips['seq'] = trips['seq'] - 1
    trips['freq'] = 1

    # zone 29 (Papagou-Cholargos) is missing from the shapefile
    # -> use zone 35 instead
    #    (Chalandri, Agia Paraskeyi, Gerakas, Cholargos, Papagou, ...)
    trips['dest'] = np.where(trips['dest'] == 29, 35, trips['dest'])
    trips['hzone'] = np.where(trips['hzone'] == 29, 35, trips['hzone'])

    # mappings
    trips['mode'] = trips['mode'].map(mappings.modes)
    trips['purp'] = trips['purp'].map(mappings.purpose)

    # some sequences happen during the next day
    trips['day'] = trips.groupby('pid', group_keys=False)['tst'].apply(
        lambda x: (x < x.shift(1)).cumsum()
    )
    # TODO: distribute trip times within the hour
    trips['tst'] = trips['tst'] + trips['day'] * 24 * 60

    # TODO: if two activities happen during the same hour, apply some offset
    trips['same_hour'] = trips.groupby('pid', group_keys=False)['tst'].apply(
        lambda x: (x == x.shift(1))
    )

    # rename fields
    trips.rename(
        columns={
            'dest': 'dzone'
        },
        inplace=True
    )

    # add origin zone
    trips['ozone'] = trips.groupby('pid').apply(
        lambda x: x['dzone'].shift(1)
    ).values
    trips['ozone'] = trips.ozone.fillna(trips.hzone).apply(int)

    # trip start time
    # arbitrarily assume 30-minute trips
    # TODO: improve this assumption
    trips['tet'] = trips['tst'] + 30

    return trips


def create_external_zone() -> gp.GeoDataFrame:
    """
    Create a dummy external zone north of Attica
    """
    external_zone = gp.GeoDataFrame(
        {
            'zone_name': '36:external',
            'type': 'external',
            'name': 'external'
        },
        index=[36],
        geometry=[box(*[480000, 4250000, 485000, 4255000])]
    )
    return external_zone


def get_zones(path: str) -> gp.GeoDataFrame:
    """
    Get the Attica zoning shapefile
    """
    zones = gp.read_file(path)
    zones[['id', 'name']] = zones['zone_name'].str.split(':', expand=True)
    zones['id'] = zones['id'].map(int)
    zones.set_index('id', inplace=True)
    zones.sort_index(inplace=True)

    # append an external zone
    external_zone = create_external_zone()
    zones = pd.concat([zones, external_zone], axis=0)

    return zones
