"""
Creates a toy population for Athens by ingesting Travel Survey data into PAM
"""

# %% Import dependencies
from re import T
from athenspop import preprocessing
import os
from datetime import timedelta
import sys
from pathlib import Path
import pandas as pd
import geopandas as gp
import matplotlib.pyplot as plt

from pam import read, write
from pam.plot.stats import plot_activity_times, plot_leg_times
from pam.samplers.spatial import RandomPointSampler
from pam.samplers.population import sample as population_sampler
from pam.samplers.time import apply_jitter_to_plan


sys.path.insert(0, os.path.join(Path(__file__).parent.absolute(), '..'))

# %% User Input
path_survey = '/c/Projects/athenspop/demand_data_NTUA'
path_outputs = '/c/Projects/athenspop/outputs'

total_population = 3.8 * 10**6  # total population of Attica
sample_perc = 0.001  # generate a 0.1% synthetic population

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

# %% resample to match totals target
scale_factor = total_population * sample_perc / len(population)
population = population_sampler(population, scale_factor)
print(population)

# %% apply some jitter
#       (so that not all activities start at xx:00:00)
for hid, pid, person in population.people():
    apply_jitter_to_plan(
        person.plan,
        jitter=timedelta(minutes=30),
        min_duration=timedelta(minutes=10)
    )
    # crop to 24-hours
    person.plan.crop()

# %% some plots
population.random_person().plot()  # plot a random-person diary
plot_activity_times(population)  # activity start times distribution by purpose
plt.savefig(os.path.join(path_outputs, 'activity_times.png'))
plot_leg_times(population)  # leg start times distribution by mode
plt.savefig(os.path.join(path_outputs, 'mode_times.png'))


# %% facility sampling
zones = preprocessing.get_zones(
    path=os.path.join(path_survey, 'shp_zones', 'zones_attica.shp')
)
zones.plot()

# random point-in-polygon sampling
sampler = RandomPointSampler(geoms=zones)
population.sample_locs(sampler)



# %% export
path_out = os.path.join(path_outputs, 'plans.xml')
write.write_matsim(
    population,
    plans_path=path_out,
    comment='Athens example pop'
)
population.to_csv(path_outputs, crs=2100)
print(f'Population exported to {path_out}')