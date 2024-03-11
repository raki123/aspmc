# aspmc
(Algebraic) answer set counter based on a treewidth-aware cycle-breaking for normal answer set programs.

For usage on Linux you may also install this software as a pip package via
```
pip install aspmc
```
Documentation for usage as a python module is available [here](https://raki123.github.io/aspmc/). 
Examples for command line usage are available below.

If you have any issues please contact us, or even better create an issue on GitHub.

For academic usage cite 

 * Eiter, T., Hecher, M., & Kiesel, R. (2021, September). Treewidth-Aware Cycle Breaking for Algebraic Answer Set Counting. In Proceedings of the International Conference on Principles of Knowledge Representation and Reasoning (Vol. 18, No. 1, pp. 269-279).

## Development setup
For developement clone via 
```
git clone --single-branch --branch=main git@github.com:raki123/aspmc.git
```
to avoid the download of the experimental results in branch `results`.

We include a setup bash script `setup.sh` that should automatically perform all steps below that are required to run our code. (Except for providing the c2d and miniC2D binary.)

### Python
* Python >= 3.6

All required modules are listed in `requirements.txt` and can be obtained by running
```
pip install -r requirements.txt
```

### Tree Decompositions via flow-cutter
We use [flow-cutter](https://github.com/kit-algo/flow-cutter-pace17) to obtain treedecompositions that are needed for our treedecomposition guided clark completion, obtaining treewidth upperbounds on the programs, variable order generation and more.

It is included as a git submodule.

The submodules can be obtained by running
```
git submodule update --init
```

flow-cutter further needs to be compiled via
```
cd aspmc/external/flow-cutter/
bash build.sh
```


### Knowledge Compilation via d4 or sharpSAT-TD 
We use [d4](https://github.com/raki123/d4) or [sharpSAT-TD](https://github.com/raki123/sharpsat-td) for knowledge compilation. Note that both of these are forks of the original model counters [here](https://github.com/crillab/d4) and [here](https://github.com/Laakeri/sharpsat-td/), respectively. For d4 we added support for smooth compilation and for sharpSAT-TD we used the nicely thought out addition by Tuukka Korhonen and Matti Järvisalo to enable weighted model counting over semirings in that we added a custom semiring to compile an sd-DNNF.

Both are also included as a git submodules.

The submodules can be obtained by running
```
git submodule update --init
```

They can then be compiled via 
```
cd aspmc/external/sharpsat-td/
mkdir bin
bash setupdev.sh
cd ../../../
cd aspmc/external/d4/
make -j4
cd ../../../
```

## Optionally: c2d and miniC2D
We also are able to use c2d to obtain d-DNNF representations. 
The c2d binary can be provided under `aspmc/external/c2d/bin/` as `c2d_linux` and can be downloaded from [here](http://reasoning.cs.ucla.edu/c2d/).
The miniC2D binary (and the hgr2htree binary) can be provided under `aspmc/external/miniC2D/bin/linux/` as `miniC2D` (and `hgr2htree`) and can be downloaded from [here](http://reasoning.cs.ucla.edu/minic2d/).

Note that they are only available for research use.

## Usage

The basic usage is

```
aspmc: An Algebraic Answer Set Counter
aspmc version 1.1.0, Mar 11, 2024

python main.py [-m .] [-st .] [-c] [-s .] [-n] [-t] [-ds .] [-dt .] [-k .] [-g .] [-b .] [-v .] [-h] [<INPUT-FILES>]
    --mode              -m  MODE        set input mode to MODE:
                                        * asp               : take a normal answer set program as input (default)
                                        * smodels           : take a normal answer set program in smodels format as input
                                        * optasp            : take a normal answer set program with weak constraints as input
                                        * cnf               : take an (extended) cnf as input
                                        * problog           : take a problog program as input
                                        * smproblog         : take a problog program with negations as input
                                        * meuproblog        : take a problog program with extra decision and utility atoms as input
                                        * mapproblog        : take a problog program with extra evidence and map query atoms as input
                                        * mpeproblog        : take a problog program with extra evidence atoms as input
                                        * dtpasp            : take a probabilistic answer set program with extra decision and utility atoms as input
                                        * credal            : take a probabilistic answer set program with credal semantics as input
    --strategy          -st STRATEGY    set solving strategy to STRATEGY:
                                        * flexible          : choose the solver flexibly 
                                        * compilation       : use knowledge compilation (default)
    --count             -c              not only output the equivalent cnf as out.cnf but also performs (algebraic) counting of the answer sets
    --semiring          -s  SEMIRING    use the semiring specified in the python file aspmc/semirings/SEMIRING.py
                                        only useful with -m problog
    --no_pp             -n              does not perform cycle breaking and outputs a normalized version of the input program as `out.lp`
                                        the result is equivalent, ground and does not contain annotated disjunctions.
    --treewidth         -t              print the treewidth of the resulting CNF
    --decos             -ds SOLVER      set the solver that computes tree decompositions to SOLVER:
                                        * flow-cutter       : uses flow_cutter_pace17 (default)
    --decot             -dt SECONDS     set the timeout for computing tree decompositions to SECONDS (default: 1)
    --knowlege          -k  COMPILER    set the knowledge compiler to COMPILER:
                                        * sharpsat-td       : uses a compilation version of sharpsat-td (default)
                                        * sharpsat-td-live  : uses a compilation version of sharpsat-td where compilation and counting are simultaneous
                                        * d4                : uses the (slightly modified) d4 compiler. 
                                        * c2d               : uses the c2d compiler. 
                                        * miniC2D           : uses the miniC2D compiler. 
    --guide_clark       -g  GUIDE       set the tree decomposition type to use to guide the clark completion to GUIDE:
                                        * none              : preform the normal clark completion without guidance
                                        * ors               : guide for or nodes only 
                                        * both              : guide for both `and` and `or` nodes (default)
                                        * adaptive          : guide `both` that takes into account the cost of auxilliary variables 
                                        * choose            : try to choose the best of the previous options bases on expected treewidth
    --cycle-breaking    -b  STRATEGY    set the cycle-breaking strategy to STRATEGY:
                                        * none              : do not perform cycle-breaking, not suitable for model counting
                                        * tp                : perform tp-unfolding, suitable for model counting (default)
                                        * binary            : use the strategy of Janhunen without local and global ranking constraints
                                                                not suitable for model counting
                                        * binary-opt        : use the strategy of Hecher, not suitable for model counting
                                        * lt                : use the strategy of Lin and Zhao, not suitable for model counting
                                        * lt-opt            : use a modified version of Lin and Zhao's strategy with a smaller encoding,
                                                                not suitable for model counting
    --verbosity         -v  VERBOSITY   set the logging level to VERBOSITY:
                                        * debug             : print everything
                                        * info              : print as usual
                                        * result            : only print results, warnings and errors
                                        * warning           : only print warnings and errors
                                        * errors            : only print errors
    --help              -h              print this help and exit
```

### Examples
These examples are for when the code is downloaded via GitHub.
When using the pip package replace `python main.py` by `aspmc` to obtain the same result.
#### ASP example:
```
python main.py -m asp -c -f 
a :- not b.
b :- not a.
```
Reads the program from stdin and counts its models.

```
python main.py -m asp -c -f test/test_cycle.lp
```
Reads the same program from file and counts its models.

#### problog example
```
python main.py -m problog -c -f
0.5::a.
b :- a.
query(b).
```
Evaluates the given simple program over the probability semiring.

```
python main.py -m problog -c -s maxplus -f
0.5::a.
b :- a.
query(b).
```
Evaluates the given simple program over the MaxPlus semiring.
