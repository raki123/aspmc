if ! python3 -c 'import sys; assert sys.version_info >= (3,6)' > /dev/null; 
then 
    echo python 3.6 or higher is required;
else
    pip install -r requirements.txt
    git submodule update --init
    cd lib/htd/
    cmake .
    make -j8
fi
