# %% Import dependencies
from athenspop import preprocessing
import os
from datetime import timedelta
from typing import Optional
import geopandas as gp
import pandas as pd
from pam import read, write
from pam.samplers.spatial import RandomPointSampler
from pam.samplers.facility import FacilitySampler
from pam.samplers.population import sample as population_sampler
from pam.samplers.time import apply_jitter_to_plan


def create_population(
    path_survey: str,
    path_outputs: str,
    path_facilities: Optional[str],
    total_population=3.8 * 10**6,  # total population of Attica
    sample_perc=0.001,  # generate a 0.1% synthetic population
):
    """
    Create a PAM population from the NTUA travel survey data.

    :param path_survey: path to the NTUA travel survey dataset
    :param outputs: path to the output population.xml file
    :param path_facilities: path to the facility (land use) dataset
    :param total_population: population target 
    :param sample_perc: population percentage to generate.
        (for example, use sample_perc = 0.001 to create a 0.1% sample synthetic population)

    """
    # Ingest travel survey data
    survey_raw = preprocessing.read_survey(
        os.path.join(path_survey, 'NEW_diaries_athens_final.csv')
    )
    person_attributes = preprocessing.get_person_attributes(survey_raw)
    trips = preprocessing.get_trips_table(survey_raw)

    # create PAM population
    population = read.load_travel_diary(
        trips=trips,
        persons_attributes=person_attributes
    )

    # resample to match totals target
    scale_factor = total_population * sample_perc / len(population)
    population = population_sampler(population, scale_factor)
    print(population)

    # apply some jitter (so that not all activities start at xx:00:00)
    for hid, pid, person in population.people():
        apply_jitter_to_plan(
            person.plan,
            jitter=timedelta(minutes=30),
            min_duration=timedelta(minutes=10)
        )
        # crop to 24-hours
        person.plan.crop()

    # facility sampling
    zones = preprocessing.get_zones(
        path=os.path.join(path_survey, 'shp_zones', 'zones_attica.shp')
    )
    zones.plot()

    if path_facilities is not None:
        # land-use facility sampling
        facilities = gp.read_file(path_facilities)
        facilities = facilities.set_crs(epsg=2100, allow_override=True)
        for act_name in ['recreation', 'service']:
            facilities = pd.concat([
                facilities,
                facilities[facilities.activity == 'other'].assign(
                    activity=act_name)
            ], axis=0, ignore_index=True)
        sampler = FacilitySampler(facilities, zones)
        population.sample_locs(sampler)

    else:
        # random point-in-polygon sampling
        sampler = RandomPointSampler(geoms=zones)
        population.sample_locs(sampler)

    # export
    path_out = os.path.join(path_outputs, 'plans.xml')
    write.write_matsim(
        population,
        plans_path=path_out,
        comment='Athens example pop'
    )
    population.to_csv(path_outputs, crs=2100)
    print(f'Population exported to {path_out}')
