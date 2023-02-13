import pandas as pd
from athenspop import mappings
import numpy as np
import geopandas as gp
from shapely.geometry import box
from . import mappings
# import statistic as stat

person_attribute_cols = [
    'gender', 'age', 'education', 'employment', 'income',
    'car_own', 'home']

def read_survey(path: str, cleanup: bool = True) -> pd.DataFrame:
    """
    Read the raw travel survey data

    :param cleanup: Whether to remove some errors such as missing return trips
    """
    survey_raw = pd.read_csv(path)
    print(len(survey_raw))
    survey_raw = survey_raw.dropna(subset=['home', 'age'])
    survey_raw['home'] = survey_raw['home'].map(int)
    survey_raw['age'] = survey_raw['age'].map(int)

    if cleanup:
        survey_raw = step_day(survey_raw)
        survey_raw = market_prob(survey_raw)
        survey_raw = fix_nobackhome(survey_raw)

    print(len(survey_raw))

    return survey_raw


def step_day(df: pd.DataFrame) -> pd.DataFrame:
    """
    This function adds extra 24 (one day), if time i < time i + 1 - next activity
    So, time >= 24 refer to the next day...  
    """
    for i in range(2, 6): 
        df[f'time{i}'] = np.where(df[f'time{i}']<df[f'time{i-1}'], df[f'time{i}'] + 24, df[f'time{i}'])

    return df

def get_durations(df: pd.DataFrame, prp: str) -> pd.Series:
    """
    Estimates duration of activities based on the completed ones.

    :param prp: Reported trip purpose
    """
    sdf =pd.concat(
            [
                df[df[f'purp{i}']==prp][[f'time{i}', f'time{i+1}']].\
                    set_axis(['start_time', 'end_time'], axis=1) \
                    for i in range(1, 5)
            ],
            axis=0,
            ignore_index=True
        )
    return sdf['end_time'] - sdf['start_time']


def prpdur_stat(df: pd.DataFrame) -> pd.DataFrame:
    """
    Estimates mean and standard deviation of duration for each trip purpose

    :param df: Raw trip survey dataframe
    """
    purposes = list(mappings.purpose.keys())
    durations = {prp: get_durations(df, prp) for prp in purposes}
    statdf = pd.DataFrame({
            'prp': k,
            'dur_mean': v.mean(),
            'dur_sd': v.std()
        } for k, v in durations.items()
    ).set_index('prp')
    return statdf

def timeupd(df, i: int, infill: pd.Series, min_duration: int=1):
    """
    Fills missing times from the missing trip.

    :param i: the trip id to update (1-5)
    :param infill: boolean series indicating the trips that need infilling
    :param min_duration: Minimun sampled duration (in hours)
    """
    prp = f'purp{i}'
    tim1 = f'time{i}'
    tim2 = f'time{i+1}'
        
    statdf = prpdur_stat(df) # table with mean and std.dev per purpose
    for item in df.loc[infill].index:
        dur_mean = statdf.loc[statdf.index == df.loc[item, prp], 'dur_mean']
        dur_sd = statdf.loc[statdf.index == df.loc[item, prp], 'dur_sd']
        x = int(np.round(np.random.normal(dur_mean, dur_sd)))
        x = max(x, min_duration)
        df.loc[item, tim2] = df.loc[item, tim1] + x # estimation of new time
    return df[tim2]

def fix_nobackhome(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a return trip home (where it is missing).
    """    
    n_trips = np.select([df[f'dest{i}']>0 for i in range(5, 0, -1)], range(5, 0, -1))
    df['purp6'] = np.nan
    df['mode6'] = np.nan
    df['dest6'] = np.nan
    df['time6'] = np.nan
    for i in range(2, 6):
        j = i + 1
        # check if the return trip is missing
        infill = (n_trips == i) & (df[f'purp{i}'] != '2: return home') & (df[f'purp{i}']  != '5: recreation')
        
        # update next trip's destination, purpose, mode and time
        df[f'dest{j}'] = np.where(infill, df.home, df[f'dest{j}']) # home location to the destinatio
        df[f'purp{j}'] = np.where(infill, '2: return home', df[f'purp{j}'])
        df[f'mode{j}'] = np.where(infill, df[f'mode{i}'], df[f'mode{j}']) # with the same mode he/she returned back
        df[f'time{j}'] = timeupd(df, i, infill)

    return df

def market_prob(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename market activities starting after 21:00 as "other" 
    """
    for i in range(1, 6):
        df[f'purp{i}'] = np.where((df[f'time{i}']>21) & (df[f'purp{i}'] =='4: market'), '7: other', df[f'purp{i}'])

    return df

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
    person_attributes['income_all'] = person_attributes['income'].map(
        mappings.income_all_categories)
    person_attributes['income'] = person_attributes['income'].map(
        mappings.income)
    person_attributes['car_own'] = person_attributes['car_own'].map(
        mappings.car_own)
    person_attributes['age_group'] = person_attributes['age'].map(
        mappings.age_group)
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


def get_trips_table(
    survey_raw: pd.DataFrame,
    filter_next_day: bool = True
    ) -> pd.DataFrame:
    """
    Create the trips table from the raw survey data

    :param filter_next_day: If True, drop any trips happening after the first day.
    """
    trips = survey_raw[
        [x for x in survey_raw if x not in person_attribute_cols]
    ].set_index('pid')

    trips.columns = pd.MultiIndex.from_tuples([
        (int(x[-1]), x[:-1]) for x in trips.columns
    ], names=['seq', ''])
    trips = trips.stack(level=0).reset_index().sort_values(['pid', 'seq']).dropna(subset='mode')
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
    trips['day'] += np.floor(trips['tst']/24/60).round(0).apply(int)

    # if activities happen during the same hour,
    #   distribute them equally
    trips['n_acts_hour'] = trips.groupby(['pid','time','day']).seq.transform(len)
    trips['offset'] = (60 / trips['n_acts_hour'] * trips['seq']).round().map(int)
    trips['tst'] = trips['tst'] + trips['offset']

    # next day activities
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
    # arbitrarily assume 10-minute trips
    # TODO: improve this assumption
    trips['tet'] = trips['tst'] + 10

    # crop any trips that start on the second day
    if filter_next_day:
        trips = trips[trips['day']==0]

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
