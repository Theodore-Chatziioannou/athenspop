"""
Simple clustering analysis
"""

# %% Import dependencies
if True:
    import os
    from pathlib import Path
    import sys
    sys.path.insert(0, os.path.join(Path(__file__).parent.absolute(), '..'))

from athenspop import preprocessing
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
from scipy.stats import kendalltau
import itertools
import seaborn as sns

import biogeme
import biogeme.database as db
import biogeme.biogeme as bio
import biogeme.models as models
from biogeme.expressions import Beta


# %% User Input
path_survey = '/c/Projects/athenspop/demand_data_NTUA'
dir_outputs = '/c/Projects/athenspop/'
n_clusters = 6
group_other = True # whether to group recreation, visit, other, and service
run_mnl = False
drop_infilled = False # whether to drop trips that did not report a return home trip


path_outputs = f'outputs_c{n_clusters}'
if group_other: path_outputs += '_group_other'
if drop_infilled: path_outputs += '_drop_infilled'
path_outputs = os.path.join(dir_outputs, path_outputs)

if not os.path.exists(path_outputs):
    os.mkdir(path_outputs)

# %% Ingest travel survey data
survey_raw = preprocessing.read_survey(
    os.path.join(path_survey, 'NEW_diaries_athens_final.csv')
)
if drop_infilled:
    survey_raw = survey_raw[~survey_raw.infilled]

# person attributes
person_attributes = preprocessing.get_person_attributes(survey_raw)

# trips dataset
trips = preprocessing.get_trips_table(survey_raw, filter_next_day=True)


# %% create PAM population
population = read.load_travel_diary(
    trips=trips,
    persons_attributes=person_attributes,
    tour_based=False
)

# limit plan to 24-hours
for hid, pid, person in population.people():
    person.plan.crop()


#%%
# activity code lookups
if group_other:
    mapping_purposes = {
        'business': 'b',
        'education': 'e',
        'home': 'h',
        'medical': 'o',
        'recreation': 'o',
        'shop': 'o',
        'service': 'o',
        'visit': 'o',
        'work': 'w',
        'other': 'o',
        'travel': 't'
    }
else:
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
    plt.show()
    scores.set_index('clusters')[metric].plot()
    plt.title(f'{metric} score')
    plt.xlabel('Number of clusters')
    plt.ylim(0)
    export_path=os.path.join(
        path_outputs, f'score_{metric}.png')
    plt.savefig(export_path, bbox_inches='tight')
    plt.show()


# %% apply the clustering algorithm after selecting the number of clusters

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
attributes.to_csv(os.path.join(path_outputs, 'attributes_cluster.csv'), index=False)
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

export_path = os.path.join(path_outputs, 'attributes_breakdown.txt')
if os.path.exists(export_path):
    os.remove(export_path)
for k, v in attribute_breakdown.items():
    v.round(3).to_csv(export_path, mode='a', sep='\t')


#%% attributes correlation
attributes['income_ordinal'] = attributes['income'].map(
    {v:k for k, v in enumerate(['zero','low','medium','high'])}
)
attributes['education_ordinal'] = attributes['education'].map(
    {v:k for k, v in enumerate(['primary', 'secondary', 'tertiary'])}
)
attributes['age_group_ordinal'] = attributes['age_group'].map(
    {v:k for k, v in enumerate(['0to20', '21to39', '40to59', '60plus'])}
)
attributes['is_female'] = (attributes['gender'] == 'female') * 1
attributes['owns_car'] = (attributes['car_own'] == 'yes') * 1

#%% kendall correlation with dummy values and significance

corr_binary = attributes.copy()
corr_binary['cluster'] = corr_binary['cluster'].map(str)
corr_binary = pd.get_dummies(corr_binary[['education', 'employment', 'gender','income', 'age_group','cluster']])

corr_matrix = []
for i, j in itertools.product(corr_binary.columns, corr_binary.columns):
    t = kendalltau(x=corr_binary[i], y=corr_binary[j])
    corr_matrix.append((i, j, t.correlation, t.pvalue))

corr_matrix = pd.DataFrame(corr_matrix)
corr_matrix.columns = ['x', 'y', 'correlation', 'pvalue']
corr_matrix.set_index(['x', 'y'], inplace=True)
corr_matrix.to_csv(os.path.join(path_outputs, f'correlation_attributes_binary_kendall.csv'))

# significant values only
corr_matrix_significant = corr_matrix.copy()
corr_matrix_significant['correlation'] = np.where(
    (corr_matrix_significant.pvalue>0.05) | 
    (corr_matrix_significant.index.get_level_values(0)==corr_matrix_significant.index.get_level_values(1)) | 
    (pd.Series(corr_matrix_significant.index.get_level_values(0)).apply(lambda x: x.split('_')[0]) == \
     pd.Series(corr_matrix_significant.index.get_level_values(1)).apply(lambda x: x.split('_')[0])).values, 
    np.nan, 
    corr_matrix_significant['correlation'])
corr_matrix_significant = corr_matrix_significant['correlation'].unstack(level='y')

cols_order = [x for x in corr_matrix_significant.columns if (x.startswith('cluster') and 'total' not in x)]
cols_order += [x for x in corr_matrix_significant.columns if not x.startswith('cluster')]
corr_matrix_significant = corr_matrix_significant.loc[cols_order, cols_order]

corr_matrix_significant.to_csv(os.path.join(path_outputs, f'correlation_attributes_binary_kendall_matrix.csv'))
corr_matrix_significant

#%% plot kendal heatmap
fig, ax = plt.subplots(1, 1, figsize=(15,15))
sns.heatmap(corr_matrix_significant, annot=True, fmt='.2f', 
            cmap='RdBu' , center=0, vmin=-1, vmax=1, linewidths=0.1,
            cbar=False, linecolor='lightgrey')
plt.title('kendall correlation')
ax.tick_params(labelbottom=True, labeltop=True, labelleft=True, labelright=True, 
               top=False, bottom=False, left=False, right=False)
plt.xticks(rotation=90)
plt.yticks(rotation=0)
plt.xlabel('')
plt.ylabel('')
plt.savefig(os.path.join(path_outputs, 'correlation_attributes_binary_kendall_matrix.png'), bbox_inches='tight')
plt.show()

#%% plan choice estimation

#%% choice set
# x_vars = ['gender', 'age_group']
if run_mnl:
    x_vars = ['gender', 'employment', 'income', 'car_own', 'age_group', 'education']
    base_cluster = pd.Series(model.labels_).value_counts().idxmax() # use cluster with most observations as base
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
                    ((i==0) | (cluster_id==base_cluster)) * 14
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

#%% marginal effects
control_vars = ['employment_active', 'employment_student', 'education_tertiary',
                                  'income_high', 'gender_female', 'age_group_60plus']
margeffs = []
for cluster_id in range(n_clusters):
    margeff = stm.Logit(
        corr_binary[f'cluster_{cluster_id}'], 
        stm.add_constant(corr_binary[control_vars])
    ).fit().get_margeff()
    margeffs.append(margeff.summary_frame().assign(cluster=cluster_id))
margeffs = pd.concat(margeffs, axis=0)
margeffs = margeffs.reset_index()[['cluster','index','dy/dx', 'Pr(>|z|)']]
margeffs.columns = ['cluster', 'variable', 'dy/dx', 'pvalue']
margeffs.round(3).to_csv(os.path.join(path_outputs, 'marginal_effects.csv'))
margeffs[margeffs.pvalue<0.3].round(3)

#%%