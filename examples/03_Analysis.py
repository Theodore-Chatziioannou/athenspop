"""
Exploration of the diary data
"""

#%% import dependencies
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from athenspop import preprocessing

# %%
path_survey = '/c/Projects/athenspop/demand_data_NTUA'
path_outputs = '/c/Projects/athenspop/outputs'

survey_raw = preprocessing.read_survey(
    os.path.join(path_survey, 'NEW_diaries_athens_final.csv')
)
person_attributes = preprocessing.get_person_attributes(survey_raw)
trips = preprocessing.get_trips_table(survey_raw)

df = pd.merge(trips, person_attributes, on='pid')

# %% number of trips distribution by income
def n_trips_distribution(df: pd.DataFrame, groupby: str = 'income') -> None:
    """
    Distribution of the number of trips by demographic group
    """

    df.groupby(groupby).pid.value_counts().\
            groupby(level=groupby).value_counts(normalize=True).\
            sort_index().groupby(groupby).cumsum().unstack(level=groupby).\
            plot(marker='o')
    plt.xlabel('Number of trips')
    plt.ylabel('Cumulative frequency')
    plt.ylim(0,1)
    plt.xlim(1,4)
    plt.grid()
    plt.show()

n_trips_distribution(df, 'income')
n_trips_distribution(df, 'income_all')
n_trips_distribution(df, 'age_group')
n_trips_distribution(df, 'gender')

#%% correlations between variables
# age vs income
df.groupby('age_group').income.value_counts(normalize=True).\
    unstack(level='income')[['zero', 'low', 'medium','high']].\
    style.format('{:,.0%}')

# %% trip start hour by income group
df.groupby('income')['time'].value_counts().unstack(level='income').\
    plot(kind='bar', stacked=True)
plt.title('Number of trips by hour and income group')

# %% as above, line plot
for income_group in ['low', 'medium', 'high']:
    df[df.income==income_group]['time'].\
        value_counts(normalize=True).sort_index().plot()
plt.grid()
plt.legend(['low', 'medium', 'high'])
plt.title('% of trips by hour')
plt.show()

#%% purpose by income group
df.groupby('income').purp.value_counts(normalize=True).\
        unstack(level='purp').\
        style.format('{:,.0%}')