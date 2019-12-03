#UTM14 Layer
huc14 = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/HUC8/HUC8_UTM14.shp","utm14","ogr")
if not huc14.isValid():
    print("huc14 not valid")
    
QgsProject.instance().addMapLayer(huc14)
    
#Buffered points Layer
tps = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/bps_utm14.shp","points","ogr")
if not tps.isValid():
    print("UTM14 not valid")
    
QgsProject.instance().addMapLayer(tps)

qgis.utils.iface.setActiveLayer(huc14)
layer = iface.activeLayer()

int_hs = []

for pp in tps.getFeatures():
    pp_geom = pp.geometry()
    for feat in huc14.getFeatures():
        if pp_geom.intersects(feat.geometry()):
            int_hs.append(feat["SUBBASIN"])
    
    print(int_hs)
    int_hs = []
    
unique_species = {}
    
for huc in huc14.getFeatures():
    pHuc = huc['SUBBASIN']
    if pHuc not in unique_species:
        unique_species[pHuc] = []

for point in tps.getFeatures():
    pTaxon = point['full_name']
    if pTaxon not in unique_species[pHuc]:
        unique_species[pHuc].append(pTaxon)

print(unique_species['Howard Draw'])