# sqlplot
![automatic test](https://github.com/koeppl/sqlplot/actions/workflows/check.yml/badge.svg)

This is a python3 reimplementation of [https://github.com/bingmann/sqlplot-tools](sqlplot-tools).

The main considerations for writing this reimplementation are:
 - more features such as macros for sql expressions
 -  python needs less code C++ as the main task is to parse text and issue SQL commands

## file types
We support `tex` and `python` as input, where the keyword are prefixed with `%%` or `##`, respectively.
As output, we support

 - `tex`
 - `python` - can be directly used with `matplotlib`
 - `csv` - can be directly used with `plotly` via `pandas` (python3 libraries)
 - `json` - useful for loading in a HTML5 webpage


## Permanent Legend
When parsing a tex file, `sqlplot` maintains a dictionary mapping legend entries (represented internal as tuples) to cycle shift numbers used in pgfplots to determine the shape and the color of a plot entry such that the same entry across several plot has the same color and shape. 
This dictionary is saved in the file `pgf_color_entries.txt`, and can be edited to change the cycle shift number of an entry.

## new keywords

### CONFIG line
A MULTIPLOT command can have a final line

```
%% CONFIG file={filename} type={filetype} mode=[wa]
```

This is basically a key-value list, where each key-value is optional.
The valid keys are:
 - file: write the output in a separate file instead of directly to stdout
 - type: use a different file type than the type of the file we are currently parsing
 - mode: either 'w' for overwriting or 'a' for appending. Appending is useful if you have several SQL commands that generate data for a single plot
 - colorcache=none: do not use the cached scheme written in `pgf_color_entries.txt`


```
%% SINGLEPLOT(name) SQL-STATEMENT 
```
Instead of a multiplot, we plot only a single dataset whose name string we set as a parameter of `SINGLELPLOT`.
The rest is exactly as `MULTIPLOT` but a regular SQL command (i.e., without `MULTIPLOT` in the SQL body).
The idea of this command is to supplement a `MULTIPLOT` command from another table that may only contain the benchmarks of a single instance.

```
%% MATRIX SELECT-STATEMENT containing columns `x`, `y` and `val`
```
create a tabular with the `x` attribute as columns, `y` attribute as rows and `val` as matrix entries.
Example:
```
%% MATRIX
%% SELECT 
%% "\num{" || prefix || "}" AS x,
%% "\texttt{" || file  || "}" AS y,
%% printf("%.2f", time) AS val
%% FROM stats
```


```
%% DEFINE macro(arg1,arg2,...) {body $arg1 ... $arg2 ...} 
```

Creates the macro `macro` with arguments `arg1`, `arg2`, etc.
The arguments must occur in the body preceded by a '$'.
The macro can then be used in a SQL expression with `$macro(parameter1, paratemer2, ...)`
You can overwrite the definition of a macro.

``
%% UNDEF macro
``

Undefines the macro `macro`.


## Program parameters

- `-i <filename>` the input file name to parse (required argument)
- `-l DEBUG` runs the program in debug level logging, issuing all SQL commands that are executed, also unpacking a `MULTIPLOT` command into multiple SQL commands
- `-D databasefile` stores in-memory created database in a file in append mode, meaning that it adds tables in case that the file is an existing sqlite database, and assuming that this database does not already contain these tables.

