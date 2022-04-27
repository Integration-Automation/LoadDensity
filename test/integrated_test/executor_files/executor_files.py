from je_load_density import execute_files
from je_load_density import get_dir_files_as_list

# get a dir json file list
files_list = get_dir_files_as_list("/test/executor_files")
# execute all file on list
execute_files(files_list)

