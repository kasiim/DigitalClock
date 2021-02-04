from machine import Pin, Timer, RTC, freq
import time
import micropython
micropython.alloc_emergency_exception_buf(100)


freq(240000000)

enable_p1 = Pin(23, Pin.OUT)
enable_p2 = Pin(22, Pin.OUT)
enable_p3 = Pin(21, Pin.OUT)
enable_p4 = Pin(19, Pin.OUT)

clear_p = Pin(18, Pin.OUT)
data_p = Pin(2, Pin.OUT)
latch_p = Pin(4, Pin.OUT)
sr_p = Pin(5, Pin.OUT)

buzzer_p = Pin(15, Pin.OUT)
buzzer_p.off()

button1_p = Pin(26, Pin.IN, Pin.PULL_DOWN)
button2_p = Pin(25, Pin.IN, Pin.PULL_DOWN)
snooze_p = Pin(33, Pin.IN, Pin.PULL_DOWN)

clear_p.on()

digits = [
    '00111111',
    '00000110',
    '01011011',
    '01001111',
    '01100110',
    '01101101',
    '01111101',
    '00000111',
    '01111111',
    '01101111'
] 

enables = [
    enable_p1,
    enable_p2,
    enable_p3,
    enable_p4
]

def do_connect(essid, password):
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(essid, password)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())

def show_digit(digit):
    #nihkeregister tühjaks
    clear_p.off()
    #võimaldab kirjutamise nihkeregistrisse
    clear_p.on()

    #käib läbi numbri bitid
    for bit in digit:
        if bit == '0':
            data_p.off()
        else:
            data_p.on()

        # biti nihutamine
        sr_p.on() #kuna nihkregister tuvastab tõusvat fronti
        sr_p.off() # madala signaali tekitamine, et saaks järgmist nihutamist teha

    # nihkregistri sisu väljastamine
    latch_p.on() # tõusev front
    latch_p.off() # madala signaali tekitamine, et saaks järgmist kuvamist teha

for enable_p in enables:
    enable_p.on()


def show_clock(args):
    global clock_mode
    for index, enable_p in enumerate(enables):
        if clock_mode:
            current_digit = int(clock_string[index]) # annab segmendi arvulise väärtuse muutujast clock
        else:
            current_digit = int(alarm_string[index])
        show_digit(digits[current_digit]) # väljastab nihkeregistrist väärtuse andmeliinile
        enable_p.off() # valin, millisele segmendile näitan väärtust
        time.sleep_ms(2)
        enable_p.on() # lülitab segmendi välja

def get_time():
    #võtab internetist NTP aja, alustab kella numbrite kuvamist 
    import ntptime  
    ntptime.settime()

    clock = RTC().datetime()
    seconds = clock[6]
    seconds_left = 60 - seconds

    oneshot_timer = Timer(1)
    oneshot_timer.init(period=seconds_left * 1000, mode=Timer.ONE_SHOT, callback=start_periodic_timer_for_clock)

def update_clock_string(args):
    #uuendab kella muutujat
    global clock_string
    clock = RTC().datetime()
    hours = str(clock[4])
    minutes = str(clock[5])
    # pane timer seisma, et alati muudetaks kellaaega
    screen_refresh = Timer(0)
    screen_refresh.deinit()
    #nulli kuvamiseks
    clock_string = (hours if len(hours) > 1 else '0' + hours) + (minutes if len(minutes) > 1 else '0' + minutes)

    # paneb uuesti timeri tööle et ekraanil numbreid näidata
    screen_refresh.init(period=10, mode=Timer.PERIODIC, callback=show_clock)
    

def start_periodic_timer_for_clock(args):
    #loeb 60 sekundi, uuendab kella
    update_clock_string(1)
    periodic_timer = Timer(1)
    periodic_timer.init(period=60000, mode=Timer.PERIODIC, callback=update_clock_string)

def timezone_correction(hours_to_add):
    rtc = RTC()
    ntp_clock = list(rtc.datetime())# teeme listiks, kuna vaja muuta
    ntp_clock[4] += hours_to_add
    rtc.datetime(tuple(ntp_clock)) #uuenda real time clock rtc muudetud kellajaga

def alarm_sound(args):
    for x in range(4):
        buzzer_p.value(1)
        time.sleep(0.5)
        buzzer_p.value(0)
        time.sleep(0.5)

def set_alarm(alarm_hours, alarm_minutes):
    rtc = RTC()
    current_time = rtc.datetime()

    current_hours = current_time[4]
    current_minutes = current_time[5]
    current_seconds = current_hours * 3600 + current_minutes * 60 + current_time[6]
    alarm_seconds = alarm_hours * 3600 + alarm_minutes * 60
    seconds_to_alarm = alarm_seconds - current_seconds 
    #vastavalt sellele kas sekudnite vahe on neg või pos on äratus järgmisel päeval. 24*3600=86400
    ms_to_alarm = (seconds_to_alarm if seconds_to_alarm > 0 else 86400 + seconds_to_alarm) * 1000
    # print(seconds_to_alarm, ms_to_alarm)
    alarm_timer = Timer(2)
    alarm_timer.init(period=ms_to_alarm, mode=Timer.ONE_SHOT, callback=alarm_sound)      

def button_handler(args):
    global button1_state
    global button2_state
    global snooze_state
    global button1_start
    global button2_start
    global snooze_start
    global dst_state
    global clock_mode
    global setting_state
    global alarm_string
    global clock_string

    if (button1_state != button1_p.value()) and button1_state == 0:
        print("Button 1 was pressed")
        button1_start = time.ticks_ms()
    if (button2_state != button2_p.value()) and button2_state == 0:
        print("Button 2 was pressed")
        button2_start = time.ticks_ms()
    if (snooze_state != snooze_p.value()) and snooze_state == 0:
        print("Snooze was pressed")
        snooze_start = time.ticks_ms()

    if (button1_state != button1_p.value()) and button1_state == 1:
        button1_delta = time.ticks_diff(time.ticks_ms(), button1_start)
        print("Button 1 was released, button was held for", button1_delta, 'ms')
        if button1_delta > 2000:
            if dst_state:
                timezone_correction(-1)
                dst_state = 0
            else:
                timezone_correction(1)
                dst_state = 1
            update_clock_string(1)

        elif clock_mode == 0:
            if setting_state:
                change_alarm_hours(-1)
            else:
                change_alarm_minutes(-1)

    if (button2_state != button2_p.value()) and button2_state == 1:
        button2_delta = time.ticks_diff(time.ticks_ms(), button2_start)
        print("Button 2 was released, button was held for", button2_delta, 'ms')
        if button2_delta > 2000:
            if clock_mode:
                clock_mode = 0
                alarm_string = clock_string
            else:
                set_alarm(int(alarm_string[0:2]), int(alarm_string[2:]))
                clock_mode = 1
            print(clock_mode)
        elif clock_mode == 0:
            if setting_state:
                change_alarm_hours(1)
            else:
                change_alarm_minutes(1)


    if (snooze_state != snooze_p.value()) and snooze_state == 1:
        snooze_delta = time.ticks_diff(time.ticks_ms(), snooze_start)
        print("Snooze was released, button was held for", snooze_delta, 'ms')
        if clock_mode == 0:
            if setting_state:
                setting_state = 0
            else:
                setting_state = 1
            

    button1_state = button1_p.value()
    button2_state = button2_p.value()
    snooze_state = snooze_p.value()

def change_alarm_hours(change):
    global alarm_string
    hours = int(alarm_string[0:2])
    if change == 1:
        hours += 1
    elif change == -1:
        hours -= 1
    hours %= 24
    hours = str(hours)
    alarm_string = (hours if len(hours) > 1 else '0' + hours) + alarm_string[2:]

def change_alarm_minutes(change):
    global alarm_string
    minutes = int(alarm_string[2:])
    if change == 1:
        minutes += 1
    elif change == -1:
        minutes -= 1
    minutes %= 60
    minutes = str(minutes)
    alarm_string = alarm_string[0:2] + (minutes if len(minutes) > 1 else '0' + minutes)

do_connect('ssid', 'password')

get_time()

timezone_correction(3)

clock_string = '1234'
alarm_string = '1234'

button1_state = 0
button2_state = 0
snooze_state = 0

button1_start = 0
button2_start = 0
snooze_start = 0

dst_state = 1
clock_mode = 1

setting_state = 1

update_clock_string(1)

screen_refresh = Timer(0)

screen_refresh.init(period=10, mode=Timer.PERIODIC, callback=show_clock)

button_checker = Timer(3)

button_checker.init(period=100, mode=Timer.PERIODIC, callback=button_handler)

# button1_p.irq(handler=button_test, trigger=Pin.IRQ_RISING)

