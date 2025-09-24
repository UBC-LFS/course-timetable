from django.shortcuts import render
from django.http import HttpResponse
from .models import CourseTerm, CourseCode, CourseNumber, CourseSection, CourseTime, CourseDay, Course, CourseYear
from collections import defaultdict
from datetime import datetime, timedelta
from django.shortcuts import redirect
from django.utils.text import slugify
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q


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



''' This constant defines how many pixels each minute of course duration will take up in the timetable view.'''
PIXELS_PER_MINUTE = 1

'''This function handles the landing page of the timetable application.'''
def landing_page(request):
    if not request.user.is_authenticated:
        return redirect('accounts:ldap_login')

    # dropdown data (same as before)
    hour_list = ["08","09","10","11","12","13","14","15","16","17","18","19","20","21"]
    terms   = CourseTerm.objects.all()
    codes   = CourseCode.objects.all()
    numbers = CourseNumber.objects.all()
    sections= CourseSection.objects.all()
    times   = CourseTime.objects.all()
    days    = CourseDay.objects.all()

    # stub filters: if any filter submitted, we still show ALL courses
    submitted = any([
        request.GET.getlist('code[]'),
        request.GET.getlist('number[]'),
        request.GET.getlist('section[]'),
        request.GET.getlist('term[]'),
        request.GET.getlist('start[]'),
        request.GET.getlist('end[]'),
        request.GET.getlist('day[]'),
    ])

    # always load everything for now
    all_courses = Course.objects.select_related(
        "code","number","section","term","academic_year","start_time","end_time","day"
    ).all()

    # split into valid (has day + start + end) vs invalid (missing any of them)
    valid_courses = []
    invalid_courses = []
    for c in all_courses:
        if c.day is None or c.start_time is None or c.end_time is None:
            invalid_courses.append(c)
        else:
            valid_courses.append(c)

    courses = valid_courses  # what the timetable will render

    if courses:
        # build time grid
        DAYS = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri']
        START_TIME = '08:00'
        END_TIME   = '19:00'
        INTERVAL   = timedelta(minutes=15)
        start_dt   = datetime.strptime(START_TIME, "%H:%M")
        end_dt     = datetime.strptime(END_TIME, "%H:%M")

        slots = {}
        cur = start_dt
        while cur < end_dt:
            tstr = cur.strftime("%H:%M")
            for d in DAYS:
                slots[(d, tstr)] = []
            cur += INTERVAL

        # place courses into slots
        for course in courses:
            attached_days = course.day.name.split('_')  # same encoding as before
            start_str = course.start_time.name[:5]
            end_str   = course.end_time.name[:5]
            cur = datetime.strptime(start_str, "%H:%M")
            end = datetime.strptime(end_str, "%H:%M")

            for d in attached_days:
                cur_time = cur
                while cur_time < end:
                    t = cur_time.strftime("%H:%M")
                    if (d, t) in slots:
                        slots[(d, t)].append(course)
                    cur_time += INTERVAL

        # compute overlaps
        for slot, group in slots.items():
            if len(group) > 1:
                for c in group:
                    day_key, _ = slot
                    if getattr(c, f"{day_key}_overlap_width", None) is None:
                        w = round((100.0 / float(len(group))) if len(group) else 100.0, 2)
                        setattr(c, f"{day_key}_overlap_width", w)
                        setattr(c, f"{day_key}_offset_left", w * group.index(c))
                        setattr(c, f"{day_key}_overlaps", True)

        # visual props (height, offset, color)
        for c in courses:
            start = datetime.strptime(c.start_time.name[:5], "%H:%M")
            end   = datetime.strptime(c.end_time.name[:5], "%H:%M")
            c.duration_minutes = (end - start).seconds // 60
            c.pixel_height = c.duration_minutes * PIXELS_PER_MINUTE
            c.offset_top = (start.minute) * PIXELS_PER_MINUTE

            # same palette as before
            code = c.code.name
            c.color = (
                "#7BDFF2" if code == "APBI" else
                "#B2F7EF" if code == "FNH"  else
                "#CBAACB" if code == "FOOD" else
                "#F6C6EA" if code == "FRE"  else
                "#EADB9A" if code == "GRS"  else
                "#FFAAA5" if code == "LFS"  else "#D3D3D3"
            )

        # per-day overlap data used by template
        for c in courses:
            c.day_data = {
                "Mon":   {"overlap": getattr(c, 'Mon_overlaps',   None), "width": getattr(c, 'Mon_overlap_width',   None), "left": getattr(c, 'Mon_offset_left',   None)},
                "Tues":  {"overlap": getattr(c, 'Tues_overlaps',  None), "width": getattr(c, 'Tues_overlap_width',  None), "left": getattr(c, 'Tues_offset_left',  None)},
                "Wed":   {"overlap": getattr(c, 'Wed_overlaps',   None), "width": getattr(c, 'Wed_overlap_width',   None), "left": getattr(c, 'Wed_offset_left',   None)},
                "Thurs": {"overlap": getattr(c, 'Thurs_overlaps', None), "width": getattr(c, 'Thurs_overlap_width', None), "left": getattr(c, 'Thurs_offset_left', None)},
                "Fri":   {"overlap": getattr(c, 'Fri_overlaps',   None), "width": getattr(c, 'Fri_overlap_width',   None), "left": getattr(c, 'Fri_offset_left',   None)},
            }

    # render
    return render(request, 'timetable/landing_page.html', {
        'hour_list': hour_list,
        'terms': terms,
        'codes': codes,
        'numbers': numbers,
        'sections': sections,
        'times': times,
        'days': days,
        'courses': courses,
        'invalid_courses': invalid_courses,
        'day_list': ['Mon','Tues','Wed','Thurs','Fri'],
        'submitted': submitted,
    })

def redirect_root(request):
    if request.user.is_authenticated:
        return redirect('scheduler:landing_page')
    return redirect('accounts:ldap_login')




def view_courses(request):
    # Queries
    code_query = request.GET.get("code", "").strip()
    number_query = request.GET.get("number", "").strip()
    section_query = request.GET.get("section", "").strip()
    term_query = request.GET.getlist("term")   # now supports multiple checkbox values
    year_query = request.GET.get("year", "").strip()

    courses = Course.objects.all()

    # Filters
    if code_query:
        courses = courses.filter(code__name__icontains=code_query)
    if number_query:
        courses = courses.filter(number__name__icontains=number_query)
    if section_query:
        courses = courses.filter(section__name__icontains=section_query)
    if term_query:
        courses = courses.filter(term__name__in=term_query)
    if year_query:
        courses = courses.filter(year__name__icontains=year_query)

    # Pagination
    paginator = Paginator(courses, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Build distinct years → extract first 4 chars (2025 from 2025-26)
    all_years = CourseYear.objects.values_list("name", flat=True).distinct()
    dropdown_years = sorted({y[:4] for y in all_years if y})  # set of start years

    querydict = request.GET.copy()
    if "page" in querydict:
        querydict.pop("page")
    querystring = querydict.urlencode()

    return render(request, "timetable/view_courses.html", {
        "courses": page_obj,
        "page_obj": page_obj,
        "terms": ["T1", "T2", "T1_T2"],   # explicit checkboxes
        "years": dropdown_years,          # cleaned years
        "querystring": querystring,
        "code_query": code_query,
        "number_query": number_query,
        "section_query": section_query,
        "term_query": term_query,
        "year_query": year_query,
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
    


def create_course(request):
    if request.method == 'POST':
        data = request.POST

        code = data.get('code')
        print(code)
        number = data.get('number')
        section = data.get('section')
        term = data.get('term')
        start = data.get('start')
        end = data.get('end')
        day = data.get('day')
        print(day)

        course_code_obj, created = CourseCode.objects.get_or_create(name=code)
        course_number_obj, created = CourseNumber.objects.get_or_create(name=number)
        course_section_obj, created = CourseSection.objects.get_or_create(name=section)
        course_term_obj, created = CourseTerm.objects.get_or_create(name=term)
        course_start_obj, created = CourseTime.objects.get_or_create(name=start)
        course_end_obj, created = CourseTime.objects.get_or_create(name=end)
        course_day_obj, created = CourseDay.objects.get_or_create(name=day)


        course_name = f"{code}-{number}-{section}-{term}"
        slug = slugify(course_name)

        if Course.objects.filter(slug=slug).exists():
            messages.error(request, 'A course with this name already exists.')
            return redirect('scheduler:view_courses')

        course = Course(
            name=course_name,
            slug=slug,
            code=course_code_obj,
            number=course_number_obj,
            section=course_section_obj,
            term=course_term_obj,
            start=course_start_obj,
            end=course_end_obj,
            day=course_day_obj
        )
        course.save()

        return redirect('scheduler:view_courses')
