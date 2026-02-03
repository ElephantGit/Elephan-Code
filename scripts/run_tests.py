import importlib

mod = importlib.import_module('tests.test_trajectory')

failures = []
for name in dir(mod):
    if name.startswith('test_'):
        func = getattr(mod, name)
        try:
            print(f"Running {name}...")
            func()
            print(f"{name}: OK")
        except Exception as e:
            print(f"{name}: FAIL -> {e}")
            failures.append((name, e))

if failures:
    print('\nSome tests failed:')
    for n, e in failures:
        print(n, e)
    raise SystemExit(1)
else:
    print('\nAll tests passed')
