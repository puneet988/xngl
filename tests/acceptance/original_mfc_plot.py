"""Plot part of MFC_diff_INDIA.py (plot_VIMFC_wind/MF_850hPa/INDIA), copied unchanged from
the line '#;;;;;;; Plotting' to the end, for the acceptance comparison with xngl.

Only the setup above the copied part is new: synthetic data instead of cdms2 reads, PyNGL's
sample shapefile instead of the India shapefiles, and res_factor 1500 instead of 8200.
Run from an output folder: python original_mfc_plot.py  -> mfc_new850_INDIA_JJAS.png
"""
# ruff: noqa
import json
from pathlib import Path

import ngl
import numpy
import Ngl, Nio

ind_to_use = 2
p_in_hpa = "850 hPa"
SHP = str(Path(ngl.__file__).parent / "ncarg/data/shp") + "/"
shapefile_path = shapefile_path_CI = SHP
shapefile_name = shapefile_name_CI = "states.shp"
varlist = ['PD_05-PI_05', 'SULPHATE_2X-PI_05', 'BC_5X-PI_05', 'DUST_2X-PI_05']
new_vars_list = ["mfc_adv_new850", "mfc_con_new850", "mfc_new850"]
Lat = numpy.arange(-2.0, 42.1, 0.95)
Lon = numpy.arange(59.0, 101.1, 1.25)
_lon2, _lat2 = numpy.meshgrid(Lon, Lat)
units_to_use = "kg/m2/s"
diff_dict = {v: 20e-5 * numpy.sin(numpy.radians(_lon2 * 4 + 40 * k)) * numpy.cos(numpy.radians(_lat2 * 4)) * 100000
             for k, v in enumerate(varlist)}

#;;;;;;; Plotting

string_font = "helvetica-bold"

if ind_to_use == 0: # imfc_adv
    minmax1 = numpy.linspace(-10.0,10.0,41)
elif ind_to_use == 1: # imfc_con
    minmax1 = numpy.linspace(-24.0,24.0,41)
elif ind_to_use == 2: # VIMFC
    minmax1 = numpy.linspace(-24.0,24.0,41)
else:
    pass









#----------------------------------------------------------------------
# This function attaches outlines from the given shapefile to the plot.
#----------------------------------------------------------------------


def add_shapefile_outlines(wks,plot,shp_path,shp_filename,color="black",ThicknessF=1.0):
#---Read data off shapefile
    f        = Nio.open_file(shp_path + shp_filename, "r")
    lon_shp      = numpy.ravel(f.variables["x"][:])
    lat_shp      = numpy.ravel(f.variables["y"][:])

    plres                  = Ngl.Resources()      # resources for polylines
    plres.gsLineColor      = color                # default is black
    plres.gsSegments       = f.variables["segments"][:,0]
    plres.gsLineThicknessF = ThicknessF           # default is 1.0
    plres.gsEdgesOn        = True
    plres.gsEdgeColor      = color

    return Ngl.add_polyline(wks, plot, lon_shp, lat_shp, plres)


def add_box_outlines(wks, plot, minlon=0, minlat=0, maxlon=0, maxlat=0, color="black", ThicknessF=1.0):

    #minlon = 70.
    #minlat = 20.
    #maxlon = 80.
    #maxlat = 30.

    x = [ minlon, maxlon, maxlon, minlon, minlon ]
    y = [ minlat, minlat, maxlat, maxlat, minlat ]

    plres                  = Ngl.Resources()      # resources for polylines
    plres.gsLineColor      = color                # default is black
    plres.gsLineThicknessF = ThicknessF           # default is 1.0
    plres.gsEdgesOn        = True
    plres.gsEdgeColor      = color

    return Ngl.add_polyline(wks, plot, x, y, plres)







def new_labels_for_lat_lon(wks, x_min, x_max, x_spacing, y_min, y_max, y_spacing, list_of_plots):
    x_axis = numpy.arange(x_min,x_max,x_spacing)
    y_axis = numpy.arange(y_min,y_max,y_spacing)
    x_axis_str = [str(i)+"E" for i in x_axis]
    y_axis_str = [str(i) if i==0 else str(i)+"S" if i<0 else str(i)+"N" for i in y_axis]

    for indx1, map1 in enumerate(list_of_plots):
        bres = Ngl.Resources()
        bres.vpXF      = Ngl.get_float(map1,"vpXF")
        bres.vpYF      = Ngl.get_float(map1,"vpYF")
        bres.vpHeightF = Ngl.get_float(map1,"vpHeightF")
        bres.vpWidthF  = Ngl.get_float(map1,"vpWidthF" )

        bres.trXMinF   = Ngl.get_float(map1,"trXMinF")
        bres.trXMaxF   = Ngl.get_float(map1,"trXMaxF")
        bres.trYMinF   = Ngl.get_float(map1,"trYMinF")
        bres.trYMaxF   = Ngl.get_float(map1,"trYMaxF")

        bres.nglPointTickmarksOutward = True

        bres.tmXBMode                = "Explicit"
        bres.tmXBValues              = x_axis
        bres.tmXBLabels              = x_axis_str


        bres.tmYLMode                = "Explicit"
        bres.tmYLValues              = y_axis
        bres.tmYLLabels              = y_axis_str

        bres.tmXBMinorOn                      = False
        bres.tmYLMinorOn                      = False
        bres.tmXTMinorOn                      = False
        bres.tmYRMinorOn                      = False
        bres.tmLabelAutoStride                = True
        bres.tmBorderThicknessF               = 2
        bres.tmXBMajorThicknessF              = 1.3
        bres.tmYLMajorThicknessF              = 1.3

        bres.tmXBMajorLengthF                 = -.015
        bres.tmYLMajorLengthF                 = -.015
        bres.tmXTMajorLengthF                 = -.015
        bres.tmYRMajorLengthF                 = -.015
        bres.tmXBMinorLengthF                 = -.0055

        bres.tmXBLabelFont                    =  string_font
        bres.tmYLLabelFont                    =  string_font
        bres.tmXBLabelFontHeightF             =  .03
        bres.tmYLLabelFontHeightF             =  .03



        if indx1 == 0:
            bres.tmXBLabelsOn = True
            bres.tmYLLabelsOn = True
        else:
            bres.tmXBLabelsOn = True
            bres.tmYLLabelsOn = False

        bres.tfDoNDCOverlay          = True

        blank = Ngl.blank_plot(wks,bres)
        Ngl.overlay(map1.base,blank)

    return None



def create_manual_labelbar(wks, plots_list, labels, vpWidth, vpHeight, xpos, ypos, lb_string):

    colors1 = Ngl.get_string_array(plots_list[0].contour,"cnFillColors")[:]

    lres                                       = Ngl.Resources()
    lres.vpWidthF                              = vpWidth           # lengthwise
    lres.vpHeightF                             = vpHeight             # breadthwise
    lres.lbPerimOn                             = False            # Turn off perimeter.
    lres.lbOrientation                         = "Horizontal"     # Default is vertical.
    lres.lbBoxLineThicknessF                   = 0.0
    lres.lbBoxLinesOn                          = False
    lres.lbPerimOn                             = False
    lres.lbPerimThicknessF                     = 0.0
    lres.lbRasterFillOn                        = True

    lres.lbLabelAlignment                      = "ExternalEdges"  # Default is "BoxCenters".
    lres.lbBoxEndCapStyle                      = "TriangleBothEnds"
    lres.lbFillColors                          = colors1
    lres.lbMonoFillPattern                     = True             # Fill them all solid.
    lres.lbLabelFontHeightF                    = 0.013            # label font height
    lres.lbLabelFont                           = string_font # Labelbar font
    lres.lbLabelAutoStride                     = False
    lres.lbTitleOn                             = True
    lres.lbTitleFont                           = string_font
    lres.lbTitleFontHeightF                    = 0.013
    lres.lbTitlePosition                       = "Top"
    lres.lbTitleOffsetF                        = 0.15
    lres.lbTitleString                         = lb_string  #(g/m~S~2~N~)"
    lres.lbLabelAngleF                         = 45
    Ngl.labelbar_ndc(wks,len(colors1),labels,xpos,ypos,lres)  #X-horizontally y-vertically

    return None

def panelling_resources(wks, plot_list, rows, columns):

    panelres                                   = Ngl.Resources()
    panelres.nglFrame                          = False
    panelres.nglDraw                           = True

    panelres.nglPaperOrientation               = "portrait"
    #panelres.nglPanelRight                     = 0.98
    #panelres.nglPanelBottom                    = 0.06
    panelres.nglPanelCenter                    = False
    #panelres.nglPanelYWhiteSpacePercent        = 20
    #panelres.nglPanelXWhiteSpacePercent        = 6

    Ngl.panel(wks,plot_list[:],[rows,columns],panelres)

    return None


res_factor = 1500.0

def plot_function(wks, data_list_of_arrays):   #######################
    # Plotting
    #######################

    plot1                                        = []
    plot                                        = []

    resources                                   = Ngl.Resources()

    def ngl_resources():

        resources.nglDraw                       = False
        resources.nglFrame                      = False
        resources.nglPaperOrientation           = "portrait"
        resources.nglMaximize                   = False

        return None

    ngl_resources()



    def contour_resources():
        resources.cnFillOn                      = True    # Turn on contour fill.
        resources.cnLineLabelsOn                = False   # Turn off contour labels
        resources.cnLinesOn                     = False
        resources.cnInfoLabelOn                 = False
        #resources.cnLabelBarEndStyle            = "ExcludeOuterBoxes"
        resources.cnFillPalette                 = "BlueYellowRed"
        resources.cnFillMode                    = "RasterFill"    # Use smooth raster contours
        resources.cnMaxLevelCount               = 255
        resources.cnRasterSmoothingOn           = True
        resources.cnRasterCellSizeF             = 1.0/res_factor
        resources.cnLevelSelectionMode          = "ExplicitLevels"      #-- define your own contour levels
        #resources.cnLevels                      = numpy.linspace(-60,60,13)
        #resources.cnMinLevelValF                =  -1.                 #-- minimum contour value
        #resources.cnMaxLevelValF                =  1.                 #-- maximum contour value
        #resources.cnLevelSpacingF               =  0.1                 #-- contour increment

        return None

    contour_resources()


    def map_resources():

        #-- map resources
        resources.mpFillOn                      =  False                  #-- don't use filled map
        resources.mpGridAndLimbOn               =  False                  #-- don't draw grid lines
        resources.mpLimitMode                   = "LatLon"                      #-- change the area of the map
        resources.mpMinLatF                     =  0.0                         #-- minimum latitude
        resources.mpMaxLatF                     =  40.0                         #-- maximum latitude
        resources.mpMinLonF                     =  60.                         #-- minimum longitude
        resources.mpMaxLonF                     =  100.                          #-- minimum longitude
        resources.mpOutlineOn                   = False
        #res.mpOutlineBoundarySets              ="NoBoundaries"

        resources.sfXCStartV                    =  float(min(Lon))   #-- x-axis location of 1st element lon
        resources.sfXCEndV                      =  float(max(Lon))   #-- x-axis location of last element lon
        resources.sfYCStartV                    =  float(min(Lat))   #-- y-axis location of 1st element lat
        resources.sfYCEndV                      =  float(max(Lat))   #-- y-axis location of last element lat

        return None

    map_resources()




    def plot_manager_resources():

        resources.pmLabelBarDisplayMode             = "Never"
        resources.pmTickMarkDisplayMode             = "Never"

        return None

    plot_manager_resources()



    def title_resources():
        resources.tiMainFont                        = string_font
        return None

    title_resources()



    def add_titles_to_panels():
        labels_list = ['PD-PI', 'SULPHATE_2X-PI', 'BC_5X-PI', 'DUST_2X-PI']

        textres                                     =  Ngl.Resources()

        textres.txFontHeightF                       =  0.014                  #-- title string size
        textres.txFont                              = string_font

        Ngl.text_ndc(wks, labels_list[0],0.144, 0.61,textres) # X-horizontal Y-vertical
        Ngl.text_ndc(wks, labels_list[1],0.39, 0.61,textres)
        Ngl.text_ndc(wks, labels_list[2],0.64, 0.61,textres)
        Ngl.text_ndc(wks, labels_list[3],0.886, 0.61,textres)

        Ngl.text_ndc(wks, 'a)',0.048, 0.61,textres) # X-horizontal Y-vertical
        Ngl.text_ndc(wks, 'b)',0.295, 0.61,textres)
        Ngl.text_ndc(wks, 'c)',0.545, 0.61,textres)
        Ngl.text_ndc(wks, 'd)',0.795, 0.61,textres)


        return None

    add_titles_to_panels()


    for key, arr in data_list_of_arrays.items():

        resources.cnLevels      =  minmax1

        resources.tiMainFontHeightF = 0.032
        resources.tiMainString  = ""

        plot.append(Ngl.contour_map(wks,arr,resources))


    new_labels_for_lat_lon(wks, 60, 101, 10, 0, 41, 5, plot) # new_labels_for_lat_lon(wks, x_min, x_max, x_spacing, y_min, y_max, y_spacing, list_of_plots):


    global labels_for_colorbar1

    # labels_for_colorbar12 = [""] + [str(numpy.round(float(i),5)) for i in minmax1] + [""]
    labels_for_colorbar12 = [""] + [str(int(i)) for i in minmax1] + [""]
    labels_for_colorbar1 = ["" if k%2==0 else val for  k, val in enumerate(labels_for_colorbar12)]
    lb_label_list = ["MFC advection", "MFC convergence", "MFC"]
    create_manual_labelbar(wks, plot[0:3], labels_for_colorbar1, vpWidth=0.985, vpHeight=0.04, xpos=0.02, ypos=0.3, lb_string=lb_label_list[ind_to_use]+" at "+ p_in_hpa+" ("+units_to_use+") X ~F22~10~S~-5~N")


    final_plot_with_shpfile                                  = []

    for ijq in plot:
        final_plot_with_shpfile.append(add_shapefile_outlines(wks,ijq,shapefile_path,shapefile_name,color="black",ThicknessF=7.0))

    final_plot_with_box                                       = []

    for ijq in plot:
        final_plot_with_box.append(add_shapefile_outlines(wks,ijq,shapefile_path_CI,shapefile_name_CI,color="darkorchid4",ThicknessF=15.0))


    panelling_resources(wks, plot, 1, 4)

    return None


#--- Indicate where to send graphics

rlist = Ngl.Resources()
# rlist.wkOrientation = "portrait"
# rlist.wkPaperWidthF  =  40.0  # in inches
# rlist.wkPaperHeightF = 40.0  # in inches
# wks_type = "pdf"



rlist.wkWidth  =  res_factor  # in inches
rlist.wkHeight = res_factor  # in inches
wks_type = "png"




wks1 = Ngl.open_wks(wks_type,new_vars_list[ind_to_use]+'_INDIA_JJAS',rlist)


plot_function(wks1, diff_dict)


Ngl.frame(wks1)


json.dump({"levels": [float(v) for v in minmax1], "nplots": len(diff_dict)}, open("original_info.json", "w"))

Ngl.end()


