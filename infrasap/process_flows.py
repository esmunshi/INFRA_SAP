import sys, os

import pandas as pd
import geopandas as gpd
from geographiclib.geodesic import Geodesic
from shapely.geometry import Point, LineString
   
def get_centroid(iso,boundaries):
    try:
        selected_country = boundaries.loc[boundaries['ISO3'] == iso]
        if selected_country.shape[0] == 1:
            return(selected_country.iloc[0]['geometry'])
        elif selected_country.shape[0] > 1:
            selected_country = selected_country.sort_values('Shape_Area', ascending=False)
            return(selected_country.iloc[0]['geometry'])
        else:
            return(None)
    except:
        return(None)

def generate_great_circle(from_pt, to_pt, interim_steps=15):
    '''
    '''
    geod = Geodesic.WGS84
    g = geod.Inverse(from_pt.x, from_pt.y, to_pt.x, to_pt.y)
    l = geod.Line(g['lat1'], g['lon1'], g['azi1'])
    num = interim_steps  # 15 intermediate steps
    list_of_points = [from_pt]
    for i in range(num+1):
        pos = l.Position(i * g['s12'] / num)
        list_of_points.append(Point(pos['lat2'], pos['lon2']))
    list_of_points.append(to_pt)
    return(LineString(list_of_points))

def generate_line_string(row, type='normal'):
    try:
        if type == 'normal':
            if row['Trade Flow'] == "Export":
                return(LineString([row['Reporter_Pt'], row['Partner_Pt']]))
            else:
                return(LineString([row['Partner_Pt'], row['Reporter_Pt']]))
        elif type == 'great':
            if row['Trade Flow'] == "Export":
                return(generate_great_circle(row['Reporter_Pt'], row['Partner_Pt']))
            else:
                return(generate_great_circle(row['Partner_Pt'], row['Reporter_Pt']))
            
    except:
        #print("Error processing %s and %s" % (row['Reporter ISO'], row['Partner ISO']))
        return(None)
        
class comtrade_flow(object):
    ''' Used to process comtrade flows of energy (etc.) trade flows between countries
    
    :param: comtrade_csv - string path to the csv containing the raw comtrade results
    :param: type - string describing the type of comtrade
    
    '''
    
    def __init__(self, comtrade_csv, type, 
                 good_columns = ['Qty Unit Code','Year','Trade Flow','Reporter ISO', 'Partner ISO', 'Commodity', 'Qty', 'Trade Value (US$)','Reporter_Pt', 'Partner_Pt']
                 ):
        '''
        initiates the comtrade_flow object, see help(comtrade_flow) for more information
        '''    
        self.type = type
        self.csv_file = comtrade_csv
        self.type = type
        self.good_columns = good_columns
        self.raw_data = gpd.read_file(self.csv_file)
        self.raw_data.crs = {'init':'epsg:4326'}
            
    def initialize(self, good_quantity_code, inB, line_type="normal"):
        '''
        Read in comtrade data, filter data without units, etc.
        
        :param: good_quantity_code - array of numbers describing the values in the column 'Qty Unit Code' that are acceptable
        :param: inB - geopandas data frame of national centroids. Must contain columns "ISO3" and "geometry"
        :param: line_type - connection type between flows. Can be set to "great" to generate great circles
        '''

        good_quantity_code = [str(x) for x in good_quantity_code]
        inD = self.raw_data
        # filter out bad data
        inD = inD.loc[inD['Qty Unit Code'].isin(good_quantity_code), self.good_columns]
        inD['Reporter_Pt'] = inD['Reporter ISO'].apply(lambda x: get_centroid(x, inB))
        inD['Partner_Pt'] = inD['Partner ISO'].apply(lambda x: get_centroid(x, inB))
        #generate country flows geometry        
        country_flows = inD.loc[inD['Partner ISO'] != "WLD"]
        country_flows['geometry'] = country_flows.apply(lambda x: generate_line_string(x, line_type), axis=1)
        country_summary = inD.loc[inD['Partner ISO'] == "WLD"]
        
        # store data 
        self.complete_data = inD
        self.country_flows = country_flows
        self.country_summary = country_summary
        
    def save_individual_layers(self, out_folder, out_type="SHP"):
        '''
        Need to split the country_summary and country_flow into the various commodity types and years
        '''
        
        
    
    
    def save(self, out_folder, out_type = "CSV"):
        '''
        Save all the outputs to a folder
        
        :param: out_folder - string path to output folder; will be created if it does not exist
        :param: out_type - string to determine the format to save the results. Default is CSV, optionally "SHP"
        import fiona
        fiona.supported_drivers
        '''
        if not os.path.exists(out_folder):
            os.makedirs(out_folder)
        
        #Convert geometry columns to text
        self.country_flows['Reporter_Pt'] = self.country_flows['Reporter_Pt'].apply(str)
        self.country_flows['Partner_Pt'] = self.country_flows['Partner_Pt'].apply(str)
        for n_field in ['Trade Value (US$)', 'Qty']:
            try:
                self.country_flows[n_field] = self.country_flows[n_field].astype(float)
            except:
                self.country_flows[n_field] = self.country_flows[n_field].replace('','0').astype(float)
            try:
                self.country_summary[n_field] = self.country_summary[n_field].astype(float)
            except:
                self.country_summary[n_field] = self.country_summary[n_field].replace('','0').astype(float)
        #Convert country summary columns to geometry
        if 'Reporter_Pt' in self.country_summary.columns:
            country_summary_geom = self.country_summary['Reporter_Pt']
            self.country_summary.drop(['Reporter_Pt'], axis=1, inplace=True)
            self.country_summary['geometry'] = country_summary_geom            
        if out_type == 'CSV':
            geom_driver = "CSV"
            out_type = "csv"
            country_flows_file = os.path.join(out_folder, f"country_flows.{out_type}")        
            country_summary_file = os.path.join(out_folder, f"country_summary.{out_type}")
            self.country_flows.to_csv(country_flows_file)
            self.country_summary.to_csv(country_summary_file)
        if out_type == "SHP": 
            geom_driver = "ESRI Shapefile"
            out_type = "shp"
            country_flows_file = os.path.join(out_folder, f"country_flows.{out_type}")        
            country_summary_file = os.path.join(out_folder, f"country_summary.{out_type}")
            self.country_flows.to_file(country_flows_file)
            self.country_summary.to_file(country_summary_file)               