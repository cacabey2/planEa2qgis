# -*- coding: utf-8 -*-
"""planEa2qgis — QGIS eklentisi giris noktasi."""


def classFactory(iface):
    from .eklenti import PlanEa2QgisPlugin
    return PlanEa2QgisPlugin(iface)
