import os.path
import re

scripts_dir = os.path.dirname(__file__)
with open(os.path.join(scripts_dir, '..', 'pre_workbench', '_version.py'), 'r') as f:
    exec(f.read())

iss_file = os.path.join(scripts_dir, 'Win_Installer.iss')
with open(iss_file, 'r') as f:
    content = f.read()

content = re.sub('#define MyAppVersion ".*"', '#define MyAppVersion "' + __version__ + '"', content)

with open(iss_file, 'w') as f:
    f.write(content)
