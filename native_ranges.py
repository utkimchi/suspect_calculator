#Total Point Layer (TRACK 3 DATA HERE)
uri_pl = "file:///D:/Colton_Data/Suspect_Calculator/t3_first_sus_records.csv?delimiter=%s&xField=%s&yField=%s" % (",","decimalLongitude","decimalLatitude")
total_p = QgsVectorLayer(uri_pl,"total_points","delimitedtext")
if not total_p.isValid():
    print("Point layer failed. Make sure your upload adheres to Darwin Core standards.")
    
#Ranges
nrs= "file:///D:/Colton_Data/Suspect_Calculator/native_ranges.csv?delimiter=,"
native_ranges = QgsVectorLayer(nrs,"native_ranges","delimitedtext")
if not native_ranges.isValid():
    print("Native_Ranges Failed")
    
QgsProject.instance().addMapLayer(total_p)

qgis.utils.iface.setActiveLayer(total_p)
layer = iface.activeLayer()
ids = [p.id() for p in total_p.getFeatures()]

final_layer = layer.materialize(QgsFeatureRequest().setFilterFids(ids))
QgsProject.instance().addMapLayer(final_layer) 
final_layer.setName("Final_layer")

QgsProject.instance().removeMapLayer(total_p)  

nr_dic_pn = {}
nr_dic_nat = {}

for n in native_ranges.getFeatures():
    nHuc = n['huc']
    nTaxon = n['taxon']
    nStatus = n['status']
    if nStatus == "Possibly native":
        if nHuc not in nr_dic_pn:
            nr_dic_pn[nHuc] = []
        if nTaxon not in nr_dic_pn[nHuc]:
            nr_dic_pn[nHuc].append(nTaxon)
    elif nStatus == "Native":
        if nHuc not in nr_dic_nat:
            nr_dic_nat[nHuc] = []
        if nTaxon not in nr_dic_nat[nHuc]:
            nr_dic_nat[nHuc].append(nTaxon)
        
print(nr_dic_pn['Carrizo'])
print(nr_dic_nat['Carrizo'])

final_layer.startEditing()

for p in final_layer.getFeatures():
    hucN = False
    hucPN = False
    pHuc = p['parentHuc']
    pTaxon = str(p['genus']) + " " + str(p['species'])
    if pHuc in nr_dic_pn:
        if pTaxon in nr_dic_pn[pHuc]:
            p['nativity'] = "Possibly native"
        else:
            hucPN =True
    if pHuc in nr_dic_nat:
        if pTaxon in nr_dic_nat[pHuc]:
            p['nativity'] = "Native"
        else:
            hucN = True
    if hucN and hucPN:
        p['nativity'] = "Non-Native"
    if pHuc not in nr_dic_pn and pHuc not in nr_dic_nat:
        p['nativity'] = "HUC not analyzed"
    final_layer.updateFeature(p)
final_layer.commitChanges()
        

