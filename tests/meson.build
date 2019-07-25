ext_dir = join_paths(meson.current_build_dir(), '../ext')
root_dir = meson.source_root()

pytest = find_program('pytest')

test('async',
  pytest,
  args : files('test_async.py'),
  env : ['PYTHONPATH=' + ext_dir + ':' + root_dir])

test('client',
  pytest,
  args : files('test_client.py'),
  env : ['PYTHONPATH=' + ext_dir + ':' + root_dir])

test('event',
  pytest,
  args : files('test_event.py'),
  env : ['PYTHONPATH=' + ext_dir + ':' + root_dir])

test('server',
  pytest,
  args : files('test_server.py'),
  env : ['PYTHONPATH=' + ext_dir + ':' + root_dir])
