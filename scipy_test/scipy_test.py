import os

def remove_ignored_patterns(files,pattern):
    from fnmatch import fnmatch
    good_files = []
    for file in files:
        if not fnmatch(file,pattern):
            good_files.append(file)
    return good_files        
    
def remove_ignored_files(original,ignored_files,cur_dir):
    """ This is actually expanded to do pattern matching.
    
    """
    if not ignored_files: ignored_files = []
    ignored_modules = map(lambda x: x+'.py',ignored_files)
    ignored_packages = ignored_files[:]
    # always ignore setup.py and __init__.py files
    ignored_files = ['setup.py','setup_*.py','__init__.py']
    ignored_files += ignored_modules + ignored_packages
    ignored_files = map(lambda x,cur_dir=cur_dir: os.path.join(cur_dir,x),
                        ignored_files)
    #print 'ignored:', ignored_files    
    #good_files = filter(lambda x,ignored = ignored_files: x not in ignored,
    #                    original)
    good_files = original
    for pattern in ignored_files:
        good_files = remove_ignored_patterns(good_files,pattern)
        
    return good_files
                            
def harvest_modules(package,ignore=None):
    """* Retreive a list of all modules that live within a package.

         Only retreive files that are immediate children of the
         package -- do not recurse through child packages or
         directories.  The returned list contains actual modules, not
         just their names.
    *"""
    import os,sys

    d,f = os.path.split(package.__file__)

    # go through the directory and import every py file there.
    import glob
    common_dir = os.path.join(d,'*.py')
    py_files = glob.glob(common_dir)
    #py_files.remove(os.path.join(d,'__init__.py'))
    #py_files.remove(os.path.join(d,'setup.py'))
        
    py_files = remove_ignored_files(py_files,ignore,d)
    #print 'py_files:', py_files
    try:
        prefix = package.__name__
    except:
        prefix = ''
                
    all_modules = []
    for file in py_files:
        d,f = os.path.split(file)
        base,ext =  os.path.splitext(f)        
        mod = prefix + '.' + base
        #print 'module: import ' + mod
        try:
            exec ('import ' + mod)
            all_modules.append(eval(mod))
        except:
            print 'FAILURE to import ' + mod
            output_exception()                
        
    return all_modules

def harvest_packages(package,ignore = None):
    """ Retreive a list of all sub-packages that live within a package.

         Only retreive packages that are immediate children of this
         package -- do not recurse through child packages or
         directories.  The returned list contains actual package objects, not
         just their names.
    """
    import os,sys
    join = os.path.join

    d,f = os.path.split(package.__file__)

    common_dir = os.path.abspath(d)
    all_files = os.listdir(d)
    
    all_files = remove_ignored_files(all_files,ignore,'')
    #print 'all_files:', all_files
    try:
        prefix = package.__name__
    except:
        prefix = ''
    all_packages = []
    for directory in all_files:        
        path = join(common_dir,directory)
        if os.path.isdir(path) and \
           os.path.exists(join(path,'__init__.py')):
            sub_package = prefix + '.' + directory
            #print 'sub-package import ' + sub_package
            try:
                exec ('import ' + sub_package)
                all_packages.append(eval(sub_package))
            except:
                print 'FAILURE to import ' + sub_package
                output_exception() 
    return all_packages

def harvest_modules_and_packages(package,ignore=None):
    """ Retreive list of all packages and modules that live within a package.

         See harvest_packages() and harvest_modules()
    """
    all = harvest_modules(package,ignore) + harvest_packages(package,ignore)
    return all

def harvest_test_suites(package,ignore = None):
    import unittest
    suites=[]
    test_modules = harvest_modules_and_packages(package,ignore)
    #for i in test_modules:
    #    print i.__name__
    for module in test_modules:
        if hasattr(module,'test_suite'):
            try:
                suite = module.test_suite()
                if suite:
                    suites.append(suite)    
                else:
                    msg = "    !! FAILURE without error - shouldn't happen" + \
                          module.__name__                
                    print msg
            except:
                print '   !! FAILURE building test for ', module.__name__                
                print '   ',
                output_exception()            
        else:
            print 'No test suite found for ', module.__name__
    total_suite = unittest.TestSuite(suites)
    return total_suite

def module_test(mod_name,mod_file):
    """*

    *"""
    import os,sys,string
    #print 'testing', mod_name
    d,f = os.path.split(mod_file)

    # add the tests directory to the python path
    test_dir = os.path.join(d,'tests')
    sys.path.append(test_dir)

    # call the "test_xxx.test()" function for the appropriate
    # module.

    # This should deal with package naming issues correctly
    short_mod_name = string.split(mod_name,'.')[-1]
    test_module = 'test_' + short_mod_name
    test_string = 'import %s;reload(%s);%s.test()' % \
                  ((test_module,)*3)

    # This would be better cause it forces a reload of the orginal
    # module.  It doesn't behave with packages however.
    #test_string = 'reload(%s);import %s;reload(%s);%s.test()' % \
    #              ((mod_name,) + (test_module,)*3)
    exec(test_string)

    # remove test directory from python path.
    sys.path = sys.path[:-1]

def module_test_suite(mod_name,mod_file):
    #try:
        import os,sys,string
        print ' creating test suite for:', mod_name
        d,f = os.path.split(mod_file)

        # add the tests directory to the python path
        test_dir = os.path.join(d,'tests')
        sys.path.append(test_dir)

        # call the "test_xxx.test()" function for the appropriate
        # module.

        # This should deal with package naming issues correctly
        short_mod_name = string.split(mod_name,'.')[-1]
        test_module = 'test_' + short_mod_name
        test_string = 'import %s;reload(%s);suite = %s.test_suite()' % ((test_module,)*3)
        #print test_string
        exec(test_string)

        # remove test directory from python path.
        sys.path = sys.path[:-1]
        return suite
    #except:
    #    print '    !! FAILURE loading test suite from', test_module, ':'
    #    print '   ',
    #    output_exception()            


# Utility function to facilitate testing.

def assert_equal(actual,desired,err_msg='',verbose=1):
    """ Raise an assertion if two items are not
        equal.  I think this should be part of unittest.py
    """
    msg = '\nItems are not equal:\n' + err_msg
    try:
        if ( verbose and len(str(desired)) < 100 and len(str(actual)) ):
            msg =  msg \
                 + 'DESIRED: ' + str(desired) \
                 + '\nACTUAL: ' + str(actual)
    except:
        msg =  msg \
             + 'DESIRED: ' + str(desired) \
             + '\nACTUAL: ' + str(actual)
    assert desired == actual, msg

def assert_almost_equal(actual,desired,decimal=7,err_msg='',verbose=1):
    """ Raise an assertion if two items are not
        equal.  I think this should be part of unittest.py
    """
    msg = '\nItems are not equal:\n' + err_msg
    try:
        if ( verbose and len(str(desired)) < 100 and len(str(actual)) ):
            msg =  msg \
                 + 'DESIRED: ' + str(desired) \
                 + '\nACTUAL: ' + str(actual)
    except:
        msg =  msg \
             + 'DESIRED: ' + str(desired) \
             + '\nACTUAL: ' + str(actual)
    assert round(abs(desired - actual),decimal) == 0, msg

try:
    # Numeric specific tests
    from Numeric import *
    from fastumath import *
    
    def assert_array_equal(x,y,err_msg=''):
        msg = '\nArrays are not equal'
        try:
            assert alltrue(equal(shape(x),shape(y))),\
                   msg + ' (shapes mismatch):\n\t' + err_msg
            reduced = equal(x,y)
            assert alltrue(ravel(reduced)),\
                   msg + ':\n\t' + err_msg
        except ValueError:
            print shape(x),shape(y)
            raise ValueError, 'arrays are not equal'
    
    def assert_array_almost_equal(x,y,decimal=6,err_msg=''):
        msg = '\nArrays are not almost equal'
        try:
            assert alltrue(equal(shape(x),shape(y))),\
                   msg + ' (shapes mismatch):\n\t' + err_msg
            reduced = equal(around(abs(x-y),decimal),0)
            assert alltrue(ravel(reduced)),\
                   msg + ':\n\t' + err_msg
        except ValueError:
            print sys.exc_value
            print shape(x),shape(y)
            print x, y
            raise ValueError, 'arrays are not almost equal'
except:
    pass # Numeric not installed
    
import traceback,sys
def output_exception():
    try:
        type, value, tb = sys.exc_info()
        info = traceback.extract_tb(tb)
        #this is more verbose
        #traceback.print_exc()
        filename, lineno, function, text = info[-1] # last line only
        print "%s:%d: %s: %s (in %s)" %\
              (filename, lineno, type.__name__, str(value), function)
    finally:
        type = value = tb = None # clean up
