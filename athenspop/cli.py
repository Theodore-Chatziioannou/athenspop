import click
import logging
from pathlib import Path
import os
from athenspop.core import create_population

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-3s %(message)s',
)
logger = logging.getLogger(__name__)



@click.group()
def cli():
    """
    Athenspop
    """
    pass

@cli.group()
def create():
    """
    Build a population file.
    """
    pass


@create.command()
@click.argument("inputs_path", type=click.Path(exists=True))
@click.option(
    "--path_outputs",
    "-o",
    help="Path to the output population.xml file."
)
@click.option(
    "--path_facilities",
    "-f",
    default=None,
    help="Path to the facility (land use) dataset (optional)."
)
def population(inputs_path, path_outputs, path_facilities):
    logger.info('Creating population...')
    create_population(
        path_survey=inputs_path,
        path_outputs=path_outputs,
        path_facilities=path_facilities
    )