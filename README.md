# athenspop
Creating and analysing synthetic and activity-based demand for Athens.

<!-- TOC depthfrom:2 -->

- [Introduction](#introduction)
- [Gettting started](#gettting-started)
    - [Installation](#installation)
        - [Ubuntu / Mac OS](#ubuntu--mac-os)
        - [Windows](#windows)
    - [Examples](#examples)
    - [Running via the command-line interface](#running-via-the-command-line-interface)
- [Data Requirements](#data-requirements)
- [Next steps](#next-steps)

<!-- /TOC -->

## Introduction
The aim of this repo is to demonstrate the creation of a synthetic MATSim population for Athens, using the open-source [Population Activity Modeller (PAM)](https://github.com/arup-group/pam) library. PAM is a python API for activity sequence modelling, focusing on the generation and modification of travel demand scenarios.

**Why?**: Transport planners and decision-makers are increasingly facing difficult questions, such as decarbonisation and transport equity, which require appropriate tools to help us answer them effectively. Activity- and agent-based modelling techniques provide us with bottom-up approaches for simulating complex travel patterns, focusing on the behavioural drivers behind invividuals' travel decisions. Through simple examples and case studies, we wish to demonstrate such approaches and gain better understanding of existing datasets.

**How?**: We employ statistical analysis, machine learning, and data fusion methodologies, often via the PAM interface.

**What does it produce**: Athenspop can be used for the analysis and visualisation of the NTUA travel survey data, or the creation of synthetic demand scnearios.


## Gettting started

### Installation

You can install the library as follows:


#### Ubuntu / Mac OS

```
git clone git@github.com:Theodore-Chatziioannou/athenspop.git
cd athenspop

virtualenv -p python3 venv
source venv/bin/activate
pip3 install -e .
```

#### Windows

```
git clone git@github.com:Theodore-Chatziioannou/athenspop.git
cd athenspop

conda create -n venv python=3.8
conda activate venv
conda install geopandas
pip3 install -e .
```


### Examples
A simple example can be found under `examples/01_Create_Simple_Athens_Population.py` scipt.

The library creates a number of examples under the `examples` directory:
* `01_Create_Simple_Athens_Population.py`: creates a simplistic population by resampling and converting the travel diary data to a MATSim-compatible format.
* `02_Create_Population_OSM_landuse.py`: as above, but using OSM land-use data for facility sampling.
* `03_Analysis.py`: Demonstrates some reporting and visualisation methods.
* `04_Clustering_demo.py`: Spatio-temporal clustering of the travel diaries.


### Running via the command-line interface
Athenspop can be also used via its Command Line Interface (CLI). Once the athenspop library is install, you can run `athenspop --help` to discover the available options.

For example:
```
$ athenspop create population --help

> Usage: athenspop create population [OPTIONS] INPUTS_PATH
> 
> Options:
>   -o, --path_outputs TEXT     Path to the output population.xml file.
>   -f, --path_facilities TEXT  Path to the facility (land use) dataset
>                               (optional).
>   --help                      Show this message and exit.
```


Therefore, to create a new population you can run:
```
athenspop create population <travel_survey_directory> -o <output_directory>
```


## Data Requirements
The repo examples use the NTUA's travel survey as an input. The diaries are self-reported in an online questionnaire, which has been advertised through a radio broadcast (ERT).

To get a copy of the data please get in touch with the repo's owners.


## Next steps
* Demonstrate some plan choice methods (for example, mode choice or plan generation).
* Apply more complex re-sampling approaches (such as IPF).
* Fuse microdata with more aggregate statistical distributions.