import glob
import pandas as pd
import numpy as np
import re
from datetime import date, time, datetime, timedelta
from time import sleep
from matplotlib import pyplot as plt
import itertools
from bokeh.io import curdoc, show
from bokeh.models import Label, Legend, LegendItem, LabelSet, Span, BoxAnnotation, ColumnDataSource, ColorBar, BasicTicker,  PrintfTickFormatter, LinearColorMapper, Range1d, Grid, LinearAxis, MultiLine, Plot, layouts
from bokeh.plotting import figure, output_file, show
from bokeh.sampledata.les_mis import data
from bokeh.transform import transform

CGM_END = date(2020,9,11)
CGM_BEGIN = date(2020,7,7) #nutrition
RESPONSE_TIME = time(3,0,0,0) #Response start peak finish time
CALIBRATION_CORRECTION_PERIOD = time(5,0,0,0) #for backward adjustment of the CGM Values after calibration, assumes drift of 20%


def clean_date_column(df):
    #validate date exists
    date = False
    cols = list(df)
    split = False
    date_column_index = 0
    for index, column in enumerate(cols):
        if re.match(r"(?i)^(Date|Day)", column):
            date = True
            date_column_index = index
            date_column_name = cols[index]
        #Remove units from column names for cleaner usage later
        # if re.match(r'\w+\s\(.*\)$', column):
        #     measurement, units = column.split(' ')
        #     df.rename(columns={column:measurement}, inplace=True)
    if not date:
        return df
    #Check formatting (may have '\' instead of '-' or include time as well
    df.rename(columns={date_column_name:'Date'}, inplace=True)
    df['Date'] = df.Date.str.replace('/' ,'-')
    df['Date'] = df.Date.str.replace('.' ,'-')
    for col in df['Date'].str.contains('\d+-\d+-\d+ \d+', regex=True):  #if time is included col needs to be split
        if col and not split:
            df['str_split'] = df['Date'].str.split(' ')
            df['Date'] = df.str_split.str.get(0)
            df['Time'] = df.str_split.str.get(1)
            del df['str_split']
            split = True
    if df.loc[0,'filename'] == 'xDripCGM.csv':
        df['Date'] = pd.to_datetime(data['Date'], format='%m-%d-%Y', exact=True)
    else:
        df['Date'] = pd.to_datetime(data['Date'], infer_datetime_format=True)
    df['Date'] = df['Date'].dt.date

    return df

def clean_time_column(df):
    if 'Time' in df:
        time_converted = False
        df['Time'] = df['Time'].fillna('00:00:00')
        # df['Time'] = pd.to_datetime(, format='%H:%M:%S')).dt.time
        # test = df['Time'].str.contains(r'')?
        df['Time'] = pd.to_datetime(df.Time).dt.time
        # df['Time'] =

        # try:
        #     test = df['Time'].str.contains('(\d{1,2}:\d{2}) (?i)(am|pm)', regex=True)
        #     # df = df.replace({'Time'}:{'(\d{1,2}:\d{2}) (?i)(am|pm)':})
        #     df['Time'] = df.mask(df['Time'].str.contains('(\d{1,2}:\d{2}) (?i)(am|pm)', regex=True),
        #                  pd.to_datetime(df['Time'], format='%I:%M %p').dt.time)
        # except Exception as e:
        #     print(f'time problems: {e}')
        #
        # try:
        #     test2 = df['Time'].str.contains('(\d{1,2}:\d{2})', regex=True)
        #     if test2[0]:
        #         df["Time"] = pd.to_datetime(df['Time'], format=('%H:%M')).dt.time
        # except:
        #     print('')
        return df
    else: #Add datetime 00:00:00
        df["Time"] = "00:00:00"
        df['Time'] = pd.to_datetime(df.Time).dt.time
        return df

def add_datetime(df):
    # df.loc['Time'] = df['Time'].fillna('00:00:00', inplace=True)
    df = df.dropna(how='any', subset=['Time'])
    df['Datetime'] = pd.to_datetime(df['Date'].astype(str)+' '+df['Time'].astype(str))
    df['Datetime'] = pd.to_datetime(df['Datetime'], format=('%Y-%m-%d %I:%M %p'))

    return df

def bg_calibration_correction(df_BG):
   #Correct BG Data based on the calibration data
    #Data adjusted by calibrated difference until 12 hours after previous calibration
    df_calibration = df_BG.dropna(how='any', subset=['BG_LEVEL'])
    df_last_calibration = None
    cal_index=0
    df_BG = df_BG.sort_index()
    for cal_time, calibration in df_calibration.iterrows():
        if cal_index%2:
            #calculate the adjustment =>  the difference between the most recent BG measurement and the calibration
            #calculate the time frame for adjustments => calibrations considered solid for 10 hours after calibration
            #find all BG values in the time frame and adjust by difference
            cal_period_end = calibration.Datetime.to_pydatetime()
            cal_period_end = cal_period_end - timedelta(minutes=15)
            cal_period_end_str = extract_time_from_datetime_str(str(pd.to_datetime(cal_period_end)))
            cal_period_start = cal_period_end - timedelta(minutes=20)
            cal_period_start_str = extract_time_from_datetime_str(str(pd.to_datetime(cal_period_start)))
            cal_level = calibration.BG_LEVEL
            cal_date = calibration.Date
            bg_start = cal_period_end - timedelta(hours=5)
            bg_end = cal_period_start + timedelta(hours=5)
            bg_start_str = str(pd.to_datetime(bg_start))
            bg_end_str = str(pd.to_datetime(bg_end))
            # need to capture the day before and after for midnight crossover errors
            df_BG_period = df_BG.loc[bg_start:bg_end]
            df_BG_period = df_BG_period[df_BG_period['UDT_CGMS'].notna()]
            mean = df_BG_period.loc[cal_period_start:cal_period_end].mean()
            try:
                mean = int(mean.mean())
            except:
                print('insufficient CGM data, expanding period')
                mean = df_BG_period.mean()
                mean = int(mean.mean())
            bg_adjustment = cal_level - mean

            period_end_str = cal_period_end_str
            period_start = cal_period_end - timedelta(hours=CALIBRATION_CORRECTION_PERIOD.hour)
            period_start_str = extract_time_from_datetime_str(str(pd.to_datetime(period_start)))
            df_BG_adjust = df_BG_period.between_time(period_start_str, period_end_str)
            i = 0
            for index, row in df_BG_adjust.iterrows():
                adj_factor = bg_adjustment*(i/len(df_BG_adjust))
                new_BG = int(row['UDT_CGMS'] + adj_factor)
                df_BG.loc[row['Datetime'],'UDT_CGMS'] = new_BG
                i += 1
        cal_index += 1
    df_BG = df_BG.dropna(how='any', subset=['UDT_CGMS'])
    print('Calibration Adjustments Completed')
    return df_BG

def bg_heatmap(df_all_CGM, df_all_health):

    num_days = (CGM_END-CGM_BEGIN).days + 1#inclusive of last day
    date_list = [CGM_BEGIN + timedelta(days=x) for x in range(num_days)]


    #create an array for all the dates and times to
    time_index = []
    min_time = datetime.min.time()
    min_datetime = datetime.combine(date_list[0], min_time)
    time_list = [min_datetime + timedelta(minutes=x*15) for x in range(96)]
    time_index = [time_list[x].strftime("%H:%M:%S") for x in range(len(time_list))]
    date_column = [date_list[x].strftime("%Y-%m-%d") for x in range(len(date_list))]

    # df_CGM_period_max = pd.concat([df_all_CGM, df_all_health], ignore_index=True)
    df_CGM_period_max = df_all_CGM.set_index(df_all_CGM['Datetime'])
    df_CGM_end_test = df_CGM_period_max.loc[df_CGM_period_max['Date'] == CGM_END]
    df_CGM_end_test= df_CGM_end_test.resample('15Min', base=15, label='right')['UDT_CGMS'].max()
    # df_CGM_period_max = df_CGM_period_max.groupby(pd.Grouper(freq='15Min', base=15, label='right')).first()
    df_CGM_period_max = df_CGM_period_max.resample('15Min', base=15, label='right')['UDT_CGMS'].max()

    if len(df_CGM_end_test.index) < len(time_index):
        for day in date_list:
            if day == CGM_END:
                for index in time_list:
                    # if index.date() == CGM_END
                    try:
                        df_CGM_period_max[datetime.combine(CGM_END,index.time())]
                    except:
                        df_CGM_period_max[datetime.combine(CGM_END,index.time())] = np.nan
        df_CGM_period_max = df_CGM_period_max.interpolate(method='linear', limit_direction='forward')
    df_meals = df_all_health.loc[df_all_health['filename'] == 'CronoServings.csv']
    df_meals = df_meals.dropna(how='all', axis=1) # drop all fully nan columns as they are not useful here
    df_dt_matrix_CGM = pd.DataFrame(0, columns=date_column, index=time_index)
    df_dt_matrix_meals = pd.DataFrame(0, columns=date_column, index=time_index)
    # if df_CGM_period_max.columns < df_dt_matrix_CGM:

    for date, date_array in df_dt_matrix_CGM.iteritems():
        date_array = date_array.reset_index()
        period_date = datetime.strptime(date, "%Y-%m-%d")
        # df_CGM_day = df_all_CGM.loc[df_all_CGM['Date'] == period_date.date()]
        # df_CGM_day = df_CGM_day.set_index(df_CGM_day['Datetime'])
        df_meals_day = df_meals.loc[df_meals['Date'] == period_date.date()] #& (df_current_day['Carbs (g)'] >= 5)
        df_meals_day = df_meals_day.set_index(df_meals_day['Datetime'])

        for time_i in range(date_array.shape[0]):
            #df of the current time period for pertinent information

            current_period_time = pd.to_datetime(date_array.loc[time_i,'index'])
            current_period_time_str = extract_time_from_datetime_str(str(current_period_time))
            if time_i < date_array.shape[0]-1:
                next_period_time = pd.to_datetime(date_array.loc[time_i + 1,'index'])
                next_period_time_str = extract_time_from_datetime_str(str(next_period_time))


            # df_CGM_period = df_CGM_day.between_time(current_period_time, next_period_time)
            # df_meals_period = df_meals_day.between_time(current_period_time_str, next_period_time_str)
            # data_array = pd.concat([df_CGM_period, df_meals_period], ignore_index=True)
            # data_array = data_array.dropna(how='all', axis=1)
            current_time = current_period_time.to_pydatetime().time()
            current_dt = datetime.combine(period_date, current_time)
            next_time = next_period_time.to_pydatetime().time()
            next_dt = datetime.combine(period_date, next_time)
            try:
                CGM_max = df_CGM_period_max[current_dt]
            except Exception as e:
                try:
                    CGM_max = df_CGM_period_max[next_dt]
                except Exception as e:
                    CGM_max = df_CGM_period_max[previous_dt]

            df_dt_matrix_CGM.loc[current_period_time_str, date] = CGM_max
            meal_string = ''
            df_meals_day = df_meals_day.sort_values(['Carbs (g)'], ascending=[False])
            for index, meal in df_meals_day.iterrows():
                meal_time = datetime.combine(period_date, meal.Time)
                time_diff = meal_time + timedelta(hours=RESPONSE_TIME.hour)
                if (time_diff > current_dt and current_dt >= meal_time):
                    meal_string += meal['Food Name'] + ' + '
            df_dt_matrix_meals.loc[current_period_time_str, date] = meal_string

            previous_dt = current_dt
        print('Day ' + date + ' finished')
    # df_dt_matrix_CGM = df_dt_matrix_CGM.reset_index()
    df_dt_matrix_CGM = df_dt_matrix_CGM.interpolate(method='linear', limit_direction='forward', axis=1)#method='polynomial', order=2)

    print("wait!")
            #calculate the avg BG over the period
            # df_BG_period = df_CGM[]

            #add the pertinent meal information


    #This is a nice bokey example using downloaded data
    total_days = df_dt_matrix_CGM.shape[1]


    # xname = date_column.tolist()
    # yname = time_index.tolist()
    xname = [[date_column[j] for i in range(len(time_index))] for j in range(len(date_column))]
    yname = [[time_index[i] for i in range(len(time_index))] for j in range(len(date_column))]
    xname = list(itertools.chain.from_iterable(xname))
    yname = list(itertools.chain.from_iterable(yname))
    bg_list = list(df_CGM_period_max.interpolate(method='linear', limit_direction='both'))
    min = df_CGM_period_max.min()
    def calc_color(bg):
        colormap = ["#004529", "#006d2c", "#238b45", "#d9f0a3", "#fed976", "#feb24c",
                "#fd8d3c", "#fc4e2a", "#e31a1c", "#bd0026", "#800026"]
        # color = []
        # for row_bg in bg:
        if bg < 60:
            color = (colormap[0])
        elif bg > 160:
            color = (colormap[10])
        else:
            color = (colormap[int(((bg-60)/100)*10)])
        return color

    color_selection = ["#004529", "#006d2c", "#238b45", "#d9f0a3", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#bd0026", "#800026"]
    mapper = LinearColorMapper(palette=color_selection, low=60, high=180)#low=df_CGM_period_max.min(), high=df_CGM_period_max.min())
    color = map(calc_color, bg_list)
    color = list(color)
    food_list = list(itertools.chain.from_iterable(df_dt_matrix_meals.transpose().values.tolist()))
    # bg_dict = df_dt_matrix_CGM.to_dict(orient="index")
    # food_dict = df_dt_matrix_meals.to_dict(orient="index")
    xydata = {'xname': xname, 'yname': yname, 'bg': bg_list, 'foods': food_list}
    source = ColumnDataSource(xydata)
    data=dict(
        xname=xname,
        yname=yname,
        colors=color,
        bg=bg_list,
        foods=food_list,
    )

    p = figure(title="Blood Glucose over " + str(total_days) + " days",
               x_axis_location="above", tools="hover,pan,box_zoom,reset,save",
               x_range=date_column, y_range=time_index, output_backend="webgl",
               tooltips=[('Sample', '@yname, @xname'), ('Foods', '@foods'), ('Blood Glucose', '@bg')])

    p.plot_width = 1200
    p.plot_height = 800
    p.grid.grid_line_color = None
    p.axis.axis_line_color = None
    p.axis.major_tick_line_color = None
    p.axis.major_label_text_font_size = "7px"
    p.axis.major_label_standoff = 0
    p.xaxis.major_label_orientation = np.pi/3

    p.rect('xname', 'yname', 0.9, 0.9, source=data,
           color='colors',
           line_color=None,
           hover_line_color='black', hover_color='colors',
           # fill_color=transform('bg', mapper),
           )

    output_file("GlucoseResponses/bgheatmap.html", title="first bg test")

    color_bar = ColorBar(color_mapper=mapper, location=(0, 0),
                     ticker=BasicTicker(desired_num_ticks=len(color_selection)-2),
                     formatter=PrintfTickFormatter(format="%d"))


    p.add_layout(color_bar, 'right')
    p.add_layout(color_bar, 'left')
    show(p) # show the plot
    print('just wait until I finish')

def bg_multi_plot(df_all_CGM, df_all_health):
    # prepare some data
    df_health_data = df_all_health.loc[CGM_BEGIN:CGM_END,:]
    df_health_data.sort_values(['Datetime'], ascending=[True])
    df_health_data = df_health_data.set_index("Datetime", drop = False)
    df_period_CGM = df_all_CGM.loc[CGM_BEGIN:CGM_END,:]
    df_period_CGM.sort_values(['Datetime'], ascending=[True])
    df_period_CGM = df_period_CGM.set_index("Datetime", drop=False)
    df_period_CGM = df_period_CGM.sort_index()

    response_meals = df_health_data.loc[(df_health_data['filename'] == 'CronoServings.csv') & (df_health_data['Carbs (g)'] >= 5)]
    # sleep_data = df_current_day.loc[df_current_day['filename'] == 'OuraSleepData.csv']
    exercise_data = df_health_data.loc[df_health_data['filename'] == 'GarminActivities.csv']
    exercise_data = exercise_data.set_index("Datetime", drop=False)
    exercise_data = exercise_data.dropna(how='any', axis=1)
    response_meals = response_meals.dropna(how='any', axis=1)
    response_meals = response_meals.sort_values(['Carbs (g)'], ascending=[False])


    p = figure(
       tools="pan,box_zoom,hover,reset,save",
       title="Multiline CGM", x_axis_type='datetime',
       x_axis_label='Response', y_axis_label='Glucose',
       y_range = (-100, 120), y_axis_location='right',
       tooltips=[('Sample', '@xname, @yname'), ('Glucose Delta', '@GD'), ('Max Blood Glucose', '@bg'),
                 ('Total Calories', '@cal'),('Total Carbs', '@carb'),('Food', '@Food')],
       y_minor_ticks=2,output_backend="webgl"
    )
    # current_date = current_date + timedelta(days=1)
    output_file('GlucoseResponses/Multi.html')
    df_plot_data = pd.DataFrame(columns=['Date','Meal','Time','Glucose'])
    df_data_summary = pd.DataFrame(columns=['Date','Time','Meal','Peak Glucose','Glucose Delta', 'Calories','Carbs'])
    for meal_time, meal in response_meals.iterrows():
        # output to static HTML file
        name_string = meal['Food Name']
        name_string = name_string.split(', ')
        start_time = meal.Datetime
        end_time = start_time + timedelta(hours=RESPONSE_TIME.hour)
        df_meal_CGM = df_period_CGM.loc[start_time:end_time,:]
        df_meal_exercise = exercise_data.loc[start_time:end_time,:]

        try:
            the_beginning = pd.to_datetime(df_meal_CGM.iloc[0]['Datetime']).to_pydatetime()
        except: #Missing Data at times due to lack of sensor
            print('Data Failure, abandoning ' + meal['Food Name'] + ' Date => ' + meal['Date'].strftime("%Y-%m-%d"))
            continue
        the_beginning = the_beginning.time()
        df_meal_CGM["Response Time"] = df_meal_CGM.Datetime - timedelta(hours=the_beginning.hour, minutes=the_beginning.minute, seconds=the_beginning.second)
        df_meal_CGM["Response Time"] = df_meal_CGM["Response Time"].dt.time
        df_meal_CGM["ZeroedCGMS"] = df_meal_CGM.UDT_CGMS - df_meal_CGM.iloc[0]["UDT_CGMS"]
        df_temp = pd.DataFrame({'Date':[meal_time],'Meal':[name_string[0]],'Time':[list(df_meal_CGM["Response Time"])],'Glucose':[list(df_meal_CGM.ZeroedCGMS)]})
        df_plot_data = df_plot_data.append(df_temp)
        meal['Delta'] = df_meal_CGM.UDT_CGMS.max() - df_meal_CGM.UDT_CGMS[0]
        meal['Peak'] = df_meal_CGM.UDT_CGMS.max()
        xydata = {'RespTime': df_meal_CGM["Response Time"], 'zg': df_meal_CGM.ZeroedCGMS ,
                  'xname': [meal['Date'].strftime("%Y-%m-%d") for i in range(len(df_meal_CGM.ZeroedCGMS))],
                  'yname': [meal['Time'].strftime("%H:%M:%S") for i in range(len(df_meal_CGM.ZeroedCGMS))],
                  'bg': [str(int(meal['Peak'])) for i in range(len(df_meal_CGM.ZeroedCGMS))],
                  'GD': [str(int(meal['Delta'])) for i in range(len(df_meal_CGM.ZeroedCGMS))],
                  'cal': [str(int(meal['Energy (kcal)'])) for i in range(len(df_meal_CGM.ZeroedCGMS))],
                  'carb': [str(int(meal['Net Carbs (g)'])) for i in range(len(df_meal_CGM.ZeroedCGMS))],
                  'Food': [meal['Food Name'] for i in range(len(df_meal_CGM.ZeroedCGMS))]}
        source = ColumnDataSource(xydata)
        line = p.line('RespTime', 'zg', line_width=4, color='grey', alpha=0.05,
                        muted_color='#e82317', muted_alpha=0.9, legend_label=name_string[0], source=source)
        df_data_summary = df_data_summary.append({'Date': meal['Date'],
                                'Time': meal['Time'],
                                'Meal': meal['Food Name'],
                                'Peak Glucose': meal['Peak'],
                                'Glucose Delta': meal['Delta'],
                                'Calories': meal['Energy (kcal)'],
                                'Carbs': meal['Net Carbs (g)']},ignore_index=True)
        # df_data_summary = df_data_summary.append([meal['Date'].strftime("%Y-%m-%d"),
        #                         meal['Time'].strftime("%H:%M:%S"),
        #                         name_string,
        #                         meal['Peak'],
        #                         meal['Delta'],
        #                         meal['Energy (kcal)'],
        #                         meal['Net Carbs (g)']],ignore_index=True)
    # source = ColumnDataSource(data=df_plot_data)
    # p = figure(
    #        tools="pan,box_zoom,hover,reset,save",
    #        title="Multiline CGM", x_axis_type='datetime',
    #        x_axis_label='Response', y_axis_label='Glucose',
    #        y_range = (-100, 100), y_axis_location='right',
    #        y_minor_ticks=2,output_backend="webgl"
    #     )

    # p.multi_line(xs=df_plot_data["Time"], ys=df_plot_data["Glucose"], line_width=3, color='grey', alpha=0.8,
    #    muted_color='#E4E5E7', muted_alpha=0.2, hover_line_color="#FF002D", legend_label=df_plot_data["Meal"])

    # show the results
    hour_one = 10800000/3
    response_hour = Span(location=hour_one,
                                  dimension='height', line_color='black',
                                  line_dash='dashed', line_width=3)
    p.add_layout(response_hour)

    hour_two = (10800000/3)*2
    response_hour_2 = Span(location=hour_two,
                                dimension='height', line_color='black',
                                line_dash='dashed', line_width=3)
    p.add_layout(response_hour_2)
    p.title.text = "Glucose Response"
    p.xgrid[0].grid_line_color=None
    p.ygrid[0].grid_line_alpha=0.5
    p.xaxis.axis_label = 'Time'
    p.yaxis.axis_label = 'mmol/dl'
    p.yaxis.ticker = [-100, -50, 0, 50, 100, 120]
    p.plot_width = 3200
    p.plot_height = 3100
    # p.legend.location = "top_left"
    p.legend.click_policy="mute"
    # p.hbar(y='Meal Name', )
    temp_list = list(df_plot_data['Meal'])
    # p.extra_y_ranges = {"Meal Names": list(df_plot_data['Meal'])}
    # p.add_layout(LinearAxis(y_range_name="Meal Names", axis_label='foo label'), 'left')

    # low_box = BoxAnnotation(top=70, fill_alpha=0.1, fill_color='red')
    mid_box = BoxAnnotation(bottom=-100, top=40, fill_alpha=0.1, fill_color='green')
    high_box = BoxAnnotation(bottom=40, top=140, fill_alpha=0.1, fill_color='red')

    # p.add_layout(low_box)
    p.add_layout(mid_box)
    p.add_layout(high_box)

    p.add_layout(p.legend[0], 'left')
    show(p)
    df_data_summary.to_csv('GlucoseResponses/MealData.csv', index=False)
    print('just wait until I finish')

def extract_time_from_datetime_str(day):
    # String should be of the form "2020-02-02 00:00:00"
    day = day.split(' ')
    time = day[1]

    return time

def bg_food_response_bokeh(df_all_CGM, df_all_health):
    df_health_data = df_all_health.loc[CGM_BEGIN:CGM_END,:]
    df_health_data.sort_values(['Datetime'], ascending=[True])
    df_health_data = df_health_data.set_index("Datetime", drop = False)
    df_period_CGM = df_all_CGM.loc[CGM_BEGIN:CGM_END,:]
    df_period_CGM.sort_values(['Datetime'], ascending=[True])
    df_period_CGM = df_period_CGM.set_index("Datetime", drop=False)
    df_period_CGM = df_period_CGM.sort_index()

    response_meals = df_health_data.loc[(df_health_data['filename'] == 'CronoServings.csv') & (df_health_data['Carbs (g)'] >= 5)]
    # sleep_data = df_current_day.loc[df_current_day['filename'] == 'OuraSleepData.csv']
    exercise_data = df_health_data.loc[df_health_data['filename'] == 'GarminActivities.csv']
    exercise_data = exercise_data.set_index("Datetime", drop=False)
    exercise_data = exercise_data.dropna(how='any', axis=1)
    response_meals = response_meals.dropna(how='any', axis=1)
    response_meals = response_meals.sort_values(['Carbs (g)'], ascending=[False])

    # current_date = current_date + timedelta(days=1)


    for time, meal in response_meals.iterrows():
        # output to static HTML file
        name_string = meal['Food Name']
        name_string = name_string.split(', ')
        output_file('GlucoseResponses/' + name_string[0] + '.html')

        # create a new plot
        p = figure(
           tools="pan,box_zoom,reset,save",
           title="log axis example", x_axis_type='datetime',
           x_axis_label='Response', y_axis_label='Glucose'
        )


        # add some renderers
        start_time = meal.Datetime
        end_time = start_time + timedelta(hours=RESPONSE_TIME.hour)
        df_meal_CGM = df_period_CGM.loc[start_time:end_time,:]
        df_meal_exercise = exercise_data.loc[start_time:end_time,:]
        try:
            the_beginning = pd.to_datetime(df_meal_CGM.iloc[0]['Datetime']).to_pydatetime()
        except: #Missing Data at times due to lack of sensor
            print('Data Failure, abandoning ' + meal['Food Name'] + ' Date => ' + meal['Date'].strftime("%Y-%m-%d"))
            continue
        the_beginning = the_beginning.time()
        df_meal_CGM["Response Time"] = df_meal_CGM.Datetime - timedelta(hours=the_beginning.hour, minutes=the_beginning.minute, seconds=the_beginning.second)
        df_meal_CGM["Response Time"] = df_meal_CGM["Response Time"].dt.time
        df_meal_CGM["ZeroedCGMS"] = df_meal_CGM.UDT_CGMS - df_meal_CGM.iloc[0]["UDT_CGMS"]
        p.line(df_meal_CGM["Datetime"], df_meal_CGM.UDT_CGMS, line_width=4, line_color="black")
        # p.circle(x, x, legend="y=x", fill_color="white", size=8)
        # p.line(x, y0, legend="y=x^2", line_width=3)
        # p.line(x, y1, legend="y=10^x", line_color="red")
        # p.circle(x, y1, legend="y=10^x", fill_color="red", line_color="red", size=6)
        # p.line(x, y2, legend="y=10^x^2", line_color="orange", line_dash="4 4")

        if not df_meal_exercise.empty:
            for time, workout in df_meal_exercise.iterrows():
                activity_info = workout
                activity_time = pd.to_datetime(activity_info['Activity Time'])
                activity_time = activity_time.to_pydatetime()
                start_time = activity_info.Datetime.to_pydatetime()
                end_time = start_time + timedelta(hours=activity_time.hour, minutes=activity_time.minute)
                exercise_box = BoxAnnotation(left=start_time, right=end_time, fill_alpha=0.4, fill_color='blue')
                label5 = Label(x=300, y=int(df_meal_CGM.UDT_CGMS.min()*1.2), x_units='screen', text="Activity = " + str(workout.Title), render_mode='css',
                    border_line_color='black', border_line_alpha=1.0,
                    background_fill_color='white', background_fill_alpha=1.0)
                label6 = Label(x=300, y=int(df_meal_CGM.UDT_CGMS.min()*1.1), x_units='screen', text='Calories = ' + str(workout.Calories), render_mode='css',
                    border_line_color='black', border_line_alpha=1.0,
                    background_fill_color='white', background_fill_alpha=1.0)
                p.add_layout(exercise_box)
                p.add_layout(label5)
                p.add_layout(label6)
        # show the results
        # exercise_box = BoxAnnotation(left=2, right=3, fill_alpha=0.1, fill_color='blue')
        low_box = BoxAnnotation(top=70, fill_alpha=0.1, fill_color='red')
        mid_box = BoxAnnotation(bottom=70, top=140, fill_alpha=0.1, fill_color='green')
        high_box = BoxAnnotation(bottom=140, fill_alpha=0.1, fill_color='red')

        p.add_layout(low_box)
        p.add_layout(mid_box)
        p.add_layout(high_box)
        # try:
        #
        #
        # except:
        #     print("no exercises found")
        delta = df_meal_CGM.UDT_CGMS.max() - df_meal_CGM.UDT_CGMS[0]
        height = int(df_meal_CGM.UDT_CGMS.max()*.95)
        height2 = int(df_meal_CGM.UDT_CGMS.max()*.93)
        height3 = int(df_meal_CGM.UDT_CGMS.max()*.90)
        height4 = int(df_meal_CGM.UDT_CGMS.max()*.87)
        label1 = Label(x=70, y=height, x_units='screen', text="Glucose Delta = " + str(delta), render_mode='css',
          border_line_color='black', border_line_alpha=1.0,
          background_fill_color='white', background_fill_alpha=1.0)
        label2 = Label(x=70, y=height2, x_units='screen', text='Peak = ' + str(df_meal_CGM.UDT_CGMS.max()) + ' mmol/dl', render_mode='css',
          border_line_color='black', border_line_alpha=1.0,
          background_fill_color='white', background_fill_alpha=1.0)
        label3 = Label(x=70, y=height3, x_units='screen', text='Total Carbs = ' + str(meal['Carbs (g)']) + ' g', render_mode='css',
          border_line_color='black', border_line_alpha=1.0,
          background_fill_color='white', background_fill_alpha=1.0)
        label4 = Label(x=70, y=height4, x_units='screen', text='Total Calories = ' + str(meal['Energy (kcal)']), render_mode='css',
          border_line_color='black', border_line_alpha=1.0,
          background_fill_color='white', background_fill_alpha=1.0)

    # hour_one = time.mktime(date(1, 0, 0).timetuple())*1000
    # response_hour = Span(location=hour_one,
    #                               dimension='height', line_color='black',
    #                               line_dash='dashed', line_width=3)
    # p.add_layout(hour_one)
    #
    # hour_two = time.mktime(date( 2, 0, 0).timetuple())*1000
    # response_hour_2 = Span(location=hour_two,
    #                             dimension='height', line_color='black',
    #                             line_dash='dashed', line_width=3)
    # p.add_layout(hour_two)
        p.add_layout(label1)
        p.add_layout(label2)
        p.add_layout(label3)
        p.add_layout(label4)
        p.title.text = "Glucose Response of " + meal['Food Name']
        p.title.align = "center"
        p.xgrid[0].grid_line_color=None
        p.ygrid[0].grid_line_alpha=0.5
        p.xaxis.axis_label = 'Time (' + str(meal['Date']) + ')'
        p.yaxis.axis_label = 'mmol/dl'
        show(p)
        sleep(1)
    print('just wait until I finish')


def bg_food_response_matplot(df_all_CGM, df_all_health):
    current_date = CGM_BEGIN
    while current_date <= CGM_END:
        print("Processing Data for " + str(current_date))
        df_current_day = df_all_health.loc[current_date,:]
        df_current_day.sort_values(['Datetime'], ascending=[True])
        df_current_day = df_current_day.set_index("Datetime", drop = False)
        df_current_day_CGM = df_all_CGM.loc[current_date,:]
        df_current_day_CGM.sort_values(['Datetime'], ascending=[True])
        df_current_day_CGM = df_current_day_CGM.set_index("Datetime", drop=False)

        response_meals = df_current_day.loc[(df_current_day['filename'] == 'CronoServings.csv') & (df_current_day['Carbs (g)'] >= 5)]
        sleep_data = df_current_day.loc[df_current_day['filename'] == 'OuraSleepData.csv']
        exercise_data = df_current_day.loc[df_current_day['filename'] == 'GarminActivities.csv']
        # exercise_data = exercise_data.set_index("Datetime", drop=False)
        response_meals = response_meals.dropna(how='any', axis=1)
        sleep_data = sleep_data.dropna(how='any', axis=1)
        exercise_data = exercise_data.dropna(how='any', axis=1)
        nrows = len(response_meals)
        extra_row = nrows % 2
        if extra_row:
            fig, axes = plt.subplots(nrows//2+1,2)
        else:
            fig, axes = plt.subplots(nrows//2,2)

        index = 0
        for food in response_meals.iterrows():
            df_meal_data = food[1]
            period_start = df_meal_data.Datetime.to_pydatetime()
            period_start_str = extract_time_from_datetime_str(str(pd.to_datetime(period_start)))
            period_end = period_start + timedelta(hours=RESPONSE_TIME.hour)
            period_end_str = extract_time_from_datetime_str(str(pd.to_datetime(period_end)))
            # time = pd.to_pydatetime(period_end)
            df_CGM_response = df_current_day_CGM.between_time(period_start_str,period_end_str)
            df_exercise = exercise_data.between_time(period_start_str,period_end_str)

            title = (str(df_CGM_response['Date'].values[0]) + " Time (Day)")
            # df_CGM_response.plot(x='Time', y='UDT_CGMS', ax=axes[index,0])
            df_CGM_response.plot(x='Time', y='UDT_CGMS', ax=axes[index//2,1 if index % 2 else 0], subplots=True)
            # df_CGM_response.ewm(span=5).mean().plot(x='Time', y='UDT_CGMS')
            # df_CGM_response['UDT_CGMS'].interpolate('polynomial', order=9).plot()

            if not df_exercise.empty:
                for workout in df_exercise.iterrows():
                    activity_info = workout[1]
                    activity_time = pd.to_datetime(activity_info['Activity Time'])
                    activity_time = activity_time.to_pydatetime()
                    start_time = activity_info.Datetime.to_pydatetime()
                    end_time = start_time + timedelta(hours=activity_time.hour, minutes=activity_time.minute)
                    axes[index//2,1 if index % 2 else 0].axvspan(str(start_time), str(end_time), color='blue', alpha=0.5)
                    axes[index//2,1 if index % 2 else 0].annotate(activity_info.Title + '\n' + activity_info['Calories'] + ' Calories Burned', xy=(str(start_time),df_CGM_response['UDT_CGMS'].median()))

            axes[index//2,1 if index % 2 else 0].set_title('BG Response to ' + df_meal_data.loc['Food Name'])
            axes[index//2,1 if index % 2 else 0].set_xlabel(str(df_CGM_response['Date'].values[0]) + " Time(Day)")
            axes[index//2,1 if index % 2 else 0].set_ylabel("Blood Glucose")
            index += 1

        plt.tight_layout()
        plt.show()
        current_date = current_date + timedelta(days=1)
    return

#Data Capture and cleanup
files = glob.glob("*.csv")
df_array = []
for filename in files:

  data = pd.read_csv(filename,encoding = "ISO-8859-1")
  if filename == 'GarminActivities.csv':
      data = data.rename(columns={'Time': 'Activity Time'})
  data = data.rename(columns={'DAY' or 'Day': 'Date'})
  data = data.rename(columns={'TIME': 'Time'})
  data['filename'] = filename
  data = clean_date_column(data)
  data = clean_time_column(data)
  data = add_datetime(data)

  if data.loc[0,'filename'] == 'OuraSleepData.csv':
    df_sleep = data
  elif data.loc[0,'filename'] == 'xDripCGM.csv':
    df_CGM = data
  elif data.loc[0,'filename'] == 'GarminActivities.csv':
    df_activity = data
  elif data.loc[0,'filename'] == 'CronoServings.csv':
    df_nutrition = data



df_combined_health_data = pd.concat([df_nutrition, df_activity, df_sleep], ignore_index=True)

#Data Cleanup
df_combined_health_data['Date'].fillna(df_combined_health_data['Date'])
# df_combined_health_data['DateTime'] = df_combined_health_data['Date'] + df_combined_health_data['Time ']
# df_combined_health_data['DateTime'] = df_combined_health_data['Date'] + df_combined_health_data['Time ']
df_combined_health_data = df_combined_health_data.sort_values(by='Datetime', ascending=True)
df_combined_health_data = df_combined_health_data.set_index("Date", drop=False)
df_CGM = df_CGM.set_index("Date", drop=False)
df_CGM = df_CGM[(df_CGM['Date'] >= CGM_BEGIN) & (df_CGM['Date'] <= CGM_END)]
df_CGM = df_CGM.sort_values('Datetime', ascending=True)
df_CGM = df_CGM.set_index("Datetime", drop=False)
df_CGM_corrected = bg_calibration_correction(df_CGM)
df_CGM_corrected = df_CGM_corrected.set_index("Date", drop=False)
# ['Day', 'Time', 'Group', 'Food Name', 'Amount', 'Energy (kcal)',
#        'Alcohol (g)', 'Caffeine (mg)', 'Water (g)', 'B1 (Thiamine) (mg)',
#        'B2 (Riboflavin) (mg)', 'B3 (Niacin) (mg)',
#        'B5 (Pantothenic Acid) (mg)', 'B6 (Pyridoxine) (mg)',
#        'B12 (Cobalamin) (Âµg)', 'Folate (Âµg)', 'Vitamin A (IU)',
#        'Vitamin C (mg)', 'Vitamin D (IU)', 'Vitamin E (mg)', 'Vitamin K (Âµg)',
#        'Calcium (mg)', 'Copper (mg)', 'Fluoride (Âµg)', 'Iodine (Âµg)',
#        'Iron (mg)', 'Magnesium (mg)', 'Manganese (mg)', 'Phosphorus (mg)',
#        'Potassium (mg)', 'Selenium (Âµg)', 'Sodium (mg)', 'Zinc (mg)',
#        'Carbs (g)', 'Fiber (g)', 'Fructose (g)', 'Glucose (g)', 'Starch (g)',
#        'Sugars (g)', 'Net Carbs (g)', 'Fat (g)', 'Cholesterol (mg)',
#        'Monounsaturated (g)', 'Polyunsaturated (g)', 'Saturated (g)',
#        'Trans-Fats (g)', 'Omega-3 (g)', 'Omega-6 (g)', 'Cystine (g)',
#        'Histidine (g)', 'Isoleucine (g)', 'Leucine (g)', 'Lysine (g)',
#        'Methionine (g)', 'Phenylalanine (g)', 'Protein (g)', 'Threonine (g)',
#        'Tryptophan (g)', 'Tyrosine (g)', 'Valine (g)', 'Category', 'filename'],
#       dtype='object')
# Index(['Activity Type', 'Date', 'Favorite', 'Title', 'Distance', 'Calories',
#        'Time', 'Avg HR', 'Max HR', 'Aerobic TE', 'Avg Run Cadence',
#        'Max Run Cadence', 'Avg Speed', 'Max Speed', 'Elev Gain', 'Elev Loss',
#        'Avg Stride Length', 'Avg Vertical Ratio', 'Avg Vertical Oscillation',
#        'Training Stress ScoreÂ®', 'Grit', 'Flow', 'Total Reps', 'Total Sets',
#        'Bottom Time', 'Min Temp', 'Surface Interval', 'Decompression',
#        'Best Lap Time', 'Number of Laps', 'Max Temp', 'filename'],
#       dtype='object')
# Index(['date', 'Sleep Score', 'Total Sleep Score', 'REM Sleep Score',
#        'Deep Sleep Score', 'Sleep Efficiency Score', 'Sleep Tranquility Score',
#        'Sleep Latency Score', 'Sleep Timing Score', 'Total Bedtime',
#        'Total Sleep Time', 'Awake Time', 'REM Sleep Time', 'Light Sleep Time',
#        'Deep Sleep Time', 'Restless Sleep', 'Sleep Efficiency',
#        'Sleep Latency', 'Sleep Timing', 'Sleep Timing.1', 'Bedtime Start',
#        'Bedtime End', 'Average Resting Heart Rate',
#        'Lowest Resting Heart Rate', 'Average HRV', 'Temperature Deviation',
#        'Respiratory Rate', 'Activity Score', 'Stay Active Score',
#        'Move Every Hour Score', 'Meet Daily Targets Score',
#        'Training Frequency Score', 'Training Volume Score',
#        'Recovery Time Score', 'Activity Burn', 'Total Burn', 'Target Calories',
#        'Steps', 'Daily Movement', 'Inactive Time', 'Rest Time',
#        'Low Activity Time', 'Medium Activity Time', 'High Activity Time',
#        'Non-wear Time', 'Average MET', 'Long Periods of Inactivity',
#        'Readiness Score', 'Previous Night Score', 'Sleep Balance Score',
#        'Previous Day Activity Score', 'Activity Balance Score',
#        'Temperature Score', 'Resting Heart Rate Score', 'HRV Balance Score',
#        'Recovery Index Score', 'filename'],
#       dtype='object')
# Index(['Date', 'Time', 'UDT_CGMS', 'BG_LEVEL', 'CH_GR', 'BOLUS', 'REMARK',
#        'filename'],
#       dtype='object')
# Index(['Day', 'Time', 'Group', 'Food Name', 'Amount', 'Energy (kcal)',
#        'Alcohol (g)', 'Caffeine (mg)', 'Water (g)', 'B1 (Thiamine) (mg)',
#        ...
#        'Activity Balance Score', 'Temperature Score',
#        'Resting Heart Rate Score', 'HRV Balance Score', 'Recovery Index Score',
#        'UDT_CGMS', 'BG_LEVEL', 'CH_GR', 'BOLUS', 'REMARK']

#Produce the Blood Glucose Response Visualizations
# bg_food_response_matplot(df_CGM_corrected, df_combined_health_data)
# bg_food_response_bokeh(df_CGM_corrected, df_combined_health_data)
# bg_heatmap(df_CGM_corrected, df_combined_health_data)
bg_multi_plot(df_CGM_corrected, df_combined_health_data)
#Find interesting correlations in the data

#

print('testing 123')
