# CGM Analysis
This script will take in data from xDrip continuous Glucose tracking, Garmin Activity Data, Cronometer Nutritional Data, and Oura Sleep Data and generate several visuals to correlate food, activity, sleep and glucose response data.  The step response is shown as a black line over a 4 hour timespan for each food/meal.  The graph is colored green in the "safe" glucose ranges of above 70 mmol/dl and below 120 mmol/dl.  If an activity was included in the 4 hour response window the graph will be colored blue and calorie and activity name is added for reference.

## Visuals
* Glucose Step Response for each meal: Matplotlib or Bodeh available
![MealActivity1](https://user-images.githubusercontent.com/50993714/164490776-af9265e1-7a5f-4228-abb5-edc90db9023a.png)
![MealActivity](https://user-images.githubusercontent.com/50993714/164490767-afaf389a-7940-4817-a44f-7c3a519b0a35.png)
* HeatMap displaying Glucose over time periods and showing corresponding meals.
![HeatMap](https://user-images.githubusercontent.com/50993714/164490759-2cf3598b-d313-46a8-a8d4-9bec9ad208d3.png)
* Multiplot showing all step responses.  Meals are selectable to compare step responses in the same time period.
![MultiPlot](https://user-images.githubusercontent.com/50993714/164490734-4ace16a2-a499-4338-9816-fac4c48e9da2.png)
## Requirements

In the root directory:

* xDripCGM.csv
  * This is CGM Data export from xDrip
  * Script will import CGM data.
  * .csv header + example data
    * DAY,TIME,UDT_CGMS,BG_LEVEL,CH_GR,BOLUS,REMARK
    * 9/1/2020,7:25,97,,,,
* GarminActivities.csv
  * This is activity data export from Garmin Connect
  * Script will import activity data from Garmin and input into Cronometer as an activity on the correlating date.
  * .csv header + example data
    * Activity Type,Date,Favorite,Title,Distance,Calories,Activity Time,Avg HR,Max HR,Aerobic TE,Avg Run Cadence,Max Run Cadence,Avg Speed,Max Speed,Elev Gain,Elev Loss,Avg Stride Length,Avg Vertical Ratio,Avg Vertical Oscillation,Avg Ground Contact Time,Avg GCT Balance,Avg Bike Cadence,Training Stress Score®,Grit,Flow,Total Strokes,Avg. Swolf,Avg Stroke Rate,Total Reps,Total Poses,Max Depth,Bottom Time,Min Temp,Surface Interval,Decompression,Water Type,Best Lap Time,Number of Laps,Max Temp
    * Cycling,7/4/2020 15:36,FALSE,Portland Cycling,7.16,520,0:49:12,132,165,3.2,--,--,8.7,23.5,223,276,0,0,0,--,--,--,0,0,0,--,--,--,--,--,--,0:00,80.6,0:00,No,--,22:30.4,2,0
* CronoServings.csv
  * This is the exported macro nutritional data from MyFitnessPal
  * Script will import the data and add to corresponding date and meal in Cronometer
  * .csv + example data
    * Date,Meal,Energy,Fat (g),Saturated,Polyunsaturated,Monounsaturated,Trans-Fat,Cholesterol,Sodium (mg),Potassium,Carbohydrates (g),Fiber,Sugars,Protein (g),Vitamin A,Vitamin C,Calcium,Iron,Note
    * 6/28/2011,Breakfast,415,9.5,3,4,1,0,75,230,1050,53,8,33,36,87,165,55,106,
* OuraSleepData.csv
  * This is a .csv export from Oura.com.
  * Script will import biometric data for date under "uncategorized"
  * .csv header + example data
    * date,Sleep Score,Total Sleep Score,REM Sleep Score,Deep Sleep Score,Sleep Efficiency Score,Restfulness Score,Sleep Latency Score,Sleep Timing Score,Total Bedtime,Total Sleep Time,Awake Time,REM Sleep Time,Light Sleep Time,Deep Sleep Time,Restless Sleep,Sleep Efficiency,Sleep Latency,Sleep Timing,Sleep Timing,Bedtime Start,Bedtime End,Average Resting Heart Rate,Lowest Resting Heart Rate,Average HRV,Temperature Deviation (°C),Respiratory Rate,Activity Score,Stay Active Score,Move Every Hour Score,Meet Daily Targets Score,Training Frequency Score,Training Volume Score,Recovery Time Score,Activity Burn,Total Burn,Target Calories,Steps,Daily Movement,Inactive Time,Rest Time,Low Activity Time,Medium Activity Time,High Activity Time,Non-wear Time,Average MET,Long Periods of Inactivity,Readiness Score,Previous Night Score,Sleep Balance Score,Previous Day Activity Score,Activity Balance Score,Temperature Score,Resting Heart Rate Score,HRV Balance Score,Recovery Index Score
    * 2020-03-04,74,74,34,99,96,53,72,100,27300,24690,2610,2400,14490,7800,41,90,270,13170,,2020-03-03T22:14:42-08:00,2020-03-04T05:49:42-08:00,56.63,46,69,-0.29,13.75,87,53,100,78,100,97,100,278,2545,350,5703,4799,690,504,234,12,0,0,1.34375,0,67,65,0,0,0,93,100,0,20

  