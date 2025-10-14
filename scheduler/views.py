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
from .forms import CourseForm
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from .forms import CourseTermForm
from .forms import CourseCodeForm
from .forms import CourseNumberForm
from .forms import CourseSectionForm
from .forms import CourseTimeForm
from .forms import CourseYearForm
from .models import Program, ProgramYearLevel
from .forms import ProgramNameForm
from django.urls import reverse


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

    # dropdown data
    hour_list = ["08","09","10","11","12","13","14","15","16","17","18","19","20","21"]
    terms   = CourseTerm.objects.all()
    codes   = CourseCode.objects.all()
    numbers = CourseNumber.objects.all()
    sections= CourseSection.objects.all()
    times   = CourseTime.objects.all()
    days    = CourseDay.objects.all()

    # this is for no filtering, change it later!!!
    submitted = (request.GET.get("submitted") == "1")

    courses = []           # timetable courses
    invalid_courses = []   # courses without scheduled times

    if submitted:
        # (for now) ignore actual filters and just load everything
        all_courses = Course.objects.select_related(
            "code","number","section","term","academic_year","start_time","end_time","day"
        ).all()

        # split valid/invalid
        valid_courses = []
        for c in all_courses:
            if c.day is None or c.start_time is None or c.end_time is None:
                invalid_courses.append(c)
            else:
                valid_courses.append(c)

        courses = valid_courses

    if courses:
        # build time grid
        DAYS = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri']
        START_TIME = '08:00'
        END_TIME   = '21:00'
        INTERVAL   = timedelta(minutes=1)
        start_dt   = datetime.strptime(START_TIME, "%H:%M")
        end_dt     = datetime.strptime(END_TIME, "%H:%M")

        slots = {}
        cur = start_dt
        while cur < end_dt:
            tstr = cur.strftime("%H:%M")
            for d in DAYS:
                slots[(d, tstr)] = []
            cur += INTERVAL

        DAY_SHORT = {
                    "Monday": "Mon",
                    "Tuesday": "Tues",
                    "Wednesday": "Wed",
                    "Thursday": "Thurs",
                    "Friday": "Fri",
        }
        def expand_days_to_short(day_name: str):
            """'Monday_Wednesday' -> ['Mon', 'Wed'] (trims whitespace too)"""
            if not day_name:
                return []
            parts = [p.strip() for p in day_name.split("_")]
            return [DAY_SHORT.get(p, p) for p in parts]
        
        # place courses into slots
        for course in courses:
            attached_days = expand_days_to_short(course.day.name) # same encoding as before
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
        # helper to turn "HH:MM" into minutes since midnight
        def _mins(hhmm: str) -> int:
            hh, mm = map(int, hhmm.split(":"))
            return hh * 60 + mm
        
        # Build day -> courses (sorted by start_time then id for stability)
        day_to_courses = {"Mon": [], "Tues": [], "Wed": [], "Thurs": [], "Fri": []}
        for c in courses:
            for d in expand_days_to_short(c.day.name):
                day_to_courses[d].append(c)

        for d in day_to_courses:
            # sort by start minutes first, then by id for a stable "older → newer" order
            day_to_courses[d].sort(key=lambda c: (_mins(c.start_time.name[:5]), c.id))

        # Chain widths: for each day list, walk in order and shrink width 10% each time
        for day_key, day_list in day_to_courses.items():
            # keep a list of active courses that cover the current start time
            # but we only care about predecessors that cover *this* course's start
            for idx, c in enumerate(day_list):
                c_start = _mins(c.start_time.name[:5])
                c_end   = _mins(c.end_time.name[:5])

                # count predecessors whose interval covers c_start
                predecessors = 0
                for prev in day_list[:idx]:
                    p_start = _mins(prev.start_time.name[:5])
                    p_end   = _mins(prev.end_time.name[:5])
                    if p_start <= c_start < p_end:
                        predecessors += 1

                k = predecessors
                width_pct = round(100.0 * (0.9 ** k), 2)
                # left_pct  = 0.0
                overlaps  = (k > 0)

                # stash per-day values the same way your template already expects
                setattr(c, f"{day_key}_overlap_width", width_pct)
                # setattr(c, f"{day_key}_offset_left", left_pct)
                setattr(c, f"{day_key}_overlaps", overlaps)
                # Optional: z-index so a later (smaller) card sits on top
                setattr(c, f"{day_key}_zindex", 100 + k)

        # visual props (height, offset, color)
        for c in courses:
            start = datetime.strptime(c.start_time.name[:5], "%H:%M")
            end   = datetime.strptime(c.end_time.name[:5], "%H:%M")
            c.duration_minutes = (end - start).seconds // 60
            c.pixel_height = c.duration_minutes * PIXELS_PER_MINUTE
            c.offset_top = (start.minute) * PIXELS_PER_MINUTE

            code = c.code.name if c.code else "None"
            c.color = (
                "#2BB1D6" if code == "APBI" else
                "#43D7C7" if code == "FNH"  else
                "#E47CC0" if code == "FRE"  else
                "#D2B64C" if code == "GRS"  else
                "#F46C63" if code == "LFS"  else "#A8A8A8"
            )

        # per-day overlap data used by template
        for c in courses:
            c.day_data = {
                "Mon":   {"overlap": getattr(c, 'Mon_overlaps',   None), "width": getattr(c, 'Mon_overlap_width',   None), "left": getattr(c, 'Mon_offset_left',   None), "z": getattr(c, 'Mon_zindex',   None)},
                "Tues":  {"overlap": getattr(c, 'Tues_overlaps',  None), "width": getattr(c, 'Tues_overlap_width',  None), "left": getattr(c, 'Tues_offset_left',  None), "z": getattr(c, 'Tues_zindex',  None)},
                "Wed":   {"overlap": getattr(c, 'Wed_overlaps',   None), "width": getattr(c, 'Wed_overlap_width',   None), "left": getattr(c, 'Wed_offset_left',   None), "z": getattr(c, 'Wed_zindex',   None)},
                "Thurs": {"overlap": getattr(c, 'Thurs_overlaps', None), "width": getattr(c, 'Thurs_overlap_width', None), "left": getattr(c, 'Thurs_offset_left', None), "z": getattr(c, 'Thurs_zindex', None)},
                "Fri":   {"overlap": getattr(c, 'Fri_overlaps',   None), "width": getattr(c, 'Fri_overlap_width',   None), "left": getattr(c, 'Fri_offset_left',   None), "z": getattr(c, 'Fri_zindex',   None)},
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



# helpers to make option lists
def _hhmm_range(start_hour, end_hour_inclusive, step_minutes=30):
    out = []
    h, m = start_hour, 0
    end_h, end_m = end_hour_inclusive, 0
    while True:
        out.append(f"{h:02d}:{m:02d}")
        if (h, m) == (end_h, end_m):
            break
        m += step_minutes
        if m >= 60:
            h += 1
            m = 0
    return out

TERM_CHOICES = ["T1", "T2", "T1_T2"]
DAY_CHOICES = [("Monday", "Monday"), ("Tuesday", "Tuesday"), ("Wednesday", "Wednesday"),
               ("Thursday", "Thursday"), ("Friday", "Friday")]
START_TIME_CHOICES = _hhmm_range(8, 21)   # 08:00 → 21:00, every 30m
END_TIME_CHOICES   = _hhmm_range(8, 21)   # 08:00 → 21:00, every 30m
YEAR_CHOICES       = [str(y) for y in range(2025, 2036)]

def create_course(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course created successfully.")
            return redirect("scheduler:view_courses")
        messages.error(request, "Please correct the errors below.")
    else:
        form = CourseForm()

    return render(request, "timetable/course_form.html", {
        "title": "Create Course",
        "form": form,
    })


def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated successfully.")
            return redirect("scheduler:view_courses")
        messages.error(request, "Please correct the errors below.")
    else:
        form = CourseForm(instance=course)

    return render(request, "timetable/course_form.html", {
        "title": "Edit Course",
        "form": form,
    })

def course_term_list(request):
    terms = CourseTerm.objects.order_by("id")
    form = CourseTermForm()  # empty for the Create modal
    return render(request, "timetable/course_term_list.html", {"terms": terms, "form": form})

@require_POST
def course_term_create(request):
    form = CourseTermForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Term created.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_term")

@require_POST
def course_term_update(request, pk):
    term = get_object_or_404(CourseTerm, pk=pk)
    form = CourseTermForm(request.POST, instance=term)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Term updated.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_term")

@require_POST
def course_term_delete(request, pk):
    term = get_object_or_404(CourseTerm, pk=pk)
    term.delete()
    messages.success(request, "Course Term deleted.")
    return redirect("scheduler:course_term")

def course_code_list(request):
    codes = CourseCode.objects.order_by("id")
    form = CourseCodeForm()
    return render(request, "timetable/course_code_list.html", {"codes": codes, "form": form})

@require_POST
def course_code_create(request):
    form = CourseCodeForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Code created.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_code")

@require_POST
def course_code_update(request, pk):
    code = get_object_or_404(CourseCode, pk=pk)
    form = CourseCodeForm(request.POST, instance=code)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Code updated.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_code")

@require_POST
def course_code_delete(request, pk):
    code = get_object_or_404(CourseCode, pk=pk)
    code.delete()
    messages.success(request, "Course Code deleted.")
    return redirect("scheduler:course_code")

def course_number_list(request):
    numbers = CourseNumber.objects.order_by("id")
    form = CourseNumberForm()
    return render(request, "timetable/course_number_list.html", {"numbers": numbers, "form": form})

@require_POST
def course_number_create(request):
    form = CourseNumberForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Number created.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_number")

@require_POST
def course_number_update(request, pk):
    number = get_object_or_404(CourseNumber, pk=pk)
    form = CourseNumberForm(request.POST, instance=number)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Number updated.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_number")

@require_POST
def course_number_delete(request, pk):
    number = get_object_or_404(CourseNumber, pk=pk)
    number.delete()
    messages.success(request, "Course Number deleted.")
    return redirect("scheduler:course_number")

def course_section_list(request):
    sections = CourseSection.objects.order_by("id")
    form = CourseSectionForm()
    return render(request, "timetable/course_section_list.html", {"sections": sections, "form": form})

@require_POST
def course_section_create(request):
    form = CourseSectionForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Section created.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_section")

@require_POST
def course_section_update(request, pk):
    section = get_object_or_404(CourseSection, pk=pk)
    form = CourseSectionForm(request.POST, instance=section)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Section updated.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_section")

@require_POST
def course_section_delete(request, pk):
    section = get_object_or_404(CourseSection, pk=pk)
    section.delete()
    messages.success(request, "Course Section deleted.")
    return redirect("scheduler:course_section")

def course_time_list(request):
    times = CourseTime.objects.order_by("id")
    form = CourseTimeForm()
    hours   = [f"{i:02d}" for i in range(24)]
    minutes = [f"{i:02d}" for i in range(60)]
    return render(
        request,
        "timetable/course_time_list.html",
        {"times": times, "form": form, "hours": hours, "minutes": minutes},
    )

@require_POST
def course_time_create(request):
    form = CourseTimeForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Time created.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_time")

@require_POST
def course_time_update(request, pk):
    t = get_object_or_404(CourseTime, pk=pk)
    form = CourseTimeForm(request.POST, instance=t)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Time updated.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_time")

@require_POST
def course_time_delete(request, pk):
    t = get_object_or_404(CourseTime, pk=pk)
    t.delete()
    messages.success(request, "Course Time deleted.")
    return redirect("scheduler:course_time")

def course_year_list(request):
    years = CourseYear.objects.order_by("name")
    form = CourseYearForm()
    # pass choices to template for the Edit modal's select
    year_choices = [str(y) for y in range(2024, 2043)]
    return render(request, "timetable/course_year_list.html",
                  {"years": years, "form": form, "year_choices": year_choices})

@require_POST
def course_year_create(request):
    form = CourseYearForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Year created.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_year")

@require_POST
def course_year_update(request, pk):
    y = get_object_or_404(CourseYear, pk=pk)
    form = CourseYearForm(request.POST, instance=y)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Year updated.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_year")

@require_POST
def course_year_delete(request, pk):
    y = get_object_or_404(CourseYear, pk=pk)
    y.delete()
    messages.success(request, "Course Year deleted.")
    return redirect("scheduler:course_year")

def program_name_list(request):
    # Distinct names only
    names = (Program.objects
             .exclude(name__isnull=True)
             .exclude(name__exact="")
             .values_list("name", flat=True)
             .distinct()
             .order_by("name"))
    form = ProgramNameForm()
    return render(request, "timetable/program_name_list.html", {"names": names, "form": form})

@require_POST
def program_name_create(request):
    form = ProgramNameForm(request.POST)
    if form.is_valid():
        new_name = form.cleaned_data["name"]
        # create a seed Program row so the name exists
        Program.objects.create(name=new_name, year_level=None)
        messages.success(request, "Program Name created.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:program_name")

@require_POST
def program_name_update(request, old_name):
    form = ProgramNameForm(request.POST, current_name=old_name)
    if form.is_valid():
        new_name = form.cleaned_data["name"]
        # cascade rename across all year levels
        Program.objects.filter(name__exact=old_name).update(name=new_name)
        messages.success(request, "Program Name updated.")
    else:
        err = "; ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:program_name")

@require_POST
def program_name_delete(request, name):
    # delete all rows in Prgram table with this name (all year levels)
    Program.objects.filter(name__exact=name).delete()
    messages.success(request, "Program Name deleted.")
    return redirect("scheduler:program_name")

def requirements(request):
    """
    Renders the Requirements page with two required filters:
    - Program Name (distinct Program.name values)
    - Program Year Level (all ProgramYearLevel rows)

    After both are chosen and Search is clicked, we show the table of courses
    linked to that (Program.name, ProgramYearLevel) combination, or “No such program exists.”
    """
    # dynamic dropdown data
    program_names = (Program.objects
                     .exclude(name__isnull=True)
                     .exclude(name__exact="")
                     .values_list("name", flat=True)
                     .distinct()
                     .order_by("name"))

    year_levels = ProgramYearLevel.objects.order_by("name")

    # read selection (GET)
    selected_program = request.GET.get("program", "").strip()
    selected_level_id = request.GET.get("level", "").strip()
    level = None
    submitted = "search" in request.GET  # Search button pressed

    courses = None
    program_obj = None
    not_found = False

    if submitted:
        if not selected_program or not selected_level_id:
            messages.error(request, "You have to select both Program Name and Program Year Level.")
        else:
            # level by id from dropdown
            level = get_object_or_404(ProgramYearLevel, id=selected_level_id)
            # exact (name, level) program
            program_obj = Program.objects.filter(name=selected_program, year_level=level).first()
            if program_obj:
                courses = (program_obj.courses
                           .select_related("code", "number", "section", "academic_year", "term")
                           .order_by("code__name", "number__name", "section__name",
                                     "academic_year__name", "term__name"))
            else:
                not_found = True
                courses = []

    return render(request, "timetable/requirements.html", {
        "program_names": program_names,
        "year_levels": year_levels,
        "selected_program": selected_program,
        "selected_level_id": selected_level_id,
        "selected_level": level,
        "submitted": submitted,
        "program_obj": program_obj,
        "courses": courses,
        "not_found": not_found,
    })

def requirements_edit(request):
    """
    Edit mapping of courses for a given (Program.name, ProgramYearLevel).
    GET  -> show all courses with checkboxes (checked if already mapped)
    POST -> save the selected set (program.courses = selected)
    """
    # read identity (passed via query string or hidden inputs)
    program_name = request.GET.get("program") or request.POST.get("program")
    level_id = request.GET.get("level") or request.POST.get("level")

    if not program_name or not level_id:
        messages.error(request, "Missing program identity.")
        return redirect("scheduler:requirements")

    level = get_object_or_404(ProgramYearLevel, id=level_id)
    program, _ = Program.objects.get_or_create(name=program_name, year_level=level)

    if request.method == "POST":
        # IDs of courses checked
        selected_ids = request.POST.getlist("course_ids")
        program.courses.set(Course.objects.filter(id__in=selected_ids))
        messages.success(request, "Program requirements saved.")
        # back to search page with same filters
        url = f"{reverse('scheduler:requirements')}?program={program_name}&level={level.id}&search=1"
        return redirect(url)

    all_courses = (Course.objects
                   .select_related("code", "number", "section", "academic_year", "term")
                   .order_by("code__name", "number__name", "section__name",
                             "academic_year__name", "term__name"))
    current_ids = set(program.courses.values_list("id", flat=True))

    return render(request, "timetable/requirements_edit.html", {
        "program": program,
        "level": level,
        "all_courses": all_courses,
        "current_ids": current_ids,
    })