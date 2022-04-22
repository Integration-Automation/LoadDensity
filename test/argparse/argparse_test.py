import os

print(os.getcwd())

os.system("cd " + os.getcwd())
os.system("python je_load_density --execute_file " + os.getcwd() + r"/test/argparse/test_json_file1.json")
os.system("python je_load_density --execute_dir " + os.getcwd() + r"/test/argparse")

