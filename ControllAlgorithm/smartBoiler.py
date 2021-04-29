"""
Implementation of SmartBoiler control algorithm. Plans socket switching based on hot water usage.

author: J.Mitura (xmitur01)
version: 1.0
"""
import influxdb
import kasa
import asyncio
import math
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import time

import numpy as np


# Time/date calculations
def getDateNDaysAgo(n_days):
    """Calculate date before N days ago.

    :param n_days: int number of days
    :return: string date YYYY-MM-DD
    """
    today = datetime.now()
    n_days_date = today - timedelta(days=n_days)

    return str(n_days_date.date())


def formatTime(t):
    """Check if hour, minute, second variable has format hh, mm or ss if not change format.

    :param t: string time hh, mm or ss
    :return: string time in correct format eg. hh=02 instead of hh=2
    """
    if len(t) < 2:
        t = "0" + t

    return t


# DB queries and operations
def queryDataForDay(day):
    """Query Influxdb for temperature data of given day.

    :param day: string date YYYY-MM-DD
    :return: tuple[list[pipe temperatures], list[tank temperatures]]
    """
    start = str(day + 'T00:00:00Z')
    to = str(day + 'T23:59:59Z')

    date_val = {'start_time': start, 'end_time': to}

    res_pipe = client.query('SELECT "value" FROM temp_pipe WHERE time >= $start_time AND time <= $end_time',
                            bind_params=date_val)
    res_tank = client.query('SELECT "value" FROM temp_tank WHERE time >= $start_time AND time <= $end_time',
                            bind_params=date_val)

    return pointsToList(res_pipe.get_points()), pointsToList(res_tank.get_points())


def queryLatestTankValue():
    """Query Influxdb for latest tank temperature record.

    :return: dictionary{time:string, last:float}
    """
    res_tank = client.query('SELECT last("value") FROM temp_tank')

    return next(res_tank.get_points())


def queryFirstTankValue():
    """Query Influxdb for first tank temperature record.

    :return: dictionary{time:string, last:float}
    """
    res_tank = client.query('SELECT first("value") FROM temp_tank')

    return next(res_tank.get_points())


def pointsToList(points):
    """Convert query response from point in time, value format to list with values only.

    :param points: query response
    :return: list[oldest value, -> , newest value]
    """
    list_of_points = []
    for point in points:
        list_of_points.append(point)

    return list_of_points


# Calculations
def heatEnergy(desired_temp, actual_temp):
    """Calculate heat energy based on temperature difference.

    :param desired_temp: float number
    :param actual_temp: float number
    :return: float heat
    """
    q = tank_volume * thermal_capacity_H2O * (desired_temp - actual_temp)

    return q


def timeTillHeated(desired_temp, actual_temp):
    """Calculate time needed to heat water on specific temperature. Using heater power and eta.

    :param desired_temp: float number
    :param actual_temp: float number
    :return: float time in minutes
    """
    t = heatEnergy(desired_temp, actual_temp) / (heater_power * eta)

    return t / 60


def calculateUsedWater(temp_tank_before, temp_tank_after):
    """Calculate amount of used water based on temperature change and tank volume.

    :param temp_tank_before: float number
    :param temp_tank_after: float number
    :return: float used water volume in liters
    """
    used_w = (tank_volume * (temp_tank_after - temp_tank_before)) / (avr_cold_H2O_temp - temp_tank_before)

    return used_w


def normalizeUsedWater(temp_tank_before, temp_tank_after, used_volume):
    """Calculate amount of used water with normalized temperature 37deg of C

    :param temp_tank_before: float number
    :param temp_tank_after: float number
    :param used_volume: float volume in liters
    :return: float used water in liters
    """
    # mean = (temp_tank_before + temp_tank_after)/2

    normalized_usage = used_volume + (
                (used_volume * (temp_tank_before - normal_H2O_temp)) / (normal_H2O_temp - avr_cold_H2O_temp))

    return normalized_usage


def calculateMaxProductionCapability(actual_tank_temp):
    """Calculate maximum available water volume when using water of temperature 37deg of C

    :param actual_tank_temp: float number
    :return: float available water in liters
    """
    max_prod = tank_volume + (
            tank_volume * (actual_tank_temp - normal_H2O_temp) / (normal_H2O_temp - avr_cold_H2O_temp))

    return max_prod


def minTankTemp(water_usage):
    """Calculate minimum tank temperature which satisfies predicted usage of water of temperature 37deg of C

    :param water_usage: float number
    :return: float number temp in deg of C
    """
    min_temp = ((limit_tank_temp * tank_volume) - (avr_cold_H2O_temp * water_usage)) / (tank_volume - water_usage)

    return min_temp


# calculations based on experiment, used due to lack of analog thermometer shaft on tank, accurate in range 40 to 70 deg
def wrapTempToWaterTemp(temp_before, temp_after):
    """Calculates actual temperature of water in tank based on wrap temperature.

    :param temp_before: float number
    :param temp_after: float number
    :return: float number temp in deg of C
    """
    diff = 13.5  # difference between tank wrap and water temperature at when sensor at 42 deg
    diff_change = 0.525  # diff change per 0.1 change on sensor
    water_change = 0.625  # water temperature change per 0.1 change on sensor

    if temp_before >= 42:
        real_before = temp_before + ((temp_before - 42) * 10 * diff_change + diff)
    elif temp_before < 42:
        real_before = temp_before + (diff - ((42 - temp_before) * 10 * diff_change))
    # real_before = temp_before + diff

    if temp_before < 38:
        real_before = temp_before  # air temperature plays more significant role

    real_after = real_before + (temp_after - temp_before) * 10 * water_change

    return real_before, real_after


# Data filters
def detectFallingSeq(points_list):
    """Find falling temperatures sequences in given list and stores beginnings and ends of them in list.
    Always with format [seq1 start index, seq1 end index, seq2 start index, seq2 end index, ...]

    :param points_list: list of pipe temperatures
    :return: list of indexes
    """
    falling = False
    index_list = []

    for i in range(2, (len(points_list) - 1)):
        actual = points_list[i]['value']
        prev = points_list[i - 1]['value']
        prev_prev = points_list[i - 2]['value']

        if float(actual) < float(prev) and float(actual) < float(prev_prev) and (not falling):
            if (float(prev_prev) - float(actual)) >= 0.2:  # Calibration to not detect falling air temperature
                index_list.append(i - 2)
                falling = True
        elif float(actual) > float(prev) and float(actual) > float(prev_prev) and falling:
            index_list.append(i)
            falling = False

    return index_list


def afternoonMinimum(data_list):
    """Find index of hour where afternoon water usage minimum is located, searching between 13pm and 15pm.

    :param data_list: list of floats, length = 24
    :return: int number index
    """
    index = 12
    tmp = data_list[12]
    for i in range(13, 15):
        if tmp > data_list[i]:
            tmp = data_list[i]
            index = i

    return index


# Data process
def dailyUsagePer15minn(index_list, tank_data_list):
    """Process tank temperatures series to water usage series divided into 96 15 minutes intervals, where each
    interval has value in liters equal to used normalized hot water(37deg of c).

    :param index_list: list of indexes
    :param tank_data_list: list of tank temperatures
    :return: list of numbers, length = 96
    """
    first_use = tank_data_list[index_list[1]]
    hh_mm = first_use['time'].split('T')[1]
    zero_intervals = int(hh_mm[0:2]) * 4  # from midnight till first use hours
    zero_intervals += int(hh_mm[3:5]) // 15  # floor division for minutes

    usage = [0] * zero_intervals  # fill intervals till first use of day

    for i in range(0, len(index_list) - 1, 2):
        tank_before = float(tank_data_list[index_list[i]]['value'])
        tank_after = float(tank_data_list[index_list[i + 1]]['value'])

        water_before, water_after = wrapTempToWaterTemp(temp_before=tank_before, temp_after=tank_after)

        used = calculateUsedWater(temp_tank_before=water_before, temp_tank_after=water_after)

        # add new interval with usage or extend last, depending on time
        if i > 0:
            t = tank_data_list[index_list[i]]['time'].split('T')[1]
            past = tank_data_list[index_list[i - 2]]['time'].split('T')[1]

            if (int(t[0:2]) - int(past[0:2])) == 0 and ((int(t[3:5]) // 15) == (int(past[3:5]) // 15)):
                usage[-1] = float(usage[-1]) + round(abs(normalizeUsedWater(
                    temp_tank_before=water_before, temp_tank_after=water_after, used_volume=used)), 2)
            else:
                usage.append(round(abs(normalizeUsedWater(temp_tank_before=water_before,
                                                          temp_tank_after=water_after, used_volume=used)), 2))
        else:
            usage.append(round(abs(normalizeUsedWater(temp_tank_before=water_before,
                                                      temp_tank_after=water_after, used_volume=used)), 2))

        # fill gaps between intervals with usage by intervals with 0
        if i + 2 <= len(index_list) - 1:
            last_time = tank_data_list[index_list[i]]['time'].split('T')[1]
            next_time = tank_data_list[index_list[i + 2]]['time'].split('T')[1]
            hour_difference = (int(next_time[0:2]) - int(last_time[0:2]))

            if hour_difference == 0:
                gap = ((int(next_time[3:5]) // 15) - (int(last_time[3:5]) // 15)) - 1
                if gap > 0:
                    usage.extend([0] * gap)
            elif hour_difference == 1:
                gap = (4 - ((int(last_time[3:5]) // 15) + 1)) + (int(next_time[3:5]) // 15)
                if gap > 0:
                    usage.extend([0] * gap)
            else:
                gap = (4 - ((int(last_time[3:5]) // 15) + 1)) + (int(next_time[3:5]) // 15)
                gap += (hour_difference - 1) * 4
                if gap > 0:
                    usage.extend([0] * gap)

    # fill intervals from last use of day till midnight
    last_use = tank_data_list[index_list[-2]]
    hh_mm = last_use['time'].split('T')[1]
    gap = ((24 - int(hh_mm[0:2])) - 1) * 4
    gap += 4 - ((int(hh_mm[3:5]) // 15) + 1)
    if gap > 0:
        usage.extend([0] * gap)

    return usage


def usage15minTo1hTransform(usage_list):
    """Transforms series of water usage in 15 minutes intervals into 1 hour intervals.

    :param usage_list: list of numbers
    :return: list of numbers(usage hourly)
    """
    usage = []
    for i in range(0, len(usage_list) - 1, 4):
        h = float(usage_list[i]) + float(usage_list[i + 1]) + float(usage_list[i + 2]) + float(usage_list[i + 3])
        usage.append(round(h, 2))

    return usage


def ema(values, n):
    """Calculates actual value of exponential moving average of given series with certain length.

    :param values: list of floats
    :param n: int ema length
    :return: float actual ema value
    """
    ema_list = []
    sma = sum(values) / n
    multiplier = 2 / (n + 1)

    # EMA(current) = Val(now) * multiplier + EMA(prev) * (1 - multiplier)
    if values:
        ema_list.append(values[0] * multiplier + sma * (1 - multiplier))
        for i in range(1, len(values) - 1):
            val = values[i] * multiplier + ema_list[-1] * (1 - multiplier)
            ema_list.append(val)
    else:
        return None

    return ema_list[-1]


def predict(list_of_usage_lists):   # list of lists [oldest data, -> ,newest data]
    """Predict today usage based on historical usage of 2,3 or 4 previous same days of week.

    :param list_of_usage_lists: list of time series usage lists
    :return: list of floats(hourly usage prediction)
    """
    p = []
    n = len(list_of_usage_lists)

    if n == 2:
        u1 = list_of_usage_lists[1]
        u2 = list_of_usage_lists[0]
        for i in range(0, 24):
            p.append(round(ema([u2[i], u1[i]], n), 2))
    elif n == 3:
        u1 = list_of_usage_lists[2]
        u2 = list_of_usage_lists[1]
        u3 = list_of_usage_lists[0]
        for i in range(0, 24):
            p.append(round(ema([u3[i], u2[i], u1[i]], n), 2))
    elif n == 4:
        u1 = list_of_usage_lists[3]
        u2 = list_of_usage_lists[2]
        u3 = list_of_usage_lists[1]
        u4 = list_of_usage_lists[0]
        for i in range(0, 24):
            p.append(round(ema([u4[i], u3[i], u2[i], u1[i]], n), 2))

    return p


# MAPE function for prediction accuracy determination
def MAPE(actual, predicted):
    """Mean average percentage error, used in prediction plotting.

    :param actual: real value series
    :param predicted: predicted value series
    :return:
    """
    mape = np.mean(np.abs((actual - predicted) / actual)) * 100
    return mape


# Socket switching
def turnOff():
    """Switch plug to off state, using asyncio.run call."""
    asyncio.run(plug.turn_off())


def turnOn():
    """Switch plug to on state, using asyncio.run call."""
    asyncio.run(plug.turn_on())


# Control functions
def produceUsage(falling_sequence_indexes, tank_data_list):
    """Creates hot water usage hourly series.

    :param falling_sequence_indexes: list of indexes(falling seq starts, ends)
    :param tank_data_list: list tank temperature series
    :return: list of hourly predicted water usage 24h or empty list if error occurs
    """
    u = []
    if falling_sequence_indexes:
        u = dailyUsagePer15minn(index_list=falling_sequence_indexes, tank_data_list=tank_data_list)
        u = usage15minTo1hTransform(usage_list=u)

    return u


# in normal situation when sensor is in shaft instead of on wrap comment first if sequence
# and change real on actual_temp
def checkLimitTemp(sched):
    """Function run regularly in 5 minute intervals to check if temperature of water inside tank didn't fall below
    allowed minimum temperature 40 deg of C. If water temp is below limit, set plug state on for 4 minutes.

    :param sched: APScheduler object, containing scheduler used in the script
    """
    diff = 13.5  # difference between tank wrap and water temperature at when sensor at 42 deg
    diff_change = 0.525  # diff change per 0.1 change on sensor

    actual_temp = queryLatestTankValue()['last']

    if actual_temp >= 42:
        real = actual_temp + ((actual_temp - 42) * 10 * diff_change + diff)
    elif actual_temp < 42:
        real = actual_temp + (diff - ((42 - actual_temp) * 10 * diff_change))

    if real <= 40:
        turnOn()

        now = datetime.now()
        now_plus_10 = now + timedelta(minutes=4)
        t_off = str(now_plus_10).split('.')[0]

        sched.add_job(func=turnOff, trigger='date', next_run_time=t_off)


def baseSwitching(sched):
    """Function for basic socket switching plan(static hours 1am to 6am, 13pm to 14pm).
    Used before enough data is gathered(first 14 days of run) or when prediction is not available.

    :param sched: APScheduler object, containing scheduler used in the script
    """
    d = datetime.date(datetime.now())

    t_on = str(d) + " " + "01:00:00"
    t_off = str(d) + " " + "06:00:00"
    t_on2 = str(d) + " " + "13:00:00"
    t_off2 = str(d) + " " + "14:00:00"

    sched.add_job(func=turnOn, trigger='date', next_run_time=t_on)
    sched.add_job(func=turnOff, trigger='date', next_run_time=t_off)
    sched.add_job(func=turnOn, trigger='date', next_run_time=t_on2)
    sched.add_job(func=turnOff, trigger='date', next_run_time=t_off2)


def planSwitchSocket(prediction, sched):
    """Schedule socket turn on and off based on water usage prediction and time needed for reaching desired temperature.
    Used in first planning before afternoon.

    :param prediction: list of numbers with water usage prediction
    :param sched: APScheduler object, containing scheduler used in the script
    """
    afternoon_min = afternoonMinimum(prediction)
    usage_sum = sum(prediction[0:(afternoon_min - 1)])
    t = math.ceil(timeTillHeated(minTankTemp(usage_sum), limit_tank_temp))
    first_use = next((index for index, value in enumerate(prediction) if value != 0), None)

    h = str((first_use * 60 - (t + 5)) // 60)
    m = str((first_use * 60 - (t + 5)) % 60)

    h = formatTime(h)
    m = formatTime(m)
    d = datetime.date(datetime.now())

    t_on = str(d) + " " + h + ":" + m + ":00"
    t_off = str(d) + " " + formatTime(str(first_use)) + ":00:00"
    t_afternoon = str(d) + " " + formatTime(str(afternoon_min)) + ":00:00"

    sched.add_job(func=turnOn, trigger='date', next_run_time=t_on)
    sched.add_job(func=turnOff, trigger='date', next_run_time=t_off)
    sched.add_job(func=switchSocketAfternoon, args=[prediction, sched, afternoon_min], trigger='date',
                  next_run_time=t_afternoon)


def switchSocketAfternoon(prediction, sched, afternoon_min_index):
    """Schedule socket turn on and off based on water usage prediction and time needed for reaching desired temperature
    and actual tank temperature. Used in afternoon planning.

    :param prediction: list of numbers with water usage prediction
    :param sched: APScheduler object, containing scheduler used in the script
    :param afternoon_min_index: index of afternoon hour with minimum water usage between 13pm and 15pm
    """
    usage_sum = sum(prediction[afternoon_min_index:23])
    actual_temp = queryLatestTankValue()['last']
    t = math.ceil(timeTillHeated(minTankTemp(usage_sum), actual_temp))
    if t > 0:
        turnOn()

        h = str((afternoon_min_index * 60 + t + 5) // 60)
        m = str((afternoon_min_index * 60 + t + 5) % 60)

        h = formatTime(h)
        m = formatTime(m)
        d = datetime.date(datetime.now())

        t_off = str(d) + " " + h + ":" + m + ":00"
        sched.add_job(func=turnOff, trigger='date', next_run_time=t_off)


def makeForecast(sched):
    """Main logical function of the script. Run regularly after every midnight. Determines the state of algorithm based
    on days pass since day with first record and decides if prediction and plug switching is made on 2,3, or 4 same
    past days of week or can't be done so base switching has to be applied.

    :param sched:
    :return:
    """
    first_record_time = queryFirstTankValue()['time']
    first_date = first_record_time.split('T')[0]
    today_date = datetime.date(datetime.now())
    d1 = datetime.date(datetime(int(first_date.split('-')[0]), int(first_date.split('-')[1]),
                                int(first_date.split('-')[2])))

    d_dif = (today_date - d1).days
    prd = []

    if d_dif <= 14:
        baseSwitching(sched=sched)
    elif 14 < d_dif <= 21:
        list_p1, list_t1 = queryDataForDay(day=getDateNDaysAgo(7))
        list_p2, list_t2 = queryDataForDay(day=getDateNDaysAgo(14))

        falling_seq_indexes_1 = detectFallingSeq(points_list=list_p1)
        falling_seq_indexes_2 = detectFallingSeq(points_list=list_p2)

        use1 = produceUsage(falling_seq_indexes_1, list_t1)
        use2 = produceUsage(falling_seq_indexes_2, list_t2)
        if use1 and use2 and len(use1) == 24 and len(use2) == 24:
            prd = predict([use2, use1])
            planSwitchSocket(prediction=prd, sched=sched)
        else:   # run base like when dif days < 14
            baseSwitching(sched=sched)

    elif 21 < d_dif <= 28:
        list_p1, list_t1 = queryDataForDay(day=getDateNDaysAgo(7))
        list_p2, list_t2 = queryDataForDay(day=getDateNDaysAgo(14))
        list_p3, list_t3 = queryDataForDay(day=getDateNDaysAgo(21))

        falling_seq_indexes_1 = detectFallingSeq(points_list=list_p1)
        falling_seq_indexes_2 = detectFallingSeq(points_list=list_p2)
        falling_seq_indexes_3 = detectFallingSeq(points_list=list_p3)

        use1 = produceUsage(falling_seq_indexes_1, list_t1)
        use2 = produceUsage(falling_seq_indexes_2, list_t2)
        use3 = produceUsage(falling_seq_indexes_3, list_t3)
        if use1 and use2 and use3 and len(use1) == 24 and len(use2) == 24 and use3 == 24:
            prd = predict([use3, use2, use1])
            planSwitchSocket(prediction=prd, sched=sched)
        else:   # run base like when dif days < 14
            baseSwitching(sched=sched)

    elif d_dif > 28:
        list_p1, list_t1 = queryDataForDay(day=getDateNDaysAgo(7))
        list_p2, list_t2 = queryDataForDay(day=getDateNDaysAgo(14))
        list_p3, list_t3 = queryDataForDay(day=getDateNDaysAgo(21))
        list_p4, list_t4 = queryDataForDay(day=getDateNDaysAgo(28))

        falling_seq_indexes_1 = detectFallingSeq(points_list=list_p1)
        falling_seq_indexes_2 = detectFallingSeq(points_list=list_p2)
        falling_seq_indexes_3 = detectFallingSeq(points_list=list_p3)
        falling_seq_indexes_4 = detectFallingSeq(points_list=list_p4)

        use1 = produceUsage(falling_seq_indexes_1, list_t1)
        use2 = produceUsage(falling_seq_indexes_2, list_t2)
        use3 = produceUsage(falling_seq_indexes_3, list_t3)
        use4 = produceUsage(falling_seq_indexes_4, list_t4)
        if use1 and use2 and use3 and use4 and len(use1) == 24 and len(use2) == 24 and use3 == 24 and use4 == 24:
            prd = predict([use4, use3, use2, use1])
            planSwitchSocket(prediction=prd, sched=sched)
        else:   # run base like when dif days < 14
            baseSwitching(sched=sched)


# ===================================== #
#                 MAIN                  #
# ===================================== #

# Constants
plugIP = "192.168.1.100"  # change to Your socket IP
tank_volume = 80  # change to Your tank volume [l]
heater_power = 2400  # change to Your tank heater power [W]

avr_cold_H2O_temp = 8.7  # [C]
normal_H2O_temp = 37  # [C]
thermal_capacity_H2O = 4175  # at 40 degrees
limit_tank_temp = 40  # [C]
eta = 0.98  # heater effectivity

# Initialize database connection
client = influxdb.InfluxDBClient(host='localhost', port=8086, username='telegraf', password='telegraf',
                                 database='sensors')
# Initialize smart plug
plug = kasa.SmartPlug(plugIP)

# Initialize scheduler and plan main events
scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(func=makeForecast, args=[scheduler], trigger='cron', hour='0', minute='15')
scheduler.add_job(func=checkLimitTemp, args=[scheduler], trigger='interval', minutes=5)

# Infinite loop for continuous script run
while True:
    time.sleep(1)
