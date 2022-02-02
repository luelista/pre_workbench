#!/bin/sh -e
rm dist/* && echo Deleted old dist. || echo No old dist to delete.

#python3 setup.py sdist bdist_wheel
python3 -m build

printf "\n\n###########################################################\n"
ls dist/*
echo
read -p "Do you want to upload the packages listed above? [yN] " yn
case $yn in
    [Yy]* ) break;;
    * ) echo "Exiting"; exit;;
esac

echo "Uploading to PyPi..."
twine upload --verbose dist/*
