File Processing API
===================

Utility functions for file and directory operations.

get_dir_files_as_list()
-----------------------

Get all files in a directory that match a given file extension.

.. code-block:: python

    def get_dir_files_as_list(
        dir_path: str = str(Path.cwd()),
        default_search_file_extension: str = ".json"
    ) -> List[str]

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Type
     - Description
   * - ``dir_path``
     - ``str``
     - Directory path to search (default: current working directory)
   * - ``default_search_file_extension``
     - ``str``
     - File extension to filter (default: ``".json"``)

**Returns:** ``List[str]`` — List of absolute file paths matching the extension.
Returns an empty list if the directory does not exist or an error occurs.

The search is recursive (uses ``Path.rglob()``).

**Example:**

.. code-block:: python

    from je_load_density import get_dir_files_as_list

    # Get all JSON files in a directory
    files = get_dir_files_as_list("./test_scripts/")

    # Get all Python files
    files = get_dir_files_as_list("./src/", ".py")

read_action_json()
------------------

Read a JSON action file and return its content.

.. code-block:: python

    def read_action_json(json_file_path: str) -> Union[dict, list]

**Parameters:**

* ``json_file_path`` — Path to the JSON file

**Returns:** ``dict`` or ``list`` — Parsed JSON content.

**Raises:** ``LoadDensityTestJsonException`` — If the file cannot be found or read.

write_action_json()
-------------------

Write data to a JSON file.

.. code-block:: python

    def write_action_json(json_save_path: str, action_json: Union[dict, list]) -> None

**Parameters:**

* ``json_save_path`` — Path to save the JSON file
* ``action_json`` — Data to write (dict or list)

**Raises:** ``LoadDensityTestJsonException`` — If the file cannot be written.
