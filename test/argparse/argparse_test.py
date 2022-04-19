import os

print(os.getcwd())

os.system("cd " + os.getcwd())
os.system("python je_locust_wrapper --execute_file " + os.getcwd() + r"/test/argparse/test_json_file1.json")


