mv aspmc/external aspmc/.external
pdoc --config='docformat="google"' -f --html --output-dir docs aspmc
mv aspmc/.external aspmc/external
python -m build
twine check dist/*
twine upload dist/*
