# athenspop
The aim of this repo is to demonstrate the creation of a synthetic MATSim population for Athens, using the open-source [PAM](https://github.com/arup-group/pam) library.

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
- [Developers](#developers)

<!-- /TOC -->

## Introduction



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

### Running via the command-line interface



## Data Requirements
The repo examples use the NTUA's travel survey as an input. The diaries are self-reported in an online questionnaire, which has been advertised through a radio broadcast (ERT).

To get a copy of the data please get in touch with the repo's owners.


## Next steps
[TBC]

## Developers