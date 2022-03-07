# -*- coding: utf-8 -*-
"""
Created on Tue Feb 15 15:27:10 2022

@author: RNA238
"""

import pandas as pd
import numpy as np
import time
import streamlit as st
from PIL import Image
import matplotlib.pyplot as plt
from azure.storage.blob import BlobServiceClient
from io import StringIO
from datetime import datetime


st.set_option('deprecation.showPyplotGlobalUse', False)
pd.set_option("display.max_rows", 5000)
pd.set_option("display.max_columns", 500)



# =====================================================
# Data Frame from azure blob storage
# =====================================================
@st.cache(suppress_st_warning=True,allow_output_mutation=True)
def fetching_data_from_azurecloud():
    t1=time.time()
    storage_account_url= 'https://stgazewdinlandpriwrkbnc.blob.core.windows.net'
    storage_account_key= 'Gkf6ADrA8Neuhoh/yv6wxJdIVQwBJqSk5PAmhGiXUONJ+hNMws7ol7xhBQtC4pqnpJ1sOVHyUh/SkvG3JdrfTw=='
    container_name = 'dnddata'
    blob_name = 'df_fte_spot_' + datetime.now().strftime('%d%b%Y') + '.csv'
    #blob_name = 'df_fte_spot_28Feb2022.csv'


    blob_service_client = BlobServiceClient(account_url=storage_account_url,credential=storage_account_key)
    blob_client_instance = blob_service_client.get_blob_client(container_name, blob_name)
    blob_data = blob_client_instance.download_blob()

    df = pd.read_csv(StringIO(blob_data.content_as_text()))
    print(df)
    t2=time.time()
    print(("It takes %s seconds to download "+blob_name) % (t2 - t1))
    return df


def main():
    def newfte(days):
        slabenddays = slabs_end_day
        for slabend in slabenddays:
            if(days<=int(slabend)):
                return slabend
            else:
                pass
    
    def montecarlosimualtion(data2, containersize, num_slab, slab_end_days, slab_rates, num_simulations):
        
        
        # =========================================
        # Function to calculate the total rates for FTE taken
        # =========================================
        def ratefun(day,daytemp = 0):
            if(day>int(slab_end_days[-1])):
                return 0
            
            total_rate1 = 0
            for days,rates in zip(slab_end_days,slab_rates):
                days = int(days)
                rates = int(rates)
                days1 = days - daytemp 
                total_rate = rates*days1
                total_rate1 = total_rate1 + total_rate
                
                if(day<=days):
                    return total_rate1
                daytemp = days  
        
        # =========================================
        # Dataframe holiding data of equipments its FTE_Taken and FTE_Amount
        # =========================================
        data2 = data2[['Equipment_No','FTE_Taken','FTE_Amount']]
        
        
        # =========================================
        # Calculation of the proposition 
        # =========================================
        calprop = 'y'
        if(calprop=='y'):
            data1prop = data2.groupby('FTE_Taken',as_index=False).sum()
            data1prop = data1prop.merge(data2[['Equipment_No','FTE_Taken']].groupby('FTE_Taken',as_index=False).count(),
                            on='FTE_Taken')
        
            data1prop['Equipment_No_props'] = 0
            data1prop['FTE_Amount_props'] = np.nan
        
            data1prop.loc[(data1prop['Equipment_No']==True)==False,'Equipment_No_props'] = round((data1prop['Equipment_No']/sum(data1prop['Equipment_No'])),3)
            data1prop.loc[(data1prop['FTE_Amount']==True)==False,'FTE_Amount_props'] = (data1prop['FTE_Amount']/sum(data1prop['FTE_Amount']))
        
        
            # =========================================
            # If the FTE of a particular day is not available, it will add the FTE day and its proposition as '0'
            # =========================================
            if(len(data1prop)<14):
                missingfte = []
                for FTE in range(1,15):
                    if FTE not in list(data1prop['FTE_Taken']):
                        missingfte.append(FTE)
        
                print('\nThe FTE missing from the data is/are ::',missingfte)
        
                for missing in missingfte:
                    data12prop =pd.DataFrame(data=[[missing,0,0,0,0]],columns =['FTE_Taken', 'FTE_Amount', 'Equipment_No',
                           'Equipment_No_props', 'FTE_Amount_props'])
        
                    data1prop = data12prop.append(data1prop).sort_values(by='FTE_Taken') 
                    
                
        data1prop = data1prop.reset_index().drop('index',axis=1)
        propdelta = 1 - sum(data1prop['Equipment_No_props'])
        print('sumpropdelta############',sum(data1prop['Equipment_No_props']))
        print('propdelta############',propdelta)
        maxprop = data1prop['Equipment_No_props'].max()
        data1prop.loc[data1prop['Equipment_No_props']==maxprop,'Equipment_No_props'] = data1prop['Equipment_No_props'] + propdelta
                    
        # =========================================
        # Input from the user for the number of container/equipments to be considered for simulation
        # =========================================
        #Input 2
        
        # if(container_counts=='y'):
        #     pass
        #     #container_count = int(input('Please enter the value of number of containers to be considered for simulation ::'))
        # else:
        #     container_count = len(data)
            
        container_count = len(data2)
    
        # =========================================
        # Execution of the simualtion
        # =========================================
        num_reps = container_count
        all_stats = []
        for simualtion in range(num_simulations):
            FTE_target_values = list(range(1,15))
            FTE_target_probs = list(data1prop['Equipment_No_props'])
            FTE_target = np.random.choice(FTE_target_values, num_reps, p=FTE_target_probs)
        
            data = pd.DataFrame(index=range(num_reps), data={'FTE_Days': FTE_target})
        
            data['RateSlab'] = np.nan
            data['RateSlab'] = data['FTE_Days'].astype(int).apply(ratefun)
            
            all_stats.append([data['RateSlab'].sum().round(0),len(data),simualtion])
        
            
        results_data = pd.DataFrame.from_records(all_stats, columns=['Revenue','Equipments','Simulation'])
        #results_data.head()
        
        print('\n Simulation Completed')
        print('\n The original revenue was::',sum(data2['FTE_Amount']),' USD')
        print('\n The average revenue for the above simulation is::',results_data['Revenue'].mean(),' USD')
        
        pincreace = round(((results_data['Revenue'].mean()/sum(data2['FTE_Amount']))*100)-100,2)
        print('\n Percentage increase/decrease in the revenue is::',pincreace,'%')
        
        full_result = [sum(data2['FTE_Amount']), results_data['Revenue'].mean(), pincreace]
        return full_result
    
    
    data1 = pd.read_csv('df_fte_spot.csv')
    #data1 = fetching_data_from_azurecloud()
    
    data1[['Tariff_Geosite_Cd','Activity_Geosite_Cd','Shipment_No','Equipment_No','FTE_Currency','CommoditySubType_Dsc',
           'Freight_Type_Dsc','Freight_Type_Cd','EquipmentSize_Cd','Equipment_SubType_Dsc','Shipment_Status_Dsc','Rate_Bases', 
           'Brand_Dsc']] = data1[['Tariff_Geosite_Cd','Activity_Geosite_Cd','Shipment_No','Equipment_No','FTE_Currency',
            'CommoditySubType_Dsc','Freight_Type_Dsc','Freight_Type_Cd','EquipmentSize_Cd','Equipment_SubType_Dsc',
            'Shipment_Status_Dsc','Rate_Bases','Brand_Dsc']].astype(str).fillna('Nulled')
    
    
    data1[['Total_Freetimegranted_Days','FTE_Taken',
           'Actual_Turntime_Days']] = data1[['Total_Freetimegranted_Days','FTE_Taken','Actual_Turntime_Days']].astype(int).fillna(0)
    
    data1[['FTE_Amount','Invoiced_Amount',
           'Waived_Amount']] = data1[['FTE_Amount','Invoiced_Amount','Waived_Amount']].astype(float).fillna(0)
    
    datecolumns = ['Discharge_Date','Freetime_Startdate','Freetime_Enddate','Charge_End_Date']
    data1[datecolumns] = data1[datecolumns].fillna('')
    
    for datecolumn in datecolumns:
        #print(datecolumn)
        data1[datecolumn] = pd.to_datetime(data1[datecolumn])
        
    data1['Calculation_Month'] = pd.to_datetime(data1['Calculation_Month'],format='%b-%y')
    month_list = list(data1['Calculation_Month'].unique())
    month_list.sort()
        
    data1['Country_Cd'] = data1['Tariff_Geosite_Cd'].apply(lambda x:x[:2])
    data1['FTE_Perday'] = round(data1['FTE_Amount']/data1['FTE_Taken'])
    #data1 = data1.rename(columns={'Free_Timegranted_Days':'Total_Freetimegranted_Days'})
    data1['Free_Timegranted_Days'] =  data1['Total_Freetimegranted_Days'] - data1['FTE_Taken']
    data1['Delay'] = data1['Actual_Turntime_Days'] - data1['Total_Freetimegranted_Days']
    
    
    
    # =================================================
    # Streamlit HTML
    # =================================================
    # Background Image
    html_temp = """<style>
    .stApp {
      background-image: url("https://github.com/rakesh-amman-maersk/Spot-Free-Time-Extension/blob/main/pic8.png?raw=true");
      background-size: cover;
    }
    </style>"""
    st.markdown(html_temp,unsafe_allow_html=True)
    
    # Logo
    image = Image.open(r'logo2.png')
    st.image(image)
      
    # Heading 
    html_temp = """
                <h2 style  = "color:black;text-align:center;background-color:#d7f5f9;">ODIN</h2>
                <h6>      </h6>
                <h2 style  = "color:black;text-align:center;background-color:#d7f5f9;">Spot Free Time Extension Simulator</h2>
     
                """
    st.markdown(html_temp,unsafe_allow_html=True)  
    
    
    # =================================================
    # Input 1
    # =================================================
    uniquebrand = data1['Brand_Dsc'].unique()
    uniquebrand.sort()
    
    container1 = st.container()
    all1 = st.checkbox("Select all operator")
    if(all1):
        brandin = container1.multiselect('Please choose the operator:', uniquebrand,uniquebrand) 
        
    else:
        brandin = container1.multiselect('Please choose the operator:',uniquebrand)
    #st.write('You selected:', brandin)
    print('The brand selected is/are: ', brandin)
    data1 = data1[data1['Brand_Dsc'].isin(brandin)]
    
    # =================================================
    # Input 2
    # =================================================
    uniquecountry = list(data1['Country_Cd'].unique())
    uniquecountry.sort()
    
    if('-1' in uniquecountry):
        uniquecountry = list(uniquecountry)[1:]
    
    container2 = st.container()
    all2 = st.checkbox("Select all country codes")
    if(all2):
        countryinput = container2.multiselect('Please choose the country code:', uniquecountry,uniquecountry)     
    else:
        countryinput = container2.multiselect('Please choose the country code:', uniquecountry) 
    
    #st.write('You selected:', countryinput)
    print('The country selected is/are:: ', countryinput)
    data1 = data1[data1['Country_Cd'].isin(countryinput)]
    
    # =================================================
    # Input 3
    # =================================================
    uniquetariffloc = data1['Tariff_Geosite_Cd'].unique()
    uniquetariffloc.sort()
    
    container3 = st.container()
    all3 = st.checkbox("Select all tariff location codes")
    if(all3):
        tariffinput = container3.multiselect('Please choose the tariff location code:', uniquetariffloc,uniquetariffloc) 
    else:
        tariffinput = container3.multiselect('Please choose the tariff location code:', uniquetariffloc) 
    
    #st.write('You selected:', tariffinput)
    print('The tariff location selected is/are:: ', tariffinput)
    data1 = data1[data1['Tariff_Geosite_Cd'].isin(tariffinput)]
    
    # =================================================
    # Input 4
    # =================================================
    uniquecalcmonth = ['Last 3 Months', 'Last 6 Months', 'Last 1 year']
    
    container4 = st.container()
    all4 = st.checkbox("Select all Calculation Months data")
    if(all4):
        calcmonthinput =  container4.multiselect('Please choose the Calculation Period:', uniquecalcmonth,uniquecalcmonth) 
    else:
        calcmonthinput =  container4.multiselect('Please choose the Calculation Period:', uniquecalcmonth) 
    
    #st.write('You selected:', calcmonthinput)
    print('The Calculation Month data is/are:: ', calcmonthinput, type(calcmonthinput))

    if(len(calcmonthinput)>0):
        if(calcmonthinput[0]=='Last 3 Months'):        
            data1 = data1[data1['Calculation_Month'].isin(month_list[-3:])]
            print('The Calculation Months data considered:: ', month_list[-3:])
        elif(calcmonthinput[0]=='Last 6 Months'):
            data1 = data1[data1['Calculation_Month'].isin(month_list[-6:])]
            print('The Calculation Months data considered:: ', month_list[-6:])            
        elif(calcmonthinput[0]=='Last 1 year'):
            data1 = data1[data1['Calculation_Month'].isin(month_list[-12:])]
            print('The Calculation Months data considered:: ', month_list[-12:])
        
    

    
    # =================================================
    # Input 5
    # =================================================
    uniquecontainers = data1['EquipmentSize_Cd'].unique()
    containersizein =  st.selectbox('Please choose the container size:', uniquecontainers) 
    #st.write('You selected:', containersizein)
    print('The Container size choosed is:: ', containersizein)
    data1 = data1[data1['EquipmentSize_Cd']==containersizein]
    
    
    
    # =================================================
    # Median of FTE Per day
    # =================================================
    data2 = data1.drop(['CommoditySubType_Dsc','Invoiced_Amount','Waived_Amount'],axis=1).drop_duplicates()
    #st.write('The Median of FTE Amount per day with above filters is:', data2['FTE_Perday'].median(),' USD')
    
    FTEperday_median = data2['FTE_Perday'].median()
    
    html_temp = """<h6 style  = "color:#0298ba;text-align:left;">The Median of FTE Amount per day with above filters is: {} USD</h6>""".format(FTEperday_median)
    if(containersizein != None):
        st.markdown(html_temp,unsafe_allow_html=True) 
    
    
    temp = data2[['FTE_Perday']].sort_values(by='FTE_Perday')
    
    tempFTEDays = list(temp['FTE_Perday'].unique())
    if(len(tempFTEDays)>0):
        medianindex = tempFTEDays.index(data2['FTE_Perday'].median())
        FTE_Rate_data = st.selectbox('Please enter the FTE Rate data to be considered', tempFTEDays,index=medianindex)
    
        #st.write('Considering only the data having ',FTE_Rate_data,' USD as FTE amount per day')
        html_temp = """<h6 style  = "color:#0298ba;text-align:left;">Considering only the data having {} USD as FTE amount per day. </h6>""".format(FTE_Rate_data)
        st.markdown(html_temp,unsafe_allow_html=True) 
        
    
        #medianFTErate = np.float64(data2['FTE_Perday'].median())
        print('len of data2%%%%%%%%%%',len(set(data2['Equipment_No'])))
        data2 = data2[data2['FTE_Perday']==FTE_Rate_data]
        print('len of data2%%%%%%%%%%',len(set(data2['Equipment_No'])))
        #st.write('Actual Spot Free Time Extension Revenue:', round(data2['FTE_Amount'].sum()),' USD for ',len(data2[['Equipment_No']].drop_duplicates()),' containers of size ',containersizein,' feet')
        
        html_temp = """<h6 style  = "color:#0298ba;text-align:left;">Actual Spot Free Time Extension Revenue is "{}" USD for total of {} containers.</h6>""".format(round(data2['FTE_Amount'].sum()),len(data2[['Equipment_No']].drop_duplicates()))
        st.markdown(html_temp,unsafe_allow_html=True)
    
    # =================================================
    # Introduction of Slabs
    # =================================================
    html_temp = """
                <h3 style  = "color:white;text-align:center;"> </h3>
                <div style ">
                <h4 style  = "color:black;text-align:center;;background-color:#d7f5f9;">Spot Free Time Extension Revenue simulation with the introduction of Slabs</h4>
                </div>"""
    st.markdown(html_temp,unsafe_allow_html=True) 
    
    html_temp = """            
                <h7 style  = "color:white;text-align:center;">    </h7>
                <h6 style  = "color:white;text-align:center;">         </h6>
                """    
                
    st.markdown(html_temp,unsafe_allow_html=True) 
    
    
    # =========================================
    # Inputs from the user
    # =========================================
    #container_size = st.number_input('Please enter the container size for the simulation (either 20/40) ::')
    if(containersizein != None):
        container_size = float(containersizein)
    num_of_slabs = st.number_input('Please enter the number of slabs to be considered for the simulation::', min_value=1, value =3)
    slabs_end_day = st.text_input('Please enter the "end day" value of slabs (ex: 4,8,14 slab1: 1-4 days, slab2: 5-8 days, slab3: 8-14 days)','4,8,14')
    slabs_end_day = slabs_end_day.split(',')
    
 
    if(containersizein != None):
        if(containersizein == '20'):
            slabs_rates_median = []
            temp_median = FTEperday_median
            for i in range(num_of_slabs):
                slabs_rates_median.append(str(int(temp_median)))
                temp_median -= 1
                
            slabs_rates_median = ','.join(slabs_rates_median)
            print('type&&&&', type(slabs_rates_median),slabs_rates_median)
            slabs_rate = st.text_input('Please enter the Slab rate per day of each slab for FTE (ex: 8,7,6 slab1: 8 USD, slab2: 7 USD, slab3: 6 USD)', slabs_rates_median)
        else:
            slabs_rates_median = []
            temp_median = FTEperday_median
            for i in range(num_of_slabs):
                slabs_rates_median.append(str(int(temp_median)))
                temp_median -= 2
                
            slabs_rates_median = ','.join(slabs_rates_median)
            print('type&&&&', type(slabs_rates_median),slabs_rates_median)
            
            slabs_rate = st.text_input('Please enter the Slab rate per day of each slab for FTE (ex: 8,7,6 slab1: 8 USD, slab2: 7 USD, slab3: 6 USD)', slabs_rates_median)
        slabs_rate = slabs_rate.split(',')
        num_of_simulations = 10
    
    
     
        # =========================================
        # Monte Carlo Simualtion Fuction Call on click
        # =========================================
        if(st.button('Run Simulation')):
            result = montecarlosimualtion(data2,int(container_size), int(num_of_slabs), slabs_end_day, slabs_rate, int(num_of_simulations))
            print(result)
            SpotFTErevBefore = round(result[0])
            SpotFTErevAfter = round(result[1])
            
            simulation_result = pd.DataFrame(columns=['Spot FTE revenue before introduction of slabs in USD', 'Spot FTE revenue after introduction of slabs in USD',
                                                      'Percentage change in the Spot FTE revenue'], data=[[SpotFTErevBefore, SpotFTErevAfter, round(result[2])]])
            #st.success('The Spot FTE revenue before introduction of slabs was {} USD '.format(result[0]))
            
            #st.write('Filters Considered for simulation::')
            #st.write('Container Size: ', container_size,' feet')
            #st.write('Number of Slabs: ', num_of_slabs)
            #st.write('Slab end days: ', slabs_end_day)
            #st.write('Slab rates: ',slabs_rate)
            #st.write('Number of simulations', num_of_simulations) 
            #st.success('The average Spot FTE revenue for the above simulation after introduction of slabs is {} USD'.format(round(result[1])))
            
            if(result[2] > 0):
                st.success('  ')
                st.table(simulation_result)
            else:
                st.error('   ')
                st.table(simulation_result)
            
       
                
                
                
            # ===============================
            # Multi Cannibalization
            # ===============================
            html_temp = """
                        <h3 style  = "color:white;text-align:center;"> </h3>
                        <div style ">
                        <h4 style  = "color:black;text-align:center;background-color:#d7f5f9;">Different slab rates combination and the impact on total revenue</h4>
                        <h5>   </h5>
                        </div>"""
            st.markdown(html_temp,unsafe_allow_html=True)
            
            #multi_cann = st.selectbox('', ['','Yes','No'])
            #if(multi_cann=='Yes'):
            print(slabs_rate)
            print(int(num_of_slabs))
            
            main_slabrate_list = []
            
            for num in [2,1,0,-1,-2,-3]:
                sub_slabrate_list = []
                for rate in slabs_rate:
                    newrate = int(rate) - num
                    sub_slabrate_list.append(newrate)
                main_slabrate_list.append(sub_slabrate_list)
                
            print('main_slabrate_list',main_slabrate_list)
            
            main_diff_slabs_rate = main_slabrate_list
            
            # num_diffslabrates = st.number_input('Please enter the number of different combinations of slab rates to be considered',min_value=1, max_value=10, value=2) 
            # print(num_diffslabrates)
            
            # main_diff_slabs_rate = []
            # for number in range(num_diffslabrates):
            #     diff_slabs_rate = st.text_input('Please enter the rates\day for slabs in combination {} '.format(number+1), ' ')
            #     diff_slabs_rate = diff_slabs_rate.split(',')
            #     main_diff_slabs_rate.append(diff_slabs_rate)
            # print(main_diff_slabs_rate)
            
            
        
            data5 = data1.copy()
            medianFTErate = np.float64(data2['FTE_Perday'].median())
            data5 = data5[data5['FTE_Perday']==medianFTErate]
            
            if(len(data5[data5['Delay']>0])>0): 
                data5 = data5[data5['Delay']>0]
                data5['Invoiced_Amount_Perday'] = round(data5['Invoiced_Amount']/data5['Delay'])
                
                data5['New_FTE_Taken'] = data5['FTE_Taken'].apply(newfte)
                data5[['New_FTE_Taken']] = data5[['New_FTE_Taken']].astype(int)
                data5['NewTotal_Freetime'] = data5['Free_Timegranted_Days'] + data5['New_FTE_Taken']
                data5['New_Delay'] = data5['Actual_Turntime_Days'] - data5['NewTotal_Freetime']
                data5['NewInvoiced_Amount'] = data5['Invoiced_Amount_Perday']*data5['New_Delay']
                
                DNDrevBefore = round(data5['Invoiced_Amount'].sum())
                DNDrevAfter  =  round(data5[data5['New_Delay']>0]['NewInvoiced_Amount'].sum())
            
            
                multi_tableslabrates = pd.DataFrame(columns=[ 'Slab Rates(USD) used in the below graph','Percentage Change in total revenue','The average Spot FTE revenue after intoduction of slabs (USD)','DND revenue after introduction of slabs (USD)'])
                multi_graphtable = pd.DataFrame(columns=[ 'Slab Rates combination','Percentage Change in total revenue after introduction of slabs for different slab rates'])
                
                for slabs_rates in main_diff_slabs_rate:
                    print(slabs_rates)
                    result = montecarlosimualtion(data2,int(container_size), int(num_of_slabs), slabs_end_day, slabs_rates, int(num_of_simulations))
                    SpotFTErevBefore = round(result[0])
                    SpotFTErevAfter = round(result[1])
                    percentagechange = round((((SpotFTErevAfter+DNDrevAfter)/(SpotFTErevBefore+DNDrevBefore))*100)-100)
                    
                    str_slabs_rates = ''
                    for slabs in slabs_rates:
                        str_slabs_rates += str(slabs) + ','
                        
                    multi_tempgraphtable = pd.DataFrame(columns=['Slab Rates combination', 'Percentage Change in total revenue after introduction of slabs for different slab rates'],data=[[str_slabs_rates[:-1],percentagechange]])
                    multi_graphtable = multi_graphtable.append(multi_tempgraphtable)
                    
                    multi_tempslabsrates = pd.DataFrame(columns=[ 'Slab Rates(USD) used in the below graph','Percentage Change in total revenue','The average Spot FTE revenue after intoduction of slabs (USD)','DND revenue after introduction of slabs (USD)'],data=[[str(slabs_rates),percentagechange,SpotFTErevAfter,DNDrevAfter]])
                    multi_tableslabrates = multi_tableslabrates.append(multi_tempslabsrates)
                    
                #st.success('The Spot FTE revenue before introduction of slabs was {} USD '.format(SpotFTErevBefore))
                st.success('The DND revenue before introduction of slabs was {} USD '.format(DNDrevBefore))
                multi_tableslabrates = multi_tableslabrates.reset_index().drop('index',axis=1)
                multi_graphtable = multi_graphtable.reset_index().drop('index',axis=1)
             
                st.table(multi_tableslabrates)  
    
                plt.bar(multi_graphtable['Slab Rates combination'],multi_graphtable['Percentage Change in total revenue after introduction of slabs for different slab rates'],color ='maroon')
                plt.xlabel("Different combination of slab rates")
                plt.ylabel("Percentage (%) change in total revenue after introduction of slabs")
                plt.title("Different combinations of slab rates and impact on total revenue")
                plt.grid()
                st.pyplot()
                #print('multi_tableslabrates',multi_tableslabrates)
               
                change1 = multi_tableslabrates[multi_tableslabrates['Slab Rates(USD) used in the below graph'] == multi_tableslabrates['Slab Rates(USD) used in the below graph'][2]]['Percentage Change in total revenue'][2]
                print(change1)
                change2 = multi_tableslabrates[multi_tableslabrates['Slab Rates(USD) used in the below graph'] == multi_tableslabrates['Slab Rates(USD) used in the below graph'][3]]['Percentage Change in total revenue'][3]
                print(change2)
                change3 = multi_tableslabrates[multi_tableslabrates['Slab Rates(USD) used in the below graph'] == multi_tableslabrates['Slab Rates(USD) used in the below graph'][1]]['Percentage Change in total revenue'][1]
                print(change3)
                html_temp = """<h6 style  = "color:black;text-align:left;background-color:#d7f5f9;">After introduction of slabs with slab rates {0} USD resp, the total revenue is changed by {1}% but an increase in 1 USD per slab rate impacts the total revenue to change by {2}%.</h6>
                               <h6> </h6>
                               <h6 style  = "color:black;text-align:left;background-color:#d7f5f9;">On the other hand a decrese in 1 USD per  slab rate impacts the total revenue to change by {3}%.</h6>""".format(slabs_rate,change1,change2,change3)
                
                st.markdown(html_temp,unsafe_allow_html=True) 
            else:
                html_temp = """<h6 style  = "color:black;text-align:left;background-color:#d7f5f9;">No Delay data found. Cannot run Cannibalization</h6>"""
                st.markdown(html_temp,unsafe_allow_html=True)
                    
                
if(__name__ == '__main__'):
    main()
    