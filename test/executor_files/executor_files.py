from je_locust_wrapper import execute_files
from je_locust_wrapper import get_dir_files_as_list

files_list = get_dir_files_as_list("/test/executor_files")
print(files_list)

execute_files(files_list)
