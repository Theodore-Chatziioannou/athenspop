"""
Creates a toy population for Athens by ingesting Travel Survey data into PAM
"""

# %% Import dependencies
import pam
from pam import read, write
from pam.plot.stats import plot_activity_times, plot_leg_times
from pam.samplers.spatial import RandomPointSampler
import pandas as pd
import geopandas as gp
import os
import sys
import re
from pathlib import Path

sys.path.insert(0, os.path.join(Path(__file__).parent.absolute(), '..'))
import athenspop
from athenspop import mappings

# %% User Input
path_survey = '/c/Projects/athenspop/demand_data_NTUA'
path_outputs = '/c/Projects/athenspop/outputs'

# %% Ingest travel survey data
person_attribute_cols = [
    'gender', 'age', 'education', 'employment', 'income',
    'car_own', 'home']
survey_raw = pd.read_csv(os.path.join(
    path_survey, 'NEW_diaries_athens_final.csv'))
print(len(survey_raw))
survey_raw = survey_raw.dropna(subset=['home', 'age'])
survey_raw['home'] = survey_raw['home'].map(int)
survey_raw['age'] = survey_raw['age'].map(int)
print(len(survey_raw))

# %% person attributes
person_attributes = survey_raw[['pid']+person_attribute_cols].copy()

# mappings
person_attributes['gender'] = person_attributes['gender'].map(mappings.gender)
person_attributes['education'] = person_attributes['education'].map(
    mappings.education)
person_attributes['employment'] = person_attributes['employment'].map(
    mappings.employment)
person_attributes['income'] = person_attributes['income'].map(mappings.income)
person_attributes['car_own'] = person_attributes['car_own'].map(
    mappings.car_own)

# rename
person_attributes.rename(
    columns={
        'home': 'hzone'
    },
    inplace=True
)

# %% trips dataset
trips = survey_raw[
    [x for x in survey_raw if x not in person_attribute_cols]
].set_index('pid')

trips.columns = pd.MultiIndex.from_tuples([
    (int(x[-1]), x[:-1]) for x in trips.columns
], names=['seq', ''])
trips = trips.stack(level=0).reset_index().sort_values(['pid', 'seq'])
trips['hid'] = trips['pid']
trips['hzone'] = trips.pid.map(person_attributes.set_index('pid').hzone)
trips['dest'] = trips['dest'].apply(int)
trips['time'] = trips['time'].apply(int)
trips['tst'] = trips['time'] * 60
trips['seq'] = trips['seq'] - 1

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


# %% create PAM population
population = read.load_travel_diary(
    trips=trips,
    persons_attributes=person_attributes
)

# %% some plots
population.random_person().plot()  # plot a diary
plot_activity_times(population)  # activity start times distribution by purpose
plot_leg_times(population)  # leg start times distribution by mode


# %% facility sampling
# read zone data
zones = gp.read_file(os.path.join(
    path_survey, 'shp_zones', 'zones_attica.shp'))
zones[['id', 'name']] = zones['zone_name'].str.split(':', expand=True)
zones['id'] = zones['id'].map(int)
zones.set_index('id', inplace=True)
zones.sort_index(inplace=True)
# TODO: zone 29 (Papagou-Cholargos) is missing from the shapefile

# random point-in-polygon sampling
sampler = RandomPointSampler(geoms=zones)
population.sample_locs(sampler)

# TODO: facility sampling using OSM land use data

# %% export
write.write_matsim(
    population,
    plans_path=os.path.join(path_outputs, 'plans.xml'),
    attributes_path=os.path.join(path_outputs, 'attributes.xml'),
    comment='Athens example pop'
)
