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
        END_TIME   = '20:00'
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
            code = c.code.name if c.code else "None"
            c.color = (
                "#7BDFF2" if code == "APBI" else
                "#B2F7EF" if code == "FNH"  else
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
    ctx = {
        "title": "Create Course",
        "term_options": TERM_CHOICES,
        "day_options": DAY_CHOICES,
        "start_time_options": START_TIME_CHOICES,
        "end_time_options": END_TIME_CHOICES,
        "year_options": YEAR_CHOICES,
        "selected_days": [],
    }

    if request.method == "POST":
        data = request.POST.copy()
        checked_days = data.getlist("day")
        data["day"] = "_".join(checked_days) if checked_days else ""
        form = CourseForm(data)
        if form.is_valid():
            form.save()
            messages.success(request, "Course created successfully.")
            return redirect("scheduler:view_courses")
        messages.error(request, "Please correct the errors below.")
        ctx["selected_days"] = checked_days
    else:
        form = CourseForm()

    ctx["form"] = form
    return render(request, "timetable/course_form.html", ctx)


def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    checked = course.day.name.split("_") if course.day else []

    ctx = {
        "title": "Edit Course",
        "term_options": TERM_CHOICES,
        "day_options": DAY_CHOICES,
        "start_time_options": START_TIME_CHOICES,
        "end_time_options": END_TIME_CHOICES,
        "year_options": YEAR_CHOICES,
        "selected_days": checked,
    }

    if request.method == "POST":
        data = request.POST.copy()
        checked_days = data.getlist("day")
        data["day"] = "_".join(checked_days) if checked_days else ""
        form = CourseForm(data)
        if form.is_valid():
            form.save(instance=course)
            messages.success(request, "Course updated successfully.")
            return redirect("scheduler:view_courses")
        messages.error(request, "Please correct the errors below.")
        ctx["selected_days"] = checked_days
    else:
        form = CourseForm(initial={
            "code": course.code.name,
            "number": course.number.name,
            "section": course.section.name,
            "term": course.term.name,
            "academic_year": course.academic_year.name,
            "start_time": course.start_time.name if course.start_time else "",
            "end_time": course.end_time.name if course.end_time else "",
            "day": course.day.name if course.day else "",
        })

    ctx["form"] = form
    return render(request, "timetable/course_form.html", ctx)

def course_term_list(request):
    terms = CourseTerm.objects.order_by("name")
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
    codes = CourseCode.objects.order_by("name")
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
    numbers = CourseNumber.objects.order_by("name")
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
    sections = CourseSection.objects.order_by("name")
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
    times = CourseTime.objects.order_by("name")
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