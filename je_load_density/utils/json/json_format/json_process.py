import json.decoder
import sys
from json import dumps
from json import loads

from je_load_density.utils.exception.exceptions import LoadDensityTestJsonException
from je_load_density.utils.exception.exception_tags import cant_reformat_json_error
from je_load_density.utils.exception.exception_tags import wrong_json_data_error


def _process_json(json_string: str, **kwargs):
    """
    :param json_string: full json str (not json type)
    :param kwargs: any another kwargs for dumps
    :return: reformat str
    """
    try:
        return dumps(loads(json_string), indent=4, sort_keys=True, **kwargs)
    except json.JSONDecodeError as error:
        print(wrong_json_data_error, file=sys.stderr)
        raise error
    except TypeError:
        try:
            return dumps(json_string, indent=4, sort_keys=True, **kwargs)
        except TypeError:
            raise LoadDensityTestJsonException(wrong_json_data_error)


def reformat_json(json_string: str, **kwargs):
    try:
        return _process_json(json_string, **kwargs)
    except LoadDensityTestJsonException:
        raise LoadDensityTestJsonException(cant_reformat_json_error)
