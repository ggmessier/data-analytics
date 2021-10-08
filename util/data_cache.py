#!/usr/bin/env python
# coding: utf-8

"""This library provides the ability to cache intermediate results that take a long time 
to generate and don't change for example, the results of pre-processing a static dataset.


    Copyright (C) 2021 Caleb John

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import pandas as pd
import pickle
import functools

hdf_like_ext = ['.h5', '.hdf', '.hd5']


def watchable(x):
    """returns true if x is a type that will neatly fit into the filename
    currently supported types are int, float, and string"""
    return isinstance(x, int) or isinstance(x, float) or (isinstance(x, str) and not "/" in x)

def default_filename(func):
    return "{}.hd5".format(func.__name__)

def CacheResult(func, *args, path=None, filename=None, **kwargs):
    """Wraps around a function that generates a datastructure and caches that
    datastructure to disk.  For subsequent calls, the datastructure is read
    from the cache file rather than being regenerated. Delete the cached file 
    to regenerate the data structure.

    NOTE: You will need to delete cache files every time you make a code change
    to the function that generates the datastructure.
    
    Separate cache files are generated for calls to the generator function with 
    different arguments.  The argument values are worked into the cache file name.
    
    It is good practice to incorporate a TQDM progress bar in your generator function.
    That way, you get visual feedback regarding whether or not you're generating new
    results or using cached results.
    
    Give an HDF file suffix (.h5, .hdf, .hd5) to save the cache as HDF, otherwise
    pickle is used.
    
    If no path is passed, the datastructure is generated without caching.
    if no filename is passed, <function_name>.hd5 will be used

    Decorator Example
    =================
    @CacheResult
    def load_features(x):
        time.sleep(5)
        return pd.DataFrame.from_dict({"a": [1, 2, 3, x]})
    df = load_features(x, path='/tmp/', filename='features.hd5')

    Direct Function Call Example
    ============================
    def load_outcomes(necessary_input=3):
        time.sleep(3)
        return pd.DataFrame.from_dict({"a": [1, 2, 3]})
    df = CacheResult(load_outcomes, path='/tmp/', necessary_input=2)
    """

    @functools.wraps(func)
    def inner(*args, path=None, filename=None, **kwargs):
        # Sometimes the user won't want to cache the run
        if path is None:
            return func(*args, **kwargs)
        if filename is None:
            filename = default_filename(func)

        path = os.path.expanduser(os.path.join(path, filename))
        without_ext, ext = os.path.splitext(path)

        arg_names = func.__code__.co_varnames[:len(args)]
        arg_with_val = '_'.join("{}{}".format(n, v) for n, v in zip(arg_names, args) if watchable(v))
        kwarg_with_val = '_'.join("{}{}".format(n, v) for n, v in kwargs.items() if watchable(v))
        path = '_'.join([without_ext, arg_with_val, kwarg_with_val, ext])
        
        is_hdf = ext in hdf_like_ext
     
        if path is None:
            raise TypeError("Must supply a valid path to the file")

        if os.path.exists(path):
            if is_hdf:
                return pd.read_hdf(path, 'Data')
            else:
                with open(path, 'rb') as f:
                    return pickle.load(f)

        result = func(*args, **kwargs)

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        if is_hdf and not hasattr(result, 'to_hdf'):
            raise TypeError("The result of {} does not have the to_hdf attribute, but the file extension ({}) suggests this is an hdf file. The extension will need to be changed to something appropriate like {}.pkl".format(func.__name__, ext, without_ext))

        if is_hdf:
            result.to_hdf(path, key='Data')
        else:
            with open(path, 'wb') as f:
                # Highest protocol will be fastest and more general
                # but it is not backwards compatible with older python versions
                pickle.dump(result, f, pickle.HIGHEST_PROTOCOL)

        return result

    if path is None:
        return inner

    return inner(*args, path=path, filename=filename, **kwargs)         

def Invalidate(cacheDir):
    """Deletes all files from a supplied directory, a.k.a. invalidates the cache at that directory.
    Usage
    =====
    @CacheResult
    def load_features(x):
        time.sleep(5)
        return pd.DataFrame.from_dict({"a": [1, 2, 3, x]})
    df = load_features(x, path='/tmp/cache/', filename='features.hd5')
    ...
    Invalidate('/tmp/cache')
    """
    cacheDir = os.path.expanduser(cacheDir)
    for filename in os.listdir(cacheDir):
        file_path = os.path.join(cacheDir, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print('Could not delete {}. {}'.format(file_path, e))


if __name__ == "__main__":
    import time

    def printDirectory(d):
        print(d)
        files = os.listdir(d)
        for f in files:
            print("\t", f)
        if len(files) == 0:
            print("\t No files")

    @CacheResult
    def LoadFeatures(x):
        time.sleep(5)
        return pd.DataFrame.from_dict({"a": [1, 2, 3, x]})

    def LoadOutcomes(ni = 3):
        time.sleep(3)
        return pd.DataFrame.from_dict({"a": [ni, ni, ni]})

    @CacheResult
    def LoadArb():
        time.sleep(2)
        return {"a": [1, 2, 3, 4]}

    print('---')
    print('Decorator Example')
    
    # The second call is much faster since the results are read from cache.
    print(LoadFeatures(4, path='/tmp/cache/'))
    print(LoadFeatures(4, path='/tmp/cache/'))
        
    print('---')
    print('Direct Function Call Example')
    
    # These first two calls generate different cache files since they 
    # accept different arguments.
    print(CacheResult(LoadOutcomes, path='/tmp/cache/', ni=2))
    print(CacheResult(LoadOutcomes, path='/tmp/cache/', ni=1))
    
    # These calls will be faster.
    print(CacheResult(LoadOutcomes, path='/tmp/cache/', ni=2))
    print(CacheResult(LoadOutcomes, path='/tmp/cache/', ni=1))

    print('---')
    print('Pickle Example')
    print(LoadArb(path='/tmp/cache/', filename='arbit.pkl'))
    print(LoadArb(path='/tmp/cache/', filename='arbit.pkl'))

    print('---')
    print('Invalidate Example')

    printDirectory('/tmp/cache/')
    Invalidate('/tmp/cache/')
    printDirectory('/tmp/cache/')

    # Finish cleanup
    os.rmdir('/tmp/cache')




