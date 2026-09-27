from .sector.__main__ import *
from .ticker.__main__ import *
from .tickers.__main__ import *
from .to_dict.__main__ import *
from .to_report.__main__ import *

# import importlib
# import os
#
# if __name__ != "__main__":
#     # print(sys.modules[__name__].sector)
#     for path in os.listdir(__path__[0]):
#         if not os.path.isdir(path) or "_" in path: continue
#         print(path)
#         submodule = importlib.import_module(f".{path}.__main__", __name__)
#         globals()[path] = getattr(submodule, path)
