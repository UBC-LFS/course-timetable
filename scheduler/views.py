from django.shortcuts import render
from django.http import HttpResponse
from .models import CourseTerm, CourseCode, CourseNumber, CourseSection, CourseTime, CourseDay, Course
from collections import defaultdict
from datetime import datetime, timedelta


# from  import Timetable

# def landing_page(request):
#     return render(request, 'timetable/base.html', {})

# make each request an array. Display the array in the filters tool in the frontend.
# when filtering, iterate through courses and filter by current iteration
    # - do this for every filter
    
PIXELS_PER_MINUTE = 1  # Adjust this value to change the height of each minute in pixels

def landing_page(request):
    # data = 
    hour_list = ["08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"]
    term = CourseTerm.objects.all()
    code = CourseCode.objects.all()
    number = CourseNumber.objects.all()
    section = CourseSection.objects.all()
    time = CourseTime.objects.all()
    day = CourseDay.objects.all()
    
    
    courses = None
    
    
    filter_code = request.GET.getlist('code[]')
    print(filter_code)
    filter_number = request.GET.getlist('number[]')
    filter_section = request.GET.getlist('section[]')
    filter_term = request.GET.getlist('term[]')
    filter_start = request.GET.getlist('start[]')
    filter_end = request.GET.getlist('end[]')
    filter_day = request.GET.getlist('day[]')
    

    
    if (filter_code or filter_number or filter_section or filter_term or filter_start or filter_end or filter_day):
        print(filter_code, filter_number, filter_section, filter_term, filter_start, filter_end, filter_day)
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
            # Group courses by day and start time
            overlap_tracker = defaultdict(list)
            for course in courses:
                attached_days = course.day.name.split('_')  # Handle multiple days
                for i, day_ in enumerate(attached_days):
                    key = (day_, course.start.name[:2])  # e.g., ('Mon', '13')
                    overlap_tracker[key].append(course)
                    # Mark overlapping courses        
                    # print(overlap_tracker)
                    for group in overlap_tracker.values():
                        if len(group) > 1:
                            for c in group:
                                c.overlaps = len(group) * (100 / len(courses))
                        else:
                            group[0].overlaps = False
                            
                            
        # for course in courses:
        #     start = datetime.strptime(course.start.name, "%H:%M:%S")
        #     end = datetime.strptime(course.end.name, "%H:%M:%S")
        #     course.intervals = []

        #     current = start
        #     while current < end:
        #         next_time = current + timedelta(minutes=30)
        #         course.intervals.append(f"{current.strftime('%H:%M')} - {next_time.strftime('%H:%M')}")
        #         current = next_time
        for course in courses:
            start = datetime.strptime(course.start.name, "%H:%M:%S")
            end = datetime.strptime(course.end.name, "%H:%M:%S")
            course.duration_minutes = (end - start).seconds // 60
            course.pixel_height = course.duration_minutes * PIXELS_PER_MINUTE
            
            course.offset_top = (start.minute) * PIXELS_PER_MINUTE
            course.offset_left = course.overlaps
                        
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
            
            
            
    return render(request, 'timetable/landing_page.html', {
        'hour_list': hour_list,
        'terms': term,
        'codes': code,
        'numbers': number,
        'sections': section,
        'times': time,
        'days': day,
        'courses': courses,
        
        })
    
    
    # {% if course.overlaps %}overlap{% endif %}