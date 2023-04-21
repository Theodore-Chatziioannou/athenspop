"""
Simple clustering analysis
"""
## Import dependencies
if True:
    import os
    from pathlib import Path
    import sys
    sys.path.insert(0, os.path.join(Path(__file__).parent.absolute(), '..'))
    from athenspop import preprocessing

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pam import read, activity
import numpy as np
import sklearn.metrics as sm
from typing import List
from scipy.stats import kendalltau
import itertools
import seaborn as sns

from pam.planner.clustering import PlanClusters

## User Input
path_survey = '/c/Projects/athenspop/demand_data_NTUA'
dir_outputs = '/c/Projects/athenspop/'
n_clusters = 6
clustering_method = 'spectral'
group_other = False # whether to group recreation, visit, other, and service purposes
run_mnl = False
drop_infilled = True # whether to drop trips that did not report a return home trip
iterate_clusters = False # whether to run sensitivities on the number of clusters
demographic_attrs = ['gender', 'education', 'employment',
        'income', 'car_own', 'age_group'] # demographic variables to analyse

path_outputs = f'outputs_{clustering_method}_c{n_clusters}'
if group_other: path_outputs += '_group_other'
if drop_infilled: path_outputs += '_drop_infilled'
path_outputs = os.path.join(dir_outputs, path_outputs)

if not os.path.exists(path_outputs):
    os.mkdir(path_outputs)

def create_population():
    """
    Ingest travel survey data
        and create a PAM population
    """
    survey_raw = preprocessing.read_survey(
        os.path.join(path_survey, 'NEW_diaries_athens_final.csv')
    )
    if drop_infilled:
        survey_raw = survey_raw[~survey_raw.infilled]

    # person attributes
    person_attributes = preprocessing.get_person_attributes(survey_raw)

    # trips dataset
    trips = preprocessing.get_trips_table(survey_raw, filter_next_day=True)

    # create PAM population
    population = read.load_travel_diary(
        trips=trips,
        persons_attributes=person_attributes,
        tour_based=False
    )

    # limit plan to 24-hours
    for hid, pid, person in population.people():
        person.plan.crop()

    # remove "travel" activities
    for hid, pid, person in population.people():
        for i, elem in enumerate(person.plan.day):
            if isinstance(elem, activity.Leg):
                elem.act = person.plan.day[i-1].act

    return population

def iterate_n_clusters(clusters):
    """
    Try different number of clusters and 
        use cluster homogeneity metrics to inform 
        the optimal selection. 
    """
    scores = []
    for i in range(2, 10):
        clusters.fit(n_clusters = i, clustering_method='spectral')
        scores.append({
            'clusters': i,
            'calinksi_harabasz':  sm.calinski_harabasz_score(clusters.distances, clusters.model.labels_),
            'silhouette': sm.silhouette_score(clusters.distances, clusters.model.labels_)
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


def get_cluster_attributes(clusters):
    """
    Summarise person attributes for each cluser
    """
    attributes = pd.DataFrame(
        [{**{'hid': hid, 'pid': pid}, **person.attributes}
            for hid, pid, person in population.people()]
    )
    attributes['cluster'] = clusters.model.labels_
    attributes.to_csv(os.path.join(path_outputs, 'attributes_cluster.csv'), index=False)
    attributes = pd.concat([attributes, attributes.assign(cluster='total')], axis=0)
    
    return attributes

def plot_attribute_breakdown(attributes: pd.DataFrame) -> None:
    """
    Plot person attributes breakdown by cluster
    """
    for var in demographic_attrs:
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

def export_attributes_breakdowns(attributes: pd.DataFrame) -> None:
    attribute_breakdown = {
        var: attributes.groupby('cluster')[var].\
            value_counts(normalize=True).unstack(level=1).fillna(0) for var in demographic_attrs
    }

    export_path = os.path.join(path_outputs, 'attributes_breakdown.txt')
    if os.path.exists(export_path):
        os.remove(export_path)
    for k, v in attribute_breakdown.items():
        v.round(3).to_csv(export_path, mode='a', sep='\t')


def get_correlation(attributes):
    """
    Kendall correlation with dummy values and significance levels
    """
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

    return corr_matrix


def get_corr_matrix_significant(corr_matrix):
    """
    Correlation matrix - only keep significant values
    """
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
    
    return corr_matrix_significant


def plot_correlation_heatmap(corr_matrix_significant):
    """
    Kendall correlation heatmap.
    """
    df_plot = corr_matrix_significant.copy()
    df_plot = df_plot.loc[
        df_plot.index.str.startswith('cluster'),
        ~df_plot.columns.str.startswith('cluster')
    ]
    fig, ax = plt.subplots(1, 1, figsize=(15,7))
    sns.heatmap(df_plot, annot=True, fmt='.2f', 
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


def plot_activity_sets(clusters):
    """
    Plot activity set counts for each cluster
    """
    n_clusters = clusters.model.n_clusters
    fig, axs = plt.subplots(n_clusters, figsize=(10, 17), sharex=True)
    for i in range(n_clusters):
        pd.Series([', '.join(set(x.act for x in plan)) for plan in clusters.get_cluster_plans(i)]).\
                value_counts(ascending=True).plot(kind='barh', ax=axs[i])
        axs[i].set_ylabel(f'Cluster {i}')
    plt.savefig(os.path.join(path_outputs, 'activity_sets.png'), bbox_inches='tight')
    plt.show()


if __name__ == '__main__':
    # population object
    population = create_population()
    
    # set up clusters object
    clusters = PlanClusters(population)
    clusters.plot_plan_breakdowns()
    plt.savefig(os.path.join(path_outputs, 'cluster_breakdown_all_plans.png'), bbox_inches='tight')
    
    # find optimal number of clusters
    if iterate_clusters:
        iterate_n_clusters(clusters)

    # apply the clustering algorithm after selecting the number of clusters
    clusters.fit(n_clusters = n_clusters, clustering_method='spectral')
    clusters.plot_plan_breakdowns_tiles()
    plt.savefig(os.path.join(path_outputs, 'cluster_breakdown_sklearn.png'), bbox_inches='tight')

    # person attributes
    attributes = get_cluster_attributes(clusters)
    plot_attribute_breakdown(attributes)
    export_attributes_breakdowns(attributes)

    # correlation between clusters and person attributes 
    corr_matrix = get_correlation(attributes)
    corr_matrix_significant = get_corr_matrix_significant(corr_matrix)
    plot_correlation_heatmap(corr_matrix_significant)

    # activity sets
    plot_activity_sets(clusters)