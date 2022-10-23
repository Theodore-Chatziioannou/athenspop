"""
Creates a toy population for Athens by ingesting Travel Survey data into PAM
"""

# %% Import dependencies
import os
import sys
from pathlib import Path

from pam import read, write
from pam.plot.stats import plot_activity_times, plot_leg_times
from pam.samplers.spatial import RandomPointSampler

sys.path.insert(0, os.path.join(Path(__file__).parent.absolute(), '..'))
from athenspop import preprocessing

# %% User Input
path_survey = '/c/Projects/athenspop/demand_data_NTUA'
path_outputs = '/c/Projects/athenspop/outputs'


# %% Ingest travel survey data
survey_raw = preprocessing.read_survey(
    os.path.join(path_survey, 'NEW_diaries_athens_final.csv')
)

# person attributes
person_attributes = preprocessing.get_person_attributes(survey_raw)

# trips dataset
trips = preprocessing.get_trips_table(survey_raw)


# %% create PAM population
population = read.load_travel_diary(
    trips=trips,
    persons_attributes=person_attributes
)

# %% some plots
population.random_person().plot()  # plot a random-person diary
plot_activity_times(population)  # activity start times distribution by purpose
plot_leg_times(population)  # leg start times distribution by mode


# %% facility sampling
zones = preprocessing.get_zones(
    path=os.path.join(path_survey, 'shp_zones', 'zones_attica.shp')
)
zones.plot()

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
