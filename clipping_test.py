#UTM13 Layer
huc14 = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/HUC8/HUC8_UTM14.shp","utm14","ogr")
if not huc14.isValid():
    print("huc14 not valid")
    
QgsProject.instance().addMapLayer(huc14)
    
#UTM13 Layer
tps = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/bps_utm14.shp","points","ogr")
if not tps.isValid():
    print("UTM14 not valid")

QgsProject.instance().addMapLayer(tps)

#Creates empty layer to append clipped polygons to
clipped14 = QgsVectorLayer("Polygon?crs=" + "EPSG:632614", 'clipped14','memory')
cDP = clipped14.dataProvider()
cDP.addAttributes(tps.fields())
clipped14.updateFields()

QgsProject.instance().addMapLayer(clipped14)

for huc8 in huc14.getFeatures():
    huc14G = huc8.geometry()
    huc14Name = huc8["SUBBASIN"]
    hucID = huc8.id()
    hucPoints = []
    for point in tps.getFeatures():
        pGeo = point.geometry()
        pHuc = point["huc8_name"]
        fpE = float(point["maximum_un"])
        #If point is supposed to be within HUC8  &  if point has less than 28139 meters in error (Taken from Wylie Centroid error determination) add to list 
        if(huc14G.contains(pGeo) and fpE < 28139):
            hucPoints.append(point)
    
    if(len(hucPoints) != 0 ):
        
        print(huc14Name + " has " + str(len(hucPoints)) + " point(s) within it, calculating now")
        for pp in hucPoints:
            print(pp.id())
        
        #Select Points
        tps.selectByIds([jj.id() for jj in hucPoints])
        
        #Add selected points to temporary layer
        qgis.utils.iface.setActiveLayer(tps)
        layer = iface.activeLayer()
        temp_clippingpoints = layer.materialize(QgsFeatureRequest().setFilterFids(tps.selectedFeatureIds()))
        temp_clippingpoints.setName('points to be clipped ' + huc14Name)
        QgsProject.instance().addMapLayer(temp_clippingpoints)
        
        qgis.utils.iface.setActiveLayer(huc14)
        layer = iface.activeLayer()
        huc14.selectByIds([hucID])
        temp_cHUC= layer.materialize(QgsFeatureRequest().setFilterFids(huc14.selectedFeatureIds()))
        temp_cHUC.setName('clippingHUC  ' + huc14Name)
        QgsProject.instance().addMapLayer(temp_cHUC)
        
        tcs = processing.run('native:clip',{'INPUT' : temp_clippingpoints, 'OUTPUT' : 'memory:clipped_pbh' , 'OVERLAY' : temp_cHUC})
        temp_clipped_ps = tcs['OUTPUT']
        temp_clipped_ps.setName("clipped points from " + huc14Name)
        QgsProject.instance().addMapLayer(temp_clipped_ps)
        
        
        
        
        
        
        
        