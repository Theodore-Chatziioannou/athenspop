"""
Simple clustering analysis
"""

# %% Import dependencies
import os
from pathlib import Path
sys.path.insert(0, os.path.join(Path(__file__).parent.absolute(), '..'))

from athenspop import preprocessing
import sys
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.ticker as mtick
from pam import read
from pylab import cm
from Levenshtein import ratio, hamming
import numpy as np
from sklearn.cluster import AgglomerativeClustering
import random
import sklearn.metrics as sm
from typing import List
import matplotlib
import statsmodels.api as stm

import biogeme
import biogeme.database as db
import biogeme.biogeme as bio
import biogeme.models as models
from biogeme.expressions import Beta


# %% User Input
path_survey = '/c/Projects/athenspop/demand_data_NTUA'
path_facilities = '/c/Projects/athenspop/osm/facilities_athens/epsg_2100.geojson'
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

# activity code lookups
mapping_purposes = {
    'business': 'b',
    'education': 'e',
    'home': 'h',
    'medical': 'm',
    'other': 'o',
    'recreation': 'r',
    'shop': 's',
    'service': 'c',
    'visit': 'v',
    'work': 'w',
    'travel': 't'
}
mapping_codes_purposes = {
    v: k for k, v in mapping_purposes.items() if not k.startswith('escort')}
mapping_codes_int = {v: k for k, v in enumerate(
    set(mapping_purposes.values()))}
mapping_int_codes = {v: k for k, v in mapping_codes_int.items()}
mapping_purposes_int = {k: mapping_codes_int[v]
                        for k, v in mapping_purposes.items()}

# create a consistent activity colour map
cmap = cm.get_cmap('tab20', len(mapping_codes_purposes))
colormap = {v: matplotlib.colors.rgb2hex(
    cmap(i)) for i, (k, v) in enumerate(mapping_codes_purposes.items())}
legend_elements = [Patch(edgecolor=v, facecolor=v, label=k)
                   for k, v in colormap.items()]


# %% Encode plans
plans = [person.plan for hid, pid, person in population.people()]
idx = [(hid, pid) for hid, pid, person in population.people()]


def create_plan_sequence(plan) -> str:
    """
    Convert a pam plan to a string sequency
    """
    seq = ''
    for act in plan.day:
        duration = int(act.duration / pd.Timedelta(seconds=60))
        seq = seq + (mapping_purposes[act.act]*duration)
    return seq


seqs = list(map(create_plan_sequence, plans))

# %% Calculate edit distances (matrix form, parallelised)


def _levenshtein_distance(a, b): return 1 - ratio(a, b)


levenshtein_distance = np.vectorize(_levenshtein_distance)


def calc_levenshtein_matrix(x: List[str], y: List[str]):
    """
    Create a levenshtein distance matrix from two lists of strings
    """
    distances = levenshtein_distance(np.array(x).reshape(-1, 1), np.array(y))
    return distances


distances = calc_levenshtein_matrix(seqs, seqs)


# %% visualise plan similarity
distances_no_diagonal = np.copy(distances)
np.fill_diagonal(distances_no_diagonal, 1)


def plot_closest_matches(plan, n):
    """
    Find and plot the closest match of a PAM activity schedule.
    """
    idx = plans.index(plan)
    idx_closest = np.argsort(distances_no_diagonal[idx])[:n]
    print('Selected plan:')
    plan.plot()
    plt.show()
    for i, j in enumerate(idx_closest):
        print(f'Match {i} - {j}')
        plans[j].plot()
        plt.show()


plan = population.random_person().plan
plot_closest_matches(plan, n=3)


# %% Agglomerative Clustering

# find the optimum number of clusters
scores = []
for i in range(2, 10):
    model = AgglomerativeClustering(
        n_clusters=i, linkage='complete', metric='precomputed'
    )
    model.fit((distances))
    scores.append({
        'clusters': i,
        'calinksi_harabasz':  sm.calinski_harabasz_score(distances, model.labels_),
        'silhouette': sm.silhouette_score(distances, model.labels_)
    })

scores = pd.DataFrame(scores)
for metric in ['calinksi_harabasz', 'silhouette']:
    scores.set_index('clusters')[metric].plot()
    plt.title(f'{metric} score')
    plt.xlabel('Number of clusters')
    plt.show()

# %% apply the clustering algorithm after selecting the number of clusters
n_clusters = 8

model = AgglomerativeClustering(
    n_clusters=n_clusters, linkage='complete', metric='precomputed'
)
model.fit((distances))
print(pd.Series(model.labels_).value_counts())


# %% Visualise clustering results


def plot_plan_breakdowns(x: list, ax=None, normalize: bool = False, legend_outside: bool = True):
    """
    Plot the activity breakdown by minute throughout the day. 
    :param x: A list of string sequences
    """
    df_plot = pd.DataFrame([i for i in j] for j in x)
    df_plot = df_plot.apply(lambda x: x.value_counts(
        normalize=normalize), axis=0).fillna(0).T
    df_plot.index /= 60
    df_plot.columns = df_plot.columns.map(mapping_codes_purposes)
    colors = [colormap[x] for x in df_plot.columns]
    df_plot.plot(kind='area', stacked=True, color=colors, ax=ax)
    if legend_outside:
        plt.legend(loc='lower left', bbox_to_anchor=(1.0, 0.5))
    plt.xlim(0, 24)
    plt.ylim(0, df_plot.max().max())
    # plt.show()


# plot the breakdown of all plan
plot_plan_breakdowns(seqs)
plt.savefig(
    os.path.join(path_outputs, 'cluster_breakdown_all_plans.png'),
    bbox_inches='tight'
)


def plot_plan_breakdowns_all_clusters_tiles(
    labels: np.array,
    n: int,
    figsize=(10, 7),
    export_path=None
):
    """
    Plot the activity breakdown of each cluster, in an n/2 * 2 tiled figure
    """
    label_list = list(pd.Series(labels).value_counts().index)
    label_list = label_list[:n]
    nrows = int(np.ceil(n/2))
    irow = 0
    icol = 0
    fig, axs = plt.subplots(nrows, 2, figsize=figsize,
                            sharex=True, sharey=True)
    fig.tight_layout(pad=2)
    for i in label_list:
        idx = list(np.where(labels == i)[0])
        ax = axs[irow, icol]
        plot_plan_breakdowns(
            np.array(seqs)[idx], ax=ax, normalize=True, legend_outside=False)
        ax.get_legend().remove()
        ax.set_title(f'Cluster {i} - {len(idx)} plans')
        ax.set_xlim(0, 24)
        ax.set_ylim(0, 1)
        irow += icol
        icol = (icol+1) % 2
    plt.legend(handles=legend_elements, loc='lower left',
               bbox_to_anchor=(1.0, 0.5), frameon=False)

    if export_path is not None:
        plt.savefig(export_path, bbox_inches='tight')


def plot_plan_breakdowns_all_clusters(labels: np.array, n=None):
    """
    Plot the activity breakdown of each cluster.
    """
    label_list = list(pd.Series(labels).value_counts().index)
    if n is not None:
        label_list = label_list[:n]
    for i in label_list:
        idx = list(np.where(labels == i)[0])
        print(f'Cluster {i} - {len(idx)} plans')
        plot_plan_breakdowns(np.array(seqs)[idx])


def plot_cluster_examples(labels: np.array, cluster: int, n: int = 3):
    """
    Plot some plans of a specified cluster
    """
    idxs = list(np.where(labels == cluster)[0])
    idxs = random.choices(idxs, k=n)
    for idx in idxs:
        plans[idx].plot()


plot_plan_breakdowns_all_clusters_tiles(
    model.labels_, n=n_clusters, figsize=(10, 10),
    export_path=os.path.join(
        path_outputs, 'cluster_breakdown_sklearn.png')
)

# plot_plan_breakdowns_all_clusters(model.labels_, n=5)
# plot_cluster_examples(model.labels_, 0)

# plot a specific cluster
# plot_plan_breakdowns(np.array(seqs)[np.where(
#     model.labels_ == 1)[0]], normalize=True)
# %% Analyse/plot person characteristics in each cluster.
attributes = pd.DataFrame(
    [{**{'hid': hid, 'pid': pid}, **person.attributes}
        for hid, pid, person in population.people()]
)
attributes['cluster'] = model.labels_
attributes = pd.concat([attributes, attributes.assign(cluster='total')], axis=0)

vars = ['gender', 'education', 'employment',
        'income', 'car_own', 'age_group']
for var in vars:
    df_plot = attributes.groupby('cluster')[var].\
        value_counts(normalize=True).unstack(level=1)
    ax = df_plot.plot(kind='bar', stacked=True)    
    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda x, _: '{:.0%}'.format(x)))
    plt.ylim(0, 1)
    plt.ylabel('Population share')
    plt.title(f'Cluster personal attributes, by {var}')
    export_path=os.path.join(
            path_outputs, f'cluster_attributes_{var}.png')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)
    plt.savefig(export_path, bbox_inches='tight')

#%% Same results as a table
attribute_breakdown = {
    var: attributes.groupby('cluster')[var].\
        value_counts(normalize=True).unstack(level=1).fillna(0) for var in vars
}

#%% plan choice estimation

#%% choice set
# x_vars = ['gender', 'age_group']
x_vars = ['gender', 'employment', 'income', 'car_own', 'age_group', 'education']
base_cluster = 3
cluster_ids = set(model.labels_)

df_choice = attributes[attributes.cluster!='total'].dropna(subset=x_vars).copy()
df_choice['cluster'] = df_choice['cluster'].apply(int)
df_choice = pd.get_dummies(df_choice)
database = db.Database('attributes', df_choice)

# utility function
V = {}
av = {}
for cluster_id in cluster_ids:
    av[cluster_id]=1 # availability
    V[cluster_id] = Beta(
        f'int_{cluster_id}', 0, None, None, 
        (cluster_id==base_cluster) * 1) # intercept
    for x_var in x_vars:
        bins = set(attributes.dropna(subset=x_vars)[x_var])
        for i, x_bin in enumerate(bins):
            V[cluster_id] += Beta(
                f'beta_{x_var}_{x_bin}_{cluster_id}', 0, None, None, 
                ((i==0) | (cluster_id==base_cluster)) * 1
                ) * database.variables[f'{x_var}_{x_bin}']

# estimate a logit model
logprob = models.loglogit(V, av, database.variables['cluster'])
cmodel = biogeme.biogeme.BIOGEME(database, logprob)
cmodel.modelName = '01logit'
cmodel.generateHtml=False
cmodel.generatePickle=False
cmodel.saveIterations=False
results = cmodel.estimate()
pandasResults = results.getEstimatedParameters()
pandasResults.round(3).to_csv(os.path.join(path_outputs, 'betas_cluster.csv'))

print('MNL results: \n', pandasResults.round(3))


#%% Statistical analysis
def cluster_participation_linear_test(cluster: int, attribute: str, value: str):
    """
    Linear regression between cluster participation and a respondent attribute
    """
    y = np.array((model.labels_==cluster) * 1)
    x = np.array((attributes[attributes.cluster!='total'][attribute]==value) * 1)
    results = stm.OLS(
        endog=y,
        exog=stm.add_constant(x)
    )
    results = results.fit()

    return results

# print(cluster_participation_linear_test(6, 'car_own', 'no').summary())
# print(cluster_participation_linear_test(6, 'income', 'high').summary())
# print(cluster_participation_linear_test(6, 'education', 'tertiary').summary())
# print(cluster_participation_linear_test(2, 'age_group', '60plus').summary())
# print(cluster_participation_linear_test(3, 'employment', 'active').summary())
print(cluster_participation_linear_test(4, 'gender', 'male').summary())