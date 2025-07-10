from django.shortcuts import render
from django.http import HttpResponse
from .models import CourseTerm, CourseCode, CourseNumber, CourseSection, CourseTime, CourseDay, Course
from collections import defaultdict
from datetime import datetime, timedelta
import pprint


# from  import Timetable

# def landing_page(request):
#     return render(request, 'timetable/base.html', {})

# make each request an array. Display the array in the filters tool in the frontend.
# when filtering, iterate through courses and filter by current iteration
    # - do this for every filter
    
'''
#increment the start time by 15 minutes until you hit the end time - 15 minutes
  as you increment, add to corresponding key in the dictionary. Minus 15 minutes because each key represents a 15 minute interval.
10:00: 1
10:15: 1, 2
10:30: 1, 2
10:45: 1, 2, 3
11:00: 3
11:15: 3,
11:30: 3,  
11:45: 3,
12:00

'''

PIXELS_PER_MINUTE = 1  # Adjust this value to change the height of each minute in pixels

def landing_page(request):
    # grabs all data from fixtures 
    hour_list = ["08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"]
    term = CourseTerm.objects.all()
    code = CourseCode.objects.all()
    number = CourseNumber.objects.all()
    section = CourseSection.objects.all()
    time = CourseTime.objects.all()
    day = CourseDay.objects.all()
    
    
    courses = None
    
    #grabs all filters used in the request
    filter_code = request.GET.getlist('code[]')
    filter_number = request.GET.getlist('number[]')
    filter_section = request.GET.getlist('section[]')
    filter_term = request.GET.getlist('term[]')
    filter_start = request.GET.getlist('start[]')
    filter_end = request.GET.getlist('end[]')
    filter_day = request.GET.getlist('day[]')
    

    # filters the fixture data and widdles down to just the filtered output
    if (filter_code or filter_number or filter_section or filter_term or filter_start or filter_end or filter_day):
        courses = Course.objects.all()
    
        if filter_code:
            courses = courses.filter(code__name__in=filter_code)
        if filter_number:
            courses = courses.filter(number__name__in=filter_number)
        if filter_section:
            courses = courses.filter(section__name__in=filter_section)
        if filter_term:
            courses = courses.filter(term__name__in=filter_term)
        if filter_start:
            courses = courses.filter(start__name__in=filter_start)
        if filter_end:
            courses = courses.filter(end__name__in=filter_end)
        if filter_day:
            courses = courses.filter(day__name__in=filter_day)
        
        if courses.exists():
            
            DAYS = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri']
            START_TIME = '08:00'
            END_TIME = '19:00'
            INTERVAL = timedelta(minutes=15)
            start = datetime.strptime(START_TIME, "%H:%M")
            end = datetime.strptime(END_TIME, "%H:%M")

            slots = {}
            current_time = start
            while current_time < end:
                time_str = current_time.strftime("%H:%M")
                for day in DAYS:
                    slots[(day, time_str)] = []  # None = not occupied
                current_time += INTERVAL
            
            # create slots dictionary with all time slots for each day
            
            # iterate through each course and fill the slots dictionary
            
            for course in courses:
                attached_days = course.day.name.split('_')
                for day in attached_days:
                    start_time = course.start.name[:5]  # e.g., '13:00'
                    end_time = course.end.name[:5]  # e.g., '15:00'
                    # Iterate through the time slots for the course
                    current_time = datetime.strptime(start_time, "%H:%M")
                    end_time_dt = datetime.strptime(end_time, "%H:%M")
                    while current_time < end_time_dt:
                        time_str = current_time.strftime("%H:%M")
                        #print("this is the slots", slots)
                        
                        # print("-----------------------------")  
                        # pprint.pprint(slots)
                        # print("-----------------------------")
                        
                        if (day, time_str) in slots:
                            # print(f"Adding {course} to slot {day} at {time_str}")
                            slots[(day, time_str)].append(course)
                        current_time += INTERVAL

                        # "Mon,Tues,Wed"
                        # [Mon, Tues, Wed]
                        # c.${day}_overlap : x
                        
            for slot, course_group in slots.items():
                if len(course_group) > 1:
                    for c in course_group:
                        slot_day, slot_time = slot

                        if getattr(c, f"{slot_day}_overlap_width", None) is None:
                            overlap_width = 1.0 / float(len(course_group)) if len(course_group) > 0 else 1.0
                            overlap_width *= 100
                            overlap_width = round(overlap_width, 2)
                            setattr(c, f"{slot_day}_overlap_width", overlap_width)
                            # calculate offset left
                            setattr(c, f"{slot_day}_offset_left", overlap_width * course_group.index(c))

                            # if offset_left > 0:
                            #     offset_left -= course_group.index(c)
                                
                            # calculate z-index
                            # setattr(c, f"{slot_day}_z_index", course_group.index(c) + 1)
                            
                            # see if it overs 
                            setattr(c, f"{slot_day}_overlaps", True)
                            
                            '''
                            course has attributes of each day dynamically added:
                            - overlap_width
                            - offset_left
                            - z_index
                            - overlaps
                            '''
                            
        for course in courses:
            start = datetime.strptime(course.start.name, "%H:%M:%S")
            end = datetime.strptime(course.end.name, "%H:%M:%S")
            course.duration_minutes = (end - start).seconds // 60
            course.pixel_height = course.duration_minutes * PIXELS_PER_MINUTE
            
            course.offset_top = (start.minute) * PIXELS_PER_MINUTE
            # course.offset_left = course.overlaps
                        
            if course.code.name == "APBI":
                course.color = "#7BDFF2"
            elif course.code.name == "FNH":
                course.color = "#B2F7EF"
            elif course.code.name == "FOOD":
                course.color = "#CBAACB"
            elif course.code.name == "FRE":
                course.color = "#F6C6EA"
            elif course.code.name == "GRS":
                course.color = "#EADB9A"
            elif course.code.name == "LFS":
                course.color = "#FFAAA5"
        
        
        for course in courses:
            course.day_data = {
                "Mon": {
                    "overlap": getattr(course, 'Mon_overlaps', None),
                    "width": getattr(course, 'Mon_overlap_width', None),
                    "left": getattr(course, 'Mon_offset_left', None)
                },
                "Tues": {
                    "overlap": getattr(course, 'Tues_overlaps', None),
                    "width": getattr(course, 'Tues_overlap_width', None),
                    "left": getattr(course, 'Tues_offset_left', None)
                },
                "Wed": {
                    "overlap": getattr(course, 'Wed_overlaps', None),
                    "width": getattr(course, 'Wed_overlap_width', None),
                    "left": getattr(course, 'Wed_offset_left', None)
                },
                "Thurs": {
                    "overlap": getattr(course, 'Thurs_overlaps', None),
                    "width": getattr(course, 'Thurs_overlap_width', None),
                    "left": getattr(course, 'Thurs_offset_left', None)
                },
                "Fri": {
                    "overlap": getattr(course, 'Fri_overlaps', None),
                    "width": getattr(course, 'Fri_overlap_width', None),
                    "left": getattr(course, 'Fri_offset_left', None)
                }
            }
            
            
        day_list = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri']
            
    return render(request, 'timetable/landing_page.html', {
        'hour_list': hour_list,
        'terms': term,
        'codes': code,
        'numbers': number,
        'sections': section,
        'times': time,
        'days': day,
        'courses': courses,
        'day_list': day_list,
        })
    
    