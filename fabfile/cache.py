class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Cache:
    __metaclass__ = Singleton
    def __init__(self):
        self._build_cache = {}

    def search_build_cache(self,package_name):
        if package_name in self._build_cache:
            # we have already installed it
            return True
        else:
            return False

    def insert_build_cache(self,package_name):
        self._build_cache[package_name] = True
