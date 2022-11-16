import os

print(os.getcwd())

# use os system to test argparse

os.system("cd " + os.getcwd())
os.system("python je_load_density --execute_file " + os.getcwd() + r"/test/unit_test/argparse/test_json_file1.json")
os.system("python je_load_density --execute_dir " + os.getcwd() + r"/test/unit_test/argparse")
