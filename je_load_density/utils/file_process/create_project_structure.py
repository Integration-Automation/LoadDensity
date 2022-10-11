from pathlib import Path


def _create_dir(dir_name: str):
    """
    create project dir
    :param dir_name: create dir use dir name
    :return: None
    """
    Path(dir_name).mkdir(
        parents=True,
        exist_ok=True
    )


def create_template_dir():
    _create_dir("je_load_density/template")
