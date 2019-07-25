project('tango', 'cpp',
    version : '9.3.3',
    default_options : ['buildtype=release'])
# Because Windows Python ships only with optimized libs,
# we must build this project the same way.

py = import('python').find_installation('python3', modules : ['numpy'])

py_dep = py.dependency()
boost_dep = dependency('boost', modules : ['python37'])
tango_dep = dependency('tango')

numpy_inc = include_directories(py.get_path('purelib') + '/numpy/core/include')
numpy_dep = declare_dependency(
  include_directories : numpy_inc)

if py_dep.found()
  subdir('ext')
  subdir('tests')
else
  error('MESON_SKIP_TEST: Python3 libraries not found, skipping test.')
endif

# py3_pkg_dep = dependency('python3', method: 'pkg-config', required : false)
# if py3_pkg_dep.found()
#   python_lib_dir = py3_pkg_dep.get_pkgconfig_variable('libdir')
# endif
