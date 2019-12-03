

#Total Point Layer (TRACK 3 DATA HERE)
uri_pl = "file:///D:/Colton_Data/Suspect_Calculator/test_track3.csv?delimiter=%s&xField=%s&yField=%s" % (",","decimalLongitude","decimalLatitude")
total_p = QgsVectorLayer(uri_pl,"total_points","delimitedtext")
if not total_p.isValid():
    print("Point layer failed")

QgsProject.instance().addMapLayer(total_p) 

layer = iface.activeLayer()
fields = layer.fields()
field_names = [field.name() for field in fields]

darwinCoreFields = ["catalogNumber","genus","species","decimalLatitude","decimalLongitude","coordinateUncertaintyInMeters"]
print(field_names)

darwinValid = False

for dcN in darwinCoreFields:
    if dcN not in field_names:
        print("The " + dcN + " field does not exist in the uploaded file.")
        qgis.utils.unloadPlugin('darwinCoreCheck')

if darwinValid:
    print("Valid!")
    
huc8_utm14 = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/HUC8/HUC8_UTM14.shp","huc8TX14","ogr")
if not huc8_utm14.isValid():
    print("HUC814 not valid")
    
QgsProject.instance().addMapLayer(total_p) 

