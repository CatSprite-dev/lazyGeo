def classFactory(iface):
    from .lazygeo import LazyGeoPlugin
    return LazyGeoPlugin(iface)
