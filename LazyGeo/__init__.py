import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

def classFactory(iface):
    from .lazygeo import LazyGeoPlugin
    return LazyGeoPlugin(iface)