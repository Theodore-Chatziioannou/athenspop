import pandas as pd
from athenspop import mappings
import numpy as np
import geopandas as gp
from shapely.geometry import box
from . import mappings
import random

person_attribute_cols = [
    'gender', 'age', 'education', 'employment', 'income',
    'car_own', 'home']

def read_survey(
    path: str, 
    fix_day: bool = True,
    fix_return: bool = True,
    fix_market: bool = True,
    ) -> pd.DataFrame:
    """
    Read the raw travel survey data

    :param cleanup: Whether to remove some errors such as missing return trips
    """
    survey_raw = pd.read_csv(path)
    print(len(survey_raw))
    survey_raw = survey_raw.dropna(subset=['home', 'age'])
    survey_raw['home'] = survey_raw['home'].map(int)
    survey_raw['age'] = survey_raw['age'].map(int)

    if fix_day: survey_raw = step_day(survey_raw)
    if fix_return: survey_raw = fix_nobackhome(survey_raw, duration_distribution='empirical')
    if fix_market: survey_raw = fix_market_window(survey_raw)
    
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

def get_durations(df: pd.DataFrame, prp: str) -> pd.DataFrame:
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
    sdf['duration'] = sdf['end_time'] - sdf['start_time']
    return sdf


def prpdur_stat(df: pd.DataFrame) -> pd.DataFrame:
    """
    Estimates mean and standard deviation of duration for each trip purpose

    :param df: Raw trip survey dataframe
    """
    purposes = list(mappings.purpose.keys())
    durations = {prp: get_durations(df, prp)['duration'] for prp in purposes}
    statdf = pd.DataFrame({
            'prp': k,
            'dur_mean': v.mean(),
            'dur_sd': v.std()
        } for k, v in durations.items()
    ).set_index('prp')
    return statdf


def create_duration_sampler_gaussian(df: pd.DataFrame, **kwargs):
    statdf = prpdur_stat(df)
    def sample(purp, *args, **kwargs):
        dur_mean = statdf.loc[purp, 'dur_mean']
        dur_sd = statdf.loc[purp, 'dur_sd']
        x = int(np.round(np.random.normal(dur_mean, dur_sd)))
        return x
    return sample


def get_durations_ecdf(df, time_period_hours=6) -> pd.Series:
    """
    Get the empirical cumulative distribution of durations,
        for each purpose and time period
    
    :param time_period_hours: how many hours in each time period
    """
    durations = []
    for purp in mappings.purpose.keys():
        durations.append(
            get_durations(df, purp).dropna().applymap(int).assign(purp=purp)
        )
    durations = pd.concat(durations, axis=0)
    # durations['purp'] = durations['purp'].map(mappings.purpose)
    durations['start_period'] = durations['start_time'] // time_period_hours
    durations = pd.concat([durations, durations.assign(start_period='total')])

    ecdf = durations.groupby(['purp','start_period'])['duration'].\
            apply(lambda x: x.value_counts(normalize=True).sort_index().cumsum())

    return ecdf

def create_duration_sampler_empirical(df: pd.DataFrame, time_period_hours=6):
    ecdf = get_durations_ecdf(df, time_period_hours=time_period_hours)

    def interpolate(x, ecdf, purp, start_period, min_duration=1):
        if (purp, start_period) not in ecdf.index:
            start_period = 'total'

        ys = [0] + list(ecdf.loc[purp, start_period].index)
        xs = [0] + list(ecdf.loc[purp, start_period].values)
        duration = np.interp(x, xs, ys)
        duration = max(duration, min_duration)
        return duration

    def sample_duration(purp, hour):
        time_period = hour // time_period_hours
        return interpolate(random.random(), ecdf, purp, time_period)

    return sample_duration

def create_duration_sampler(df, distribution='gaussian'):
    if distribution == 'gaussian':
        return create_duration_sampler_gaussian(df)
    elif distribution == 'empirical':
        return create_duration_sampler_empirical(df)
    else:
        raise ValueError('Please provide a valid sampler type')

def timeupd(df, duration_sampler, i: int, infill: pd.Series, min_duration: int=1) -> None:
    """
    Fills missing times from the missing trip.

    :param i: the trip sequence to update (1-5)
    :param infill: boolean series indicating the trips that need infilling
    :param min_duration: Minimun sampled duration (in hours)
    """    
    for idx, values in df.loc[infill].iterrows():
        prp = values[f'purp{i}']
        start_time = values[f'time{i}']

        # sample new duration
        duration = duration_sampler(prp, start_time)
        duration = max(duration, min_duration)

        df.loc[idx, f'time{i+1}']  = start_time + duration

def fix_nobackhome(df: pd.DataFrame, duration_distribution='empirical') -> pd.DataFrame:
    """
    Add a return trip home (where it is missing).
    """
    duration_sampler = create_duration_sampler(df, duration_distribution)    
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
        timeupd(df, duration_sampler, i, infill)

    return df

def fix_market_window(df: pd.DataFrame) -> pd.DataFrame:
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
    # TODO: if two activities happen during the same hour, apply some offset
    trips['same_hour'] = trips.groupby('pid', group_keys=False)['time'].apply(
        lambda x: (x == x.shift(1))
    )
    offset = lambda x: (60/len(x)*x.cumsum()).round().map(int)
    trips['offset'] = trips.groupby(['pid','time','day']).same_hour.transform(offset)
    trips['tst'] = trips['tst'] + trips['offset']

    # next day activities
    trips['tst'] = trips['tst'] + trips['day'] * 24 * 60

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
