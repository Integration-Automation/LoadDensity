import os

from je_load_testing import execute_files
from je_load_testing import get_dir_files_as_list

files_list = get_dir_files_as_list("/test/executor_files")
print(files_list)

execute_files(files_list)
