import pandas as pd
from athenspop import mappings
import numpy as np
import geopandas as gp
from shapely.geometry import box
import statistic as stat

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

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def nights(df):
    # this function add extra 24 (one day), if time i < time i + 1 - next activity
    # so time >= 24 refer to the next day...
    df["time2"] = np.where(df.time2<df.time1, df.time2 + 24, df.time2)
    df["time3"] = np.where(df.time3<df.time2, df.time3 + 24, df.time3)
    df["time4"] = np.where(df.time4<df.time3, df.time4 + 24, df.time4)
    df["time5"] = np.where(df.time5<df.time4, df.time4 + 24, df.time5)
    return(df)

def prpdur_est(df, prp):
    # this function estimates duration of activities based on the completed ones
    # it saves them in a dataframe
    sdf = pd.DataFrame({'purp': prp,'beftime': df.loc[(df.purp1 == prp), 'time1'],
                              'afttime':  df.loc[(df.purp1 == prp), 'time2']})
    sdf = pd.concat([sdf, pd.DataFrame({'purp': prp,'beftime': df.loc[(df.purp2 == prp), 'time2'],
                              'afttime':  df.loc[(df.purp2 == prp), 'time3']})])
    sdf = pd.concat([sdf, pd.DataFrame({'purp': prp,'beftime': df.loc[(df.purp3 == prp), 'time3'],
                              'afttime':  df.loc[(df.purp3 == prp), 'time4']})])
    sdf = pd.concat([sdf, pd.DataFrame({'purp': prp,'beftime': df.loc[(df.purp4 == prp), 'time4'],
                              'afttime':  df.loc[(df.purp4 == prp), 'time5']})])
    sdf['dur'] = sdf.afttime - sdf.beftime
    sdf = sdf.dropna()
    return sdf

def prpdur_stat(df):
    # estimate mean and std.dev per trip puropose
    statdf = pd.DataFrame({'prp': ['1: work', '2: return home', '3: education',
                               '4: market', '5: recreation', '6: service', '7: other']}) # here we may replace it with mappings
    statdf = statdf.set_index('prp')
    for item in statdf.index:
        statdf.loc[item, "durmean"] = stat.mean(prpdur_est(df, item).dur) 
        statdf.loc[item, "dursd"] = stat.stdev(prpdur_est(df, item).dur)
    return statdf

def timeupd(xcheck, df):
    # this function fill missing times from the missing link
    if xcheck == "x2": # if trip 2 is the last one without returning home
        prp = "purp2" # then save the purpose 2 and time 2.
        tim1 = "time2"
        tim2 = "time3" # to estimate time 3, where you return home
    elif xcheck == "x3":
        prp = "purp3"
        tim1 = "time3"
        tim2 = "time4"
    elif xcheck == "x4":
        prp = "purp4"
        tim1 = "time4"
        tim2 = "time5"
    elif xcheck == "x5":
        prp = "purp5"
        tim1 = "time5"
        tim2 = "time6"
        
    statdf = prpdur_stat(df) # table with mean and std.dev per purpose
    for item in df.loc[df[xcheck] == True].index:
        x = int(np.round(np.random.normal(statdf.loc[statdf.index == df.loc[item, prp], 'durmean'],
                         statdf.loc[statdf.index == df.loc[item, prp], 'dursd'])))
        # it needs to be an integer value
        x = abs(x) # we keep only the positive, but it does not matter after the time upd in the beggining
        if x == 0: x = 1 # if you draw zero, plus one
        df.loc[item, tim2] = df.loc[item, tim1] + x # estimatio of new time
    return df[tim2]

def fix_nobackhome(df):
    x = 4
    
    df['ntrips'] = np.where(df.dest5>0,5,np.where(df.dest4>0, 4, np.where(df.dest3>0,3, np.where(df.dest2>0,2, np.where(df.dest1>0,1,0)))))
    df = df.set_index("pid")
    df["x2"] = (df.ntrips == 2) & (df.purp2 != '2: return home') & (df.purp2 != '5: recreation') # return home purpose
    df.dest3 = np.where(df.x2 == True, df.home, df.dest3) # home location to the destinatio
    df.purp3 = np.where(df.x2 == True, '2: return home', df.purp3)
    df.mode3 = np.where(df.x2 == True, df.mode2, df.mode3) # with the same mode he/she returned back
    df.time3 = timeupd("x2", df)
    
    df["x3"] = (df.ntrips == 3) & (df.purp3 != '2: return home') & (df.purp3 != '5: recreation')
    df.dest4 = np.where(df.x3 == True, df.home, df.dest4)
    df.purp4 = np.where(df.x3 == True, '2: return home', df.purp4)
    df.mode4 = np.where(df.x3 == True, df.mode3, df.mode4)
    df.time4 = timeupd("x3", df)
    
    df["x4"] = (df.ntrips == 4) & (df.purp4 != '2: return home') & (df.purp4 != '5: recreation') # this is per trip
    df.dest5 = np.where(df.x4 == True, df.home, df.dest5)
    df.purp5 = np.where(df.x4 == True, '2: return home', df.purp5)
    df.mode5 = np.where(df.x4 == True, df.mode4, df.mode5)
    df.time5 = timeupd("x4", df)
    
    df["x5"] = (df.ntrips == 5) & (df.purp5 != '2: return home') & (df.purp5 != '5: recreation') # this is per trip
    df["purp6"] = np.where(df.x5 == True, '2: return home', np.nan)
    df["dest6"] = np.where(df.x5 == True, df.home, np.nan)
    df["mode6"] = np.where(df.x5 == True, df.mode5, np.nan)
    df["time6"] = np.where(df.x5 == True, df.time5 + x, np.nan)
    df['time6'] = timeupd("x5", df)
    # df['prob'] = np.where((df.x5 == True) | (df.x4 == True) | (df.x3 == True) | (df.x2 == True), 1, 0) # this is the column with problematic data
    df = df.drop(columns = ['x2', 'x3', 'x4', 'x5', 'ntrips'])

    return df

def market_prob(df):
    df.purp1 = np.where((df.time1>21) & (df.purp1 =='4: market'), '7: other', df.purp1)
    df.purp2 = np.where((df.time2>21) & (df.purp2 =='4: market'), '7: other', df.purp2)
    df.purp3 = np.where((df.time3>21) & (df.purp3 =='4: market'), '7: other', df.purp3)
    df.purp4 = np.where((df.time4>21) & (df.purp4 =='4: market'), '7: other', df.purp4)
    df.purp5 = np.where((df.time5>21) & (df.purp5 =='4: market'), '7: other', df.purp5)
    return df


#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

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
