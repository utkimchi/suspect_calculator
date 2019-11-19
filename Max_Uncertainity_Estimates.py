#FUNCTIONS##################################################################################################
#Creates UTM projected points
def pointSelector(utm, proj):
    print(proj)
    selection = []
    #For each point in layer, check to see if it lies within a UTM Zone
    for point in total_p.getFeatures():
        inGeom = point.geometry()
        utmgeo = utm.getFeatures()
        for cells in utmgeo:
            utmbounding = cells.geometry()
            if utmbounding.contains(inGeom):
                selection.append(point)
    #Select all points that lie within the zone
    print(len(selection))
    total_p.selectByIds([k.id() for k in selection])
    #Adds selected point as 'utm14points'
    layer = iface.activeLayer()
    new_layer_p = layer.materialize(QgsFeatureRequest().setFilterFids(total_p.selectedFeatureIds()))
    new_layer_p.setName('utmpoints')
    QgsProject.instance().addMapLayer(new_layer_p)
    parameter = {'INPUT' : new_layer_p, 'TARGET_CRS' : proj, 'OUTPUT' : 'memory:Reproject_UTM'}
    result = processing.run('native:reprojectlayer',parameter)
    QgsProject.instance().removeMapLayer(new_layer_p)
    return result['OUTPUT']

#Buffers UTM Project Points
def pointBuffer(utm_ps, utmp_name):
    mem_str = "memory:"+ str(utmp_name)
    print(mem_str)
    #Utilizes "Vector Geometry - Buffer" with variable buffer value
    buff_result = processing.run('native:buffer', {'INPUT': utm_ps, "DISTANCE":QgsProperty.fromExpression('"maximum_uncertainty_estimate"'),"OUTPUT": mem_str})
    return buff_result['OUTPUT']

def createFields(buffPs, bDP):
    #Add empty buffered area field "buff_area"
    buff_area = [QgsField('buff_area', QVariant.Double),QgsField('sus_calc',QVariant.String),QgsField('nativity',QVariant.String)]
    bDP.addAttributes(buff_area)
    buffPs.updateFields()
    
#Adds area of buffered point to attribute table and determines if a record should be omitted from calculation
def areaCalc(temp_buff, area_dic):
    temp_buff.startEditing()
    for bp in temp_buff.getFeatures():
        bp_area = bp.geometry().area()
        bp['buff_area'] = bp_area
        #Omit records that have an uncertainity larger than average huc 8 distance centroid -> edge
        if float(bp['maximum_uncertainty_estimate'] > 28139):
            bp['sus_calc'] = "Omitted"
        else:
            area_dic[bp['id']] = bp_area
        temp_buff.updateFeature(bp)
    temp_buff.commitChanges()

def clipPoints(buff_ps ,huc8_utm,cDP,clipped_ps):
    for huc8 in huc8_utm.getFeatures():
        hucGeo = huc8.geometry()
        hucName = str(huc8["SUBBASIN"])
        print(hucName)
        hucPoints = []
        for point in buff_ps.getFeatures():
            pGeo = point.geometry()
            pHuc = point["huc8_name"]
            pError = float(point["maximum_uncertainty_estimate"])
            #If point is supposed to be within HUC8  &  if point has less than 28139 meters in error (Taken from Wylie Centroid error determination) add to list 
            if(pHuc == hucName and pError < 28139):
                hucPoints.append(point)
        if(len(hucPoints) != 0 ):
            print(hucName + " has " + str(len(hucPoints)) + " point(s) within it, calculating now")

            #Add selected points to temporary layer
            qgis.utils.iface.setActiveLayer(buff_ps)
            layer = iface.activeLayer()
            
            #Select Points
            buff_ps.selectByIds([jj.id() for jj in hucPoints])
            
            temp_clippingpoints = layer.materialize(QgsFeatureRequest().setFilterFids(buff_ps.selectedFeatureIds()))
            temp_clippingpoints.setName('points to be clipped')
            QgsProject.instance().addMapLayer(temp_clippingpoints)
            
            #Select the HUC8 & Set as active layer
            print(str(huc8.id()) + " is choppin em up")
            
            qgis.utils.iface.setActiveLayer(huc8_utm)
            layer = iface.activeLayer()
            huc8_utm.selectByIds([huc8.id()])
            temp_clippinghuc = layer.materialize(QgsFeatureRequest().setFilterFids(huc8_utm.selectedFeatureIds()))
            QgsProject.instance().addMapLayer(temp_clippinghuc)
            
            tcs = processing.run('native:clip',{'INPUT' : temp_clippingpoints, 'OUTPUT' : 'memory:clipped_pbh' , 'OVERLAY' : temp_clippinghuc})
            temp_clipped_ps = tcs['OUTPUT']
            QgsProject.instance().addMapLayer(temp_clipped_ps)
            
            print(len(temp_clipped_ps))
            
            for feat in temp_clipped_ps.getFeatures():
                cDP.addFeatures([feat])
            clipped_ps.updateFields()

            QgsProject.instance().removeMapLayer(temp_clippingpoints)
            QgsProject.instance().removeMapLayer(temp_clipped_ps)
            QgsProject.instance().removeMapLayer(temp_clippinghuc)

def clAreaCalc(clip_ps, clip_dic):
    clip_ps.startEditing()
    for cp in clip_ps.getFeatures():
        cp_area = cp.geometry().area()
        cp['buff_area'] = cp_area
        clip_dic[cp['id']] = cp_area
        clip_ps.updateFeature(cp)
    clip_ps.commitChanges()
    
def areaDiff(clipped_ps,buff_areas,clipped_areas):
    bcount = 0
    clipped_ps.startEditing()
    for bps in clipped_ps.getFeatures():
        bp_id = bps['id']
        buff_area = float(buff_areas[bp_id])
        clip_area = float(clipped_areas[bp_id])
        if bcount < 10:
            print(str(clip_area) + " is the clipped value for " + str(bp_id))
            print(str(buff_area) + " is the normal value for " + str(bp_id))
            bcount += 1
        like_val = ((buff_area - clip_area )/ buff_area) * 100
        if like_val >= 25:
            bps['sus_calc'] = "Possibly Suspect"
        else:
            bps['sus_calc'] = "Not Suspect"
        clipped_areas.pop(bp_id)
        buff_areas.pop(bp_id)
        clipped_ps.updateFeature(bps)
        sus_l[bp_id] = bps['sus_calc']
    clipped_ps.commitChanges()

def firstSus(buffL):
    buffL.startEditing()
    #Adds omitted fish to the layer
    for p in buffL.getFeatures():
        p_id = p['id']
        if p_id in sus_l:
            p['sus_calc'] = sus_l[p_id]
            sus_l.pop(p_id)
            buffL.updateFeature(p)
    buffL.commitChanges()
      
def projectWGS84(buffL):
    #Return buffered point layers to WGS84 and add them to final_layer
    wsg_param = {'INPUT' : buffL, 'TARGET_CRS' : 'EPSG:4326', 'OUTPUT' : 'memory:wsg_buffs'}
    wsg_result = processing.run('native:reprojectlayer',wsg_param)
    wsg_reverse = wsg_result['OUTPUT']
    QgsProject.instance().addMapLayer(wsg_reverse)
    for feat in wsg_reverse.getFeatures():
        fldp.addFeatures([feat])
    final_layer.updateFields()
    QgsProject.instance().removeMapLayer(wsg_reverse)
    QgsProject.instance().removeMapLayer(buffL)

### MAIN ################################################################################################
#Import all UTM Vector Layers for coord projection
#UTM13 Layer
utm13 = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/Shapefiles/UTM13N.shp","utm13","ogr")
if not utm13.isValid():
    print("UTM14 not valid")
#UTM14 Layer
utm14 = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/Shapefiles/UTM14N.shp","utm14","ogr")
if not utm14.isValid():
    print("UTM14 not valid")
#UTM15 Layer
utm15 = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/Shapefiles/UTM15N.shp","utm14","ogr")
if not utm15.isValid():
    print("UTM14 not valid")    

#Total Point Layer (TRACK 3 DATA HERE)
uri_pl = "file:///D:/Colton_Data/Suspect_Calculator/track3_spec_TX.csv?delimiter=%s&xField=%s&yField=%s" % (",","longitude","latitude")
total_p = QgsVectorLayer(uri_pl,"total_points","delimitedtext")
if not total_p.isValid():
    print("Point layer failed")
     
QgsProject.instance().addMapLayer(utm13)     
QgsProject.instance().addMapLayer(utm14)
QgsProject.instance().addMapLayer(utm15)
QgsProject.instance().addMapLayer(total_p) 

#Project points to UTM 13, 14, or 15
pl_13 = pointSelector(utm13, "EPSG:32613")
pl_13.setName('utm13points')
pl_14 = pointSelector(utm14,"EPSG:32614")
pl_14.setName('utm14points')
pl_15 = pointSelector(utm15,"EPSG:32615")
pl_15.setName('utm15points')

#Add reprojected point layer (So that we can add buffer)
QgsProject.instance().addMapLayer(pl_13)
QgsProject.instance().addMapLayer(pl_14)
QgsProject.instance().addMapLayer(pl_15)

#Removes UTM Layers
QgsProject.instance().removeMapLayer(utm13)
QgsProject.instance().removeMapLayer(utm14)
QgsProject.instance().removeMapLayer(utm15)

#Buffer all UTM Point Layers
buff13 = pointBuffer(pl_13, "UTM13_Buffer")
buff14 = pointBuffer(pl_14, "UTM14_Buffer")
buff15 = pointBuffer(pl_15, "UTM15_Buffer")
dp13 = buff13.dataProvider()
dp14 = buff14.dataProvider()
dp15 = buff15.dataProvider()

#Add buffered points to map
QgsProject.instance().addMapLayer(buff13)
QgsProject.instance().addMapLayer(buff14)
QgsProject.instance().addMapLayer(buff15)

#Create generated fields "buffered area" "suspect status" "nativity"
createFields(buff13,dp13)
createFields(buff14,dp14)
createFields(buff15,dp15)

#Init dicts for comparing areas
b13_areas = {}
b14_areas = {}
b15_areas = {}

#Calculate Area of Buffered Points
areaCalc(buff13,b13_areas)
areaCalc(buff14,b14_areas)
areaCalc(buff15,b15_areas)
    
#Add in HUC8 layers
huc8_utm13 = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/HUC8/HUC8_UTM13.shp","huc8TX13","ogr")
if not huc8_utm13.isValid():
    print("HUC813 not valid")
huc8_utm14 = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/HUC8/HUC8_UTM14.shp","huc8TX14","ogr")
if not huc8_utm14.isValid():
    print("HUC814 not valid")
huc8_utm15 = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/HUC8/HUC8_UTM15.shp","huc8TX15","ogr")
if not huc8_utm15.isValid():
    print("HUC815 not valid")

QgsProject.instance().addMapLayer(huc8_utm13)
QgsProject.instance().addMapLayer(huc8_utm14)
QgsProject.instance().addMapLayer(huc8_utm15)

#Creates empty layers to append clipped polygons to
clipped13 = QgsVectorLayer("Polygon?crs=" + "EPSG:32613", 'clipped13','memory')
cdp13 = clipped13.dataProvider()
cdp13.addAttributes(buff13.fields())
clipped13.updateFields()

clipped14 = QgsVectorLayer("Polygon?crs=" + "EPSG:32614", 'clipped14','memory')
cdp14 = clipped14.dataProvider()
cdp14.addAttributes(buff14.fields())
clipped14.updateFields()

clipped15 = QgsVectorLayer("Polygon?crs=" + "EPSG:32615", 'clipped15','memory')
cdp15 = clipped15.dataProvider()
cdp15.addAttributes(buff15.fields())
clipped15.updateFields()

#Clips point if inside HUC
clipPoints(buff13,huc8_utm13,cdp13,clipped13)
clipPoints(buff14,huc8_utm14,cdp14,clipped14)
clipPoints(buff15,huc8_utm15,cdp15,clipped15)

QgsProject.instance().addMapLayer(clipped13)
QgsProject.instance().addMapLayer(clipped14)
QgsProject.instance().addMapLayer(clipped15)

#Init dict for comparing areas
cl_areas13 = {}
cl_areas14 = {}
cl_areas15 = {}

#Calculate new area for clipped guys
clAreaCalc(clipped13, cl_areas13)
clAreaCalc(clipped14, cl_areas14)
clAreaCalc(clipped15, cl_areas15)

#For adding suspect results to final point layer
sus_l = {}

#Determine if the area of the point that lies within the huc is >=75%
areaDiff(clipped13,b13_areas,cl_areas13)
areaDiff(clipped14,b14_areas,cl_areas14)
areaDiff(clipped15,b15_areas,cl_areas15)

firstSus(buff13)
firstSus(buff14)
firstSus(buff15)

### THE RESULTING LAYER OF ^^^ TEMP BUFF will have empty records for duplicates & those located in West San Antonio Bay

##HERE USE TRACK 1 & 2 Flat File!

############Determine if the fish has already been found within the huc, by checking those that are already possibly suspect
#Generate List of Unique Species for Huc
track2_data = "file:///D:/Colton_Data/Suspect_Calculator/FlatFileFOTX3-29-18.csv?delimiter=%s&xField=%s&yField=%s" % (",","longitude","latitude")
track2_p = QgsVectorLayer(track2_data,"total_points","delimitedtext")
if not track2_p.isValid():
    print("Track2 Point layer failed")
    
#Import total Huc to check for if a fish has been collected
huc8_tot = QgsVectorLayer("D:/Colton_Data/Suspect_Calculator/HUC8/HUC8_TX_cca10-10-2019.shp","huc8_total","ogr")
if not huc8_tot.isValid():
    print("HUC8tot not valid")
    
unique_species ={}
uFish = []
for huc in huc8_tot.getFeatures():
    hName = huc["SUBBASIN"]
    if hName not in unique_species:
        #Use clipped features because they will have omitted records removed
        for pn in track2_p.getFeatures():
            if pn["full_name"] not in uFish and pn["huc8_name"] == hName:
                uFish.append(pn["full_name"])
        unique_species[hName] = uFish  
    uFish = []
    
print(unique_species['Howard Draw'])

QgsProject.instance().removeMapLayer(clipped13)
QgsProject.instance().removeMapLayer(clipped14)
QgsProject.instance().removeMapLayer(clipped15)


final_layer = QgsVectorLayer("Polygon?crs=" + "EPSG:4326", 'final_layer','memory')
fldp = final_layer.dataProvider()
fldp.addAttributes(buff15.fields())
final_layer.updateFields()


projectWGS84(buff13)
projectWGS84(buff14)
projectWGS84(buff15)

QgsProject.instance().removeMapLayer(huc8_utm13)
QgsProject.instance().removeMapLayer(huc8_utm14)
QgsProject.instance().removeMapLayer(huc8_utm15)


#For any point already "Possibly Suspect" Clip the hucs underneath to a memory layer then check if taxon in buffered point is in all of the hucs
qgis.utils.iface.setActiveLayer(huc8_tot)
layer = iface.activeLayer()
#HUCS underneath
int_hs = []
final_layer.startEditing()
for pp in final_layer.getFeatures():
    if pp['sus_calc'] == "Possibly Suspect":
        pp_geom = pp.geometry()
        pp_taxon = pp['full_name']
        for feat in huc8_tot.getFeatures():
            if pp_geom.intersects(feat.geometry()):
                int_hs.append(feat["SUBBASIN"])
        #Checks list of unique species for each huc that it intersected with
        for huc in int_hs:
            if pp_taxon not in unique_species[huc]:
                pp['sus_calc'] = "New Suspect"
                break
            else:
                pp['sus_calc'] = "Not Suspect (UTM-TX EDGE)"
        final_layer.updateFeature(pp)
    int_hs = []
final_layer.commitChanges()

QgsProject.instance().addMapLayer(huc8_tot)
QgsProject.instance().addMapLayer(final_layer)

QgsProject.instance().removeMapLayer(pl_13)
QgsProject.instance().removeMapLayer(pl_14)
QgsProject.instance().removeMapLayer(pl_15)

