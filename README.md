# aspmc
(algebraic) answer set counter based on a treewidth-aware cycle-breaking for normal answer set programs

## Requirements
We include a setup bash script `setup.sh` that should automatically perform all steps required to run our code. (Except for providing the c2d binary)

### Python
* Python >= 3.6

All required modules are listed in `requirements.txt` and can be obtained by running
```
pip install -r requirements.txt
```

### Treedecompositions via htd
We use [htd](https://github.com/TU-Wien-DBAI/htd) to obtain treedecompositions that are needed for our treedecomposition guided clark completion and for obtaining treewidth upperbounds on the programs.

It is included as a git submodule, together with [dpdb](https://github.com/hmarkus/dp_on_dbs) and [htd_validate](https://github.com/raki123/htd_validate). They are needed to parse the treedecompositions produced by htd.

The submodules can be obtained by running
```
git submodule update --init
```

htd further needs to be compiled. Detailed instructions can be found [here](https://github.com/mabseher/htd/blob/master/INSTALL.md) but in all likelihood it is enough to run
```
cd lib/htd/
cmake .
make -j8
```

### Optionally: c2d
We use c2d to compute the number of answer sets/to obtain d-DNNF representations for probabilistic reasoning. 
The binary needs to be provided under `lib/c2d/bin/` as `c2d_linux` and can be downloaded from [here](http://reasoning.cs.ucla.edu/c2d/).

## Usage

The basic usage is

```
python bin/main.py <MODE> [OPTIONS] [<INPUT-FILES>]
```
Here, `<MODE>` must be one of
* `asp`: read a (possibly non-ground) normal answer set program and write a cnf with the same number of models to the file `out.cnf`
* `problog`: read a ground probabilistic program in [Problog](https://dtai.cs.kuleuven.be/problog/index.html) syntax and write a cnf with the same number of models to the file `out.cnf`
* `problogwmc`: the same as `problog` mode, but after writing `out.cnf` we automatically use c2d (if provided by the user) to compute a d-DNNF representation of the it and compute the answers to the probabilistic queries included in the input program

The following options are accepted:
* `-no_subset_check`: can provide a performance boost for computing treedecompositions for large instances
* `-no_pp`: only useful with mode problog. translates the problog program to an underlying answer set program, which is written to `out.lp`
