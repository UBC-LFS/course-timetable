from django.shortcuts import render
from django.http import HttpResponse
from .models import CourseTerm, CourseCode, CourseNumber, CourseSection, CourseTime, CourseDay, Course
from collections import defaultdict
from datetime import datetime, timedelta
from django.shortcuts import redirect
from django.utils.text import slugify
from django.contrib import messages


'''
TODO READ BEFORE CONTINUING:
VIEWS WORK FLOW:
1. Grab all variables from fixtures/database
2. Grab all filters inputted by user from Landing Page
3. Filter the courses based on the filters
4. Create a slots dictionary with all time slots for each day split up into 15 minute intervals
    - This will represent the time slots in the timetable to find conflicting courses/overlaps
5. Iterate through all courses to find their start/end time and add courses to their corresponding time slots in the slots dictionary
6. If a slot has > 1 course in it, calculate the overlap width, offset left for each course in that slot
7. Create a dictionary (day_data) for each course that has its overlap info for each day
8. Render the landing page with the courses and their overlap data
'''


# def redirect_root(request):
#     if request.user.is_authenticated:
#         return redirect('scheduler:landing_pade')
#     return redirect('accounts:ldap_login')

''' This constant defines how many pixels each minute of course duration will take up in the timetable view.'''
PIXELS_PER_MINUTE = 1

'''This function handles the landing page of the timetable application.'''
def landing_page(request):
    
    submitted = False

    # print(f"heyy {request.user.is_authenticated}")

    if not request.user.is_authenticated:
       return redirect('accounts:ldap_login')
    
    '''Variables from the fixtures/database'''
    hour_list = ["08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"]
    term = CourseTerm.objects.all()
    code = CourseCode.objects.all()
    number = CourseNumber.objects.all()
    section = CourseSection.objects.all()
    time = CourseTime.objects.all()
    day = CourseDay.objects.all()

    '''Instantiate the variable that will hold the courses after filtering'''
    courses = None

    '''Get the filter values from the landing page request'''
    filter_code = request.GET.getlist('code[]')
    filter_number = request.GET.getlist('number[]')
    filter_section = request.GET.getlist('section[]')
    filter_term = request.GET.getlist('term[]')
    filter_start = request.GET.getlist('start[]')
    filter_end = request.GET.getlist('end[]')
    filter_day = request.GET.getlist('day[]')

    print(filter_code, filter_number, filter_section, filter_term, filter_start, filter_end, filter_day)

    '''Filters the fixture data and widdles down to just the filtered output'''
    if (filter_code or filter_number or filter_section or filter_term or filter_start or filter_end or filter_day):
        courses = Course.objects.all()
        submitted = True
    
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
        
        print(len(courses))
        '''If there are courses after filtering, proceed to create the timetable slots and calculate overlaps'''
        if courses.exists():
            
            '''Outline for the timetable slots and overlaps'''
            DAYS = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri']
            START_TIME = '08:00'
            END_TIME = '19:00'
            INTERVAL = timedelta(minutes=15)
            start = datetime.strptime(START_TIME, "%H:%M")
            end = datetime.strptime(END_TIME, "%H:%M")

            '''Create a slots dictionary to hold all time slots for each day in 15 minute intervals.'''
            '''The keys will be tuples of (day, time) and the values will be lists'''
            slots = {}
            current_time = start
            while current_time < end:
                time_str = current_time.strftime("%H:%M")
                for day in DAYS:
                    slots[(day, time_str)] = []
                current_time += INTERVAL
            
            
            '''Iterate through the courses and add them to the corresponding time slots in the slots dictionary.'''
            for course in courses:
                attached_days = course.day.name.split('_')
                for day in attached_days:
                    start_time = course.start.name[:5]  # e.g., '13:00'
                    end_time = course.end.name[:5]  # e.g., '15:00'
                    current_time = datetime.strptime(start_time, "%H:%M") # strip times into datetime
                    end_time_dt = datetime.strptime(end_time, "%H:%M")  # strip times into datetime
                    
                    '''Iterate from start time to end time in 15 minute intervals and add the course to the corresponding slot'''
                    while current_time < end_time_dt:
                        time_str = current_time.strftime("%H:%M")
                        
                        if (day, time_str) in slots:
                            slots[(day, time_str)].append(course)
                        current_time += INTERVAL
                        
            '''
            Increment the start time by 15 minutes until you hit the end time - 15 minutes
            as you increment, add to corresponding key in the dictionary. Minus 15 minutes because each key represents a 15 minute interval.
            It will look like this:
            
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
            
            
            '''Iterate through the slots dictionary to calculate overlaps and add attributes to each course'''
            for slot, course_group in slots.items():
                '''If there is > 1 course in a slot, then continue to calculate overlaps'''
                if len(course_group) > 1:
                    for c in course_group:
                        slot_day, slot_time = slot

                        ''' Check if the course already has attributes for this day, if not, create them '''
                        if getattr(c, f"{slot_day}_overlap_width", None) is None:
                            overlap_width = 1.0 / float(len(course_group)) if len(course_group) > 0 else 1.0
                            overlap_width *= 100
                            overlap_width = round(overlap_width, 2)
                            
                            '''
                            course has attributes of each day dynamically added:
                            - overlap_width
                            - offset_left
                            - overlaps
                            '''
                            
                            setattr(c, f"{slot_day}_overlap_width", overlap_width)
                            setattr(c, f"{slot_day}_offset_left", overlap_width * course_group.index(c))
                            setattr(c, f"{slot_day}_overlaps", True) # For styling purposes
                            
        ''' For each course, assign a color and pixel height based off its duration'''
        for course in courses:
            for t_format in ("%H:%M:%S", "%H:%M"):
                try:
                    start = datetime.strptime(course.start.name, t_format)
                    start = start.strftime("%H:%M")
                    start = datetime.strptime(start, "%H:%M")
                except:
                    continue
            
            for t_format in ("%H:%M:%S", "%H:%M"):
                try:
                    end = datetime.strptime(course.end.name, t_format)
                    end = end.strftime("%H:%M")
                    end = datetime.strptime(end, "%H:%M")
                except:
                    continue
                
            course.duration_minutes = (end - start).seconds // 60
            course.pixel_height = course.duration_minutes * PIXELS_PER_MINUTE
            
            course.offset_top = (start.minute) * PIXELS_PER_MINUTE
                        
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
        
        ''' For each course, create a day_data dictionary that holds the overlap info for each day '''
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
     
     
    ''' Used to render the days in the timetable landing page '''
    day_list = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri']
    
    ''' Returns the variables created in this view and makes them accessible in the template through their key names '''
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
        'submitted': submitted
        })

def redirect_root(request):
    if request.user.is_authenticated:
        return redirect('scheduler:landing_page')
    return redirect('accounts:ldap_login')

def view_courses(request):
    
    courses = Course.objects.all()
    terms = CourseTerm.objects.all()
    times = CourseTime.objects.all()
    days = CourseDay.objects.all()

    return render(request, 'timetable/view_courses.html', {
        'courses': courses,
        'terms': terms,
        'times': times,
        'days': days
    })


def edit_course(request, course_id):
    if request.method == 'POST':
        course = Course.objects.get(id=course_id)
        
        data = request.POST

        code = data.get('code', course.code)
        number = data.get('number', course.number)
        section = data.get('section', course.section)
        term = data.get('term', course.term)
        start = data.get('start', course.start)
        end = data.get('end', course.end)
        day = data.get('day', course.day)


        if datetime.strptime(end, "%H:%M") < datetime.strptime(start, "%H:%M"):
            messages.error(request, 'End time must be after start time.')
            return redirect('scheduler:view_courses')

        course_code_obj, created = CourseCode.objects.get_or_create(name=code)
        course_number_obj, created = CourseNumber.objects.get_or_create(name=number)
        course_section_obj, created = CourseSection.objects.get_or_create(name=section)
        course_term_obj, created = CourseTerm.objects.get_or_create(name=term)
        course_start_obj, created = CourseTime.objects.get_or_create(name=start)
        course_end_obj, created = CourseTime.objects.get_or_create(name=end)
        course_day_obj, created = CourseDay.objects.get_or_create(name=day)

        course.code = course_code_obj
        course.number = course_number_obj
        course.section = course_section_obj
        course.term = course_term_obj
        course.start = course_start_obj
        course.end = course_end_obj
        course.day = course_day_obj

        course_name = f"{code}-{number}-{section}-{term}"
        slug = slugify(course_name)

        if Course.objects.filter(slug=slug).exists():
            messages.error(request, 'A course with this name already exists.')
            return redirect('scheduler:view_courses')
    
        course.save()

        return redirect('scheduler:view_courses')

