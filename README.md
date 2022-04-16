# CGM Analysis
This script will take in data from xDrip continuous Glucose tracking, Garmin Activity Data, Cronometer Nutritional Data, and Oura Sleep Data and generate several visuals to correlate food, activity, sleep and glucose response data.

##Visuals
* Glucose Step Response for each meal
* HeatMap displaying Glucose over time periods and showing corresponding meals.
* Multiplot showing all step responses.  Meals are selectable to compare step responses in the same time period.
* 
## Requirements

In the root directory:

* LabResults.csv
  * This is a .csv export from wellnessfx.com.
  * Script will import biometric data for date under "uncategorized"
  * .csv header + example data
    * Draw Date,Marker Name,Marker Description,Value,Units,Reference Range,Source
    * 1/23/2012,% Basophils,Part of WBC differential,0.4,%,,
* BloodNutrientTracking.csv
  * This is a .csv spreadsheet for Ketones and Blood Glucose data.
  * Script will import biometric data for date under "uncategorized"
  * .csv header + example data
    * Date Time,Ketones (mmol/L),Ratio,BG (mmol/l),Blood Sugar (mg/dl),Activity Level,Notes
    * 10/9/16 6:30pm,0.1,50,5,90,Very Low  ~1000 steps and no gym,"Lots of carbs night before.  Fasting today, with the exception of vitamins and cocoa with honey"
* Activities.csv
  * This is activity data export from Garmin Connect
  * Script will import activity data from Garmin and input into Cronometer as an activity on the correlating date.
  * .csv header + example data
    * Activity Type,Date,Favorite,Title,Distance,Calories,Activity Time,Avg HR,Max HR,Aerobic TE,Avg Run Cadence,Max Run Cadence,Avg Speed,Max Speed,Elev Gain,Elev Loss,Avg Stride Length,Avg Vertical Ratio,Avg Vertical Oscillation,Avg Ground Contact Time,Avg GCT Balance,Avg Bike Cadence,Training Stress Score®,Grit,Flow,Total Strokes,Avg. Swolf,Avg Stroke Rate,Total Reps,Total Poses,Max Depth,Bottom Time,Min Temp,Surface Interval,Decompression,Water Type,Best Lap Time,Number of Laps,Max Temp
    * Cycling,7/4/2020 15:36,FALSE,Portland Cycling,7.16,520,0:49:12,132,165,3.2,--,--,8.7,23.5,223,276,0,0,0,--,--,--,0,0,0,--,--,--,--,--,--,0:00,80.6,0:00,No,--,22:30.4,2,0
* Nutrition-Summary.csv
  * This is the exported macro nutritional data from MyFitnessPal
  * Script will import the data and add to corresponding date and meal in Cronometer
  * .csv + example data
    * Date,Meal,Energy,Fat (g),Saturated,Polyunsaturated,Monounsaturated,Trans-Fat,Cholesterol,Sodium (mg),Potassium,Carbohydrates (g),Fiber,Sugars,Protein (g),Vitamin A,Vitamin C,Calcium,Iron,Note
    * 6/28/2011,Breakfast,415,9.5,3,4,1,0,75,230,1050,53,8,33,36,87,165,55,106,
* chromedriver.exe => required.  Make sure the version of chromedriver matches the version of your chrome browser


## Available Scripts

    "build": "npm run build --prefix client",
    "start": "nodemon server.js",
    "client": "npm start --prefix client",
    "dev": "concurrently -n 'server,client' -c 'red,green'  \"nodemon server.js\" \"npm run client\""
