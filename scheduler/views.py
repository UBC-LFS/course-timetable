from django.shortcuts import render
from .models import CourseTerm, CourseCode, CourseNumber, CourseSection, CourseTime, CourseDay, Course, CourseYear, MajorName
from datetime import datetime, timedelta
from django.shortcuts import redirect
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
from .models import Major, MajorYearLevel
from .forms import MajorNameForm
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Min
from django.views.decorators.http import require_GET
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from .models import HistoryLog, HistoryTopic, HistoryAction
from django.utils import timezone
from zoneinfo import ZoneInfo
import openpyxl
import os
import tempfile
import random


'''
TODO READ BEFORE CONTINUING:
VIEWS WORK FLOW:
1. Grab all variables from database
2. Grab all filters inputted by user from Landing Page
3. Filter the courses based on the filters
4. Create a slots dictionary with all time slots for each day split up into 1 minute intervals
    - This will represent the time slots in the timetable to find conflicting courses/overlaps
5. Iterate through all courses to find their start/end time and add courses to their corresponding time slots in the slots dictionary
6. If a slot has > 1 course in it, calculate the overlap width, offset left for each course in that slot
7. Create a dictionary (day_data) for each course that has its overlap info for each day
8. Render the landing page with the courses and their overlap data
'''



''' This constant defines how many pixels each minute of course duration will take up in the timetable view.'''
PIXELS_PER_MINUTE = 1

# helper: sort the array in the order of "Mon, Tues, Wed, Thurs, Fri"
def expand_days(course):
    parts = [d.name for d in course.day.all()]
    order = ["Mon", "Tues", "Wed", "Thurs", "Fri"]
    return sorted(parts, key=lambda d: order.index(d))

# --- AJAX: terms available for a given academic year ---
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_GET
def ajax_terms_for_year(request):
    year = request.GET.get("year", "").strip()  # e.g., "2025"

    terms = (
        Course.objects
        .filter(academic_year__name=year)
        .exclude(term__name__isnull=True)
        .values_list("term__name", flat=True)
        .distinct()
        .order_by("term__name")
    )
    return JsonResponse({"terms": list(terms)})

'''This function handles the landing page of the timetable application.'''
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def landing_page(request):

    hour_list = ["08","09","10","11","12","13","14","15","16","17","18","19","20","21"]
    terms   = CourseTerm.objects.all()
    codes   = CourseCode.objects.all()
    numbers = CourseNumber.objects.all()
    sections= CourseSection.objects.all()
    times   = CourseTime.objects.all()
    days    = CourseDay.objects.all()

    # Academic Year
    all_years = CourseYear.objects.values_list("name", flat=True)
    dropdown_years = sorted({y for y in all_years})

    # For the Name dropdown (once terms are chosen)
    major_names = MajorName.objects.order_by("name")

    selected_year  = request.GET.get("year", "").strip()
    selected_terms = request.GET.getlist("term") # multi-select
    selected_pname = request.GET.get("pname", "").strip()
    selected_plevel = request.GET.get("plevel", "").strip()
    course_filters_json = request.GET.get("course_filters_json", "").strip()
    course_filters = []
    if course_filters_json:
        try:
            data = json.loads(course_filters_json)
            # keep only sane items: {"code": str, "numbers": [str, ...]}
            for item in (data if isinstance(data, list) else []):
                code = (item.get("code") or "").strip()
                nums = [str(x).strip() for x in (item.get("numbers") or []) if str(x).strip()]
                if code or nums:
                    course_filters.append({"code": code, "numbers": nums})
        except Exception:
            course_filters = []

    submitted      = ("search" in request.GET)

    # preload term options for the selected year, this make UI more beautiful than client fetch available_terms_for_year
    available_terms_for_year = []
    if selected_year:
        available_terms_for_year = list(
            Course.objects
            .filter(academic_year__name=selected_year)
            .exclude(term__name__isnull=True)
            .values_list("term__name", flat=True)
            .distinct()
            .order_by("term__name")
        )

    # Build a preload dict for numbers of any codes that were selected, this make UI more beautiful
    selected_codes = sorted({f["code"] for f in course_filters if f.get("code")})
    numbers_by_code = {}
    if selected_codes:
        rows = (Course.objects
                .filter(code__name__in=selected_codes)
                .exclude(number__name__isnull=True)
                .values_list('code__name', 'number__name')
                .distinct())
        for code, num in rows:
            numbers_by_code.setdefault(code, []).append(num)
        for code in numbers_by_code:
            numbers_by_code[code].sort()
    numbers_by_code_json = json.dumps(numbers_by_code)

    # preload year levels options for the selected name, this make UI more beautiful than client fetch available_levels_for_name
    available_levels_for_name = []
    if selected_pname:
        available_levels_for_name = list(
            Major.objects
            .filter(name__name=selected_pname)
            .values_list("year_level__name", flat=True)
            .distinct()
            .order_by("year_level__name")
        )

    # Output collections
    courses = []          # timetable "occurrences"
    invalid_courses = []  # Course rows missing day/time/5 things on slug
    all_courses = []      # all_courses = courses + invalid_courses

    if submitted:
        if not selected_year or not selected_terms:
            messages.error(request, "You have to select both Academic Year and Term.")
        else:
            # NOTE: with M2M you must prefetch 'day'
            # base queryset
            base_qs = (
                Course.objects
                .select_related("code", "number", "section", "term", "academic_year", "start_time", "end_time")
                .prefetch_related("day")
                .filter(academic_year__name=selected_year,
                        term__name__in=selected_terms)
                .order_by("code__name", "number__name", "section__name", "academic_year__name", "term__name")
            )

            # BY Course
            # Numbers can now be either:
            #   - concrete course numbers, e.g. "101", "210"
            #   - synthetic "level" tokens: "L1" → 100 level (course number starts with 1), "L2" → 200 level, etc.
            if course_filters:
                or_q = Q()
                for f in course_filters:
                    code = f.get("code", "")
                    nums = f.get("numbers", [])
                    if not code and not nums:
                        continue
                    if code and nums:
                        exact_nums = []
                        level_digits = []

                        for raw in nums:
                            s = str(raw)
                            if s.startswith("L") and len(s) == 2 and s[1].isdigit():
                                level_digits.append(s[1])   # "L1" → "1"
                            else:
                                exact_nums.append(s)
                        
                        or_q |= Q(code__name=code,
                                    number__name__in=exact_nums)
                        for d in level_digits:
                            or_q |= Q(code__name=code,
                                    number__name__startswith=d)
                    elif code:
                        or_q |= Q(code__name=code)
                if or_q:
                    base_qs = base_qs.filter(or_q)

            # By Major
            if selected_pname and not selected_plevel:
                base_qs = base_qs.filter(majors__name__name=selected_pname)
            elif selected_pname and selected_plevel:
                base_qs = base_qs.filter(majors__name__name=selected_pname,
                                          majors__year_level__name=selected_plevel)
            all_courses = base_qs

        # A course is valid only if it has at least one day AND both times AND 5 things
        courses = []
        for c in all_courses:
            has_times = (c.start_time is not None and c.end_time is not None)
            has_days  = c.day.exists()
            has_5_things_on_slug = (c.code is not None and c.number is not None and c.section is not None and c.academic_year is not None and c.term is not None)
            if has_times and has_days and has_5_things_on_slug:
                courses.append(c)
            else:
                invalid_courses.append(c)
    
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
        
        # place courses into slots
        for course in courses:
            attached_days = expand_days(course)
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
        # helper: turn "HH:MM" into minutes since midnight
        def _mins(hhmm: str) -> int:
            hh, mm = map(int, hhmm.split(":"))
            return hh * 60 + mm
        
        # Build day -> courses (sorted by start_time then id for stability)
        day_to_courses = {"Mon": [], "Tues": [], "Wed": [], "Thurs": [], "Fri": []}
        for c in courses:
            for d in expand_days(c):
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
                overlaps  = (k > 0)

                # stash per-day values the same way your template already expects
                setattr(c, f"{day_key}_overlap_width", width_pct)
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
            c.day_names = expand_days(c)

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
        'dropdown_years': dropdown_years,
        'selected_year': selected_year,
        'selected_terms': selected_terms,
        'major_names': major_names,
        'selected_pname': selected_pname,
        'selected_plevel': selected_plevel,
        'available_levels_for_name': available_levels_for_name,
        'available_terms_for_year': available_terms_for_year,
        'course_filters_json': course_filters_json,
        'numbers_by_code_json': numbers_by_code_json,
    })

def redirect_root(request):
    if request.user.is_authenticated:
        return redirect('scheduler:landing_page')
    return redirect('accounts:ldap_login')

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def view_courses(request):
    submitted = "search" in request.GET

    # Queries
    code_query = request.GET.get("code", "").strip()
    number_query = request.GET.get("number", "").strip()
    section_query = request.GET.get("section", "").strip()
    term_query = request.GET.getlist("term", "")
    year_query = request.GET.getlist("year", "")
    day_query  = request.GET.getlist("day", "")
    courses = Course.objects.none()
    page_obj = None
    
    if submitted:

        if not year_query:
            messages.error(request, "You have to select Academic Year.")
        else:
            courses = (Course.objects.all()
            .prefetch_related("day")
            .order_by("code__name", "number__name", "section__name", "academic_year__name", "term__name"))

            # Filters
            if year_query:
                courses = courses.filter(academic_year__name__in=year_query)
            if code_query:
                courses = courses.filter(code__name__exact=code_query)
            if number_query:
                courses = courses.filter(number__name__exact=number_query)
            if section_query:
                courses = courses.filter(section__name__exact=section_query)
            if term_query:
                courses = courses.filter(term__name__in=term_query)
            if day_query:
                # Any selected day matches
                # distinct avoids dup rows from the M2M join
                courses = courses.filter(day__name__in=day_query).distinct()

            # Pagination
            paginator = Paginator(courses, 20)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)

            for c in page_obj.object_list:
                c.day_names = expand_days(c)

    # Build terms
    all_terms = CourseTerm.objects.values_list("name", flat=True).distinct()
    dropdown_terms = sorted({t for t in all_terms})

    # Build years
    all_years = CourseYear.objects.values_list("name", flat=True).distinct()
    dropdown_years = sorted({y for y in all_years})

    # Build days
    all_days = CourseDay.objects.values_list("name", flat=True).distinct()
    order = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    dropdown_days = sorted(all_days, key=lambda d: order.index(d))

    querydict = request.GET.copy()
    if "page" in querydict:
        querydict.pop("page")
    querystring = querydict.urlencode()

    return render(request, "timetable/view_courses.html", {
        "courses": page_obj,
        "page_obj": page_obj,
        "terms": dropdown_terms,
        "years": dropdown_years,
        "days": dropdown_days,
        "querystring": querystring,
        "code_query": code_query,
        "number_query": number_query,
        "section_query": section_query,
        "term_query": term_query,
        "year_query": year_query,
        "day_query": day_query,
        "submitted": submitted,
    })

# helper: append error based on error types
def _summarize_form_errors(form):
    parts = []
    # field-specific
    for field, errors in form.errors.items():
        if field == "__all__":
            continue
        for e in errors:
            parts.append(e)
    # non-field
    for e in form.non_field_errors():
        parts.append(e)
    return " ".join(parts)

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def create_course(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course created.")
            return redirect("scheduler:view_courses")
        summary = _summarize_form_errors(form) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {summary}")
    else:
        form = CourseForm()

    return render(request, "timetable/course_form.html", {
        "title": "Create Course",
        "form": form,
    })

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course edited.")
            return redirect("scheduler:view_courses")
        summary = _summarize_form_errors(form) or "Please fix the errors and try again."
        messages.error(request, f"Edit failed: {summary}")
    else:
        form = CourseForm(instance=course)

    return render(request, "timetable/course_form.html", {
        "title": "Edit Course",
        "form": form,
    })

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    def safe_name(obj):
        return getattr(obj, "name", None)
    
    def get_days(days):
        if not days:
            return "None"
        order = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        return ",".join(sorted(days, key=lambda d: order.index(d)))

    details = {
        "code":          safe_name(course.code),
        "number":        safe_name(course.number),
        "section":       safe_name(course.section),
        "term":          safe_name(course.term),
        "day":           get_days([d.name for d in course.day.all()]),
        "start_time":    safe_name(course.start_time),
        "end_time":      safe_name(course.end_time),
        "academic_year": safe_name(course.academic_year),
    }

    if request.method == "POST":
        course.delete()
        messages.success(request, "Course deleted.")
        return redirect("scheduler:view_courses")

    return render(request, "timetable/course_delete_confirm.html", {
        "course": course,
        "details": details,
    })

def _log_history(topic, user, action, before_value="", after_value=""):
    HistoryLog.objects.create(
        topic=topic,
        user=user,
        action=action,
        before_value=before_value,
        after_value=after_value,
    )

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def history(request):
    """
    - For now, only Course Term is implemented.
    """
    # static options (value, label)
    options = [
        ("course_term",   "Course Term"),
        ("course_code",   "Course Code"),
        ("course_number", "Course Number"),
        ("course_section","Course Section"),
        ("course_time",   "Course Time"),
        ("course_year",   "Course Year"),
        ("major_name",  "Major Name"),
    ]

    selected = None
    logs = None  # None = haven't searched; [] = searched but nothing found

    if request.method == "POST":
        selected = request.POST.get("name", "").strip()

        if not selected:
            messages.error(request, "You have to select Name.")
        else:
            if selected == "course_term":
                logs = (
                    HistoryLog.objects
                    .filter(topic=HistoryTopic.COURSE_TERM)
                    .select_related("user")
                )
            if selected == "course_code":
                logs = (
                    HistoryLog.objects
                    .filter(topic=HistoryTopic.COURSE_CODE)
                    .select_related("user")
                )
            if selected == "course_number":
                logs = (
                    HistoryLog.objects
                    .filter(topic=HistoryTopic.COURSE_NUMBER)
                    .select_related("user")
                )
            if selected == "course_section":
                logs = (
                    HistoryLog.objects
                    .filter(topic=HistoryTopic.COURSE_SECTION)
                    .select_related("user")
                )
            if selected == "course_time":
                logs = (
                    HistoryLog.objects
                    .filter(topic=HistoryTopic.COURSE_TIME)
                    .select_related("user")
                )
            if selected == "course_year":
                logs = (
                    HistoryLog.objects
                    .filter(topic=HistoryTopic.COURSE_YEAR)
                    .select_related("user")
                )
            if selected == "major_name":
                logs = (
                    HistoryLog.objects
                    .filter(topic=HistoryTopic.MAJOR_NAME)
                    .select_related("user")
                )
                
            for log in logs:
                log.local_time = timezone.localtime(log.created_at, ZoneInfo("America/Vancouver")).strftime("%Y-%m-%d %H:%M:%S")

    context = {
        "options": options,
        "selected": selected,
        "logs": logs,
    }
    return render(request, "timetable/history.html", context)

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_term_affected(request, pk):
    """
    Return all courses currently pointing at this CourseTerm.
    Used by the preview modal for both edit and delete.
    """
    term = get_object_or_404(CourseTerm, pk=pk)
    qs = (Course.objects
          .filter(term=term)
          .select_related("code", "number", "section", "academic_year", "term")
          .order_by("code__name", "number__name", "section__name",
                    "academic_year__name", "term__name"))

    def safe_name(obj):
        return getattr(obj, "name", "") or "None"

    items = [{
        "code":   safe_name(c.code),
        "number": safe_name(c.number),
        "section":safe_name(c.section),
        "year":   safe_name(c.academic_year),
        "term":   safe_name(c.term),
    } for c in qs]

    return JsonResponse({"count": len(items), "items": items})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_term_list(request):
    terms = CourseTerm.objects.all()
    form = CourseTermForm()
    return render(request, "timetable/course_term_list.html", {"terms": terms, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_term_create(request):
    form = CourseTermForm(request.POST)
    if form.is_valid():
        obj = form.save()
        _log_history(
                    topic=HistoryTopic.COURSE_TERM,
                    user=request.user,
                    action=HistoryAction.CREATED,
                    after_value=obj.name,
        )
        messages.success(request, "Course Term created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_term")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_term_update(request, pk):
    term = get_object_or_404(CourseTerm, pk=pk)
    before = term.name
    form = CourseTermForm(request.POST, instance=term)
    if form.is_valid():
        obj = form.save()
        after = obj.name
        _log_history(
                    topic=HistoryTopic.COURSE_TERM,
                    user=request.user,
                    action=HistoryAction.EDITED,
                    before_value=before,
                    after_value=after,
        )
        messages.success(request, "Course Term edited.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Edit failed: {err}")
    return redirect("scheduler:course_term")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_term_delete(request, pk):
    term = get_object_or_404(CourseTerm, pk=pk)
    before = term.name
    term.delete()
    _log_history(
                topic=HistoryTopic.COURSE_TERM,
                user=request.user,
                action=HistoryAction.DELETED,
                before_value=before,
    )
    messages.success(request, "Course Term deleted.")
    return redirect("scheduler:course_term")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_code_affected(request, pk):
    """
    Return all courses currently pointing at this CourseCode.
    Used by the preview modal for both edit and delete of CourseCode.
    """
    code = get_object_or_404(CourseCode, pk=pk)
    qs = (Course.objects
          .filter(code=code)
          .select_related("code", "number", "section", "academic_year", "term")
          .order_by("code__name", "number__name", "section__name",
                    "academic_year__name", "term__name"))

    def safe_name(obj):
        return getattr(obj, "name", "") or "None"

    items = [{
        "code":   safe_name(c.code),
        "number": safe_name(c.number),
        "section":safe_name(c.section),
        "year":   safe_name(c.academic_year),
        "term":   safe_name(c.term),
    } for c in qs]

    return JsonResponse({"count": len(items), "items": items})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_code_list(request):
    codes = CourseCode.objects.all()
    form = CourseCodeForm()
    return render(request, "timetable/course_code_list.html", {"codes": codes, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_code_create(request):
    form = CourseCodeForm(request.POST)
    if form.is_valid():
        obj = form.save()
        _log_history(
                    topic=HistoryTopic.COURSE_CODE,
                    user=request.user,
                    action=HistoryAction.CREATED,
                    after_value=obj.name + obj.color,
        )
        messages.success(request, "Course Code created.")
    else:
        name_err = " ".join(form.errors.get("name", []))
        color_err = " ".join(form.errors.get("color", []))
        # Combine only non-empty error
        err_list = [msg.strip() for msg in [name_err, color_err] if msg]
        err = " ".join(err_list) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_code")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_code_update(request, pk):
    code = get_object_or_404(CourseCode, pk=pk)
    before = code.name + code.color
    form = CourseCodeForm(request.POST, instance=code)
    if form.is_valid():
        obj = form.save()
        after = obj.name + obj.color
        _log_history(
                    topic=HistoryTopic.COURSE_CODE,
                    user=request.user,
                    action=HistoryAction.EDITED,
                    before_value=before,
                    after_value=after,
        )
        messages.success(request, "Course Code edited.")
    else:
        name_err = " ".join(form.errors.get("name", []))
        color_err = " ".join(form.errors.get("color", []))
        # Combine only non-empty error
        err_list = [msg.strip() for msg in [name_err, color_err] if msg]
        err = " ".join(err_list) or "Please fix the errors and try again."
        messages.error(request, f"Edit failed: {err}")
    return redirect("scheduler:course_code")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_code_delete(request, pk):
    code = get_object_or_404(CourseCode, pk=pk)
    before = code.name + code.color
    code.delete()
    _log_history(
                topic=HistoryTopic.COURSE_CODE,
                user=request.user,
                action=HistoryAction.DELETED,
                before_value=before,
    )
    messages.success(request, "Course Code deleted.")
    return redirect("scheduler:course_code")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_number_affected(request, pk):
    """
    Return all courses currently pointing at this CourseNumber.
    Used by the preview modal for both edit and delete of CourseNumber.
    """
    number = get_object_or_404(CourseNumber, pk=pk)
    qs = (Course.objects
          .filter(number=number)
          .select_related("code", "number", "section", "academic_year", "term")
          .order_by("code__name", "number__name", "section__name",
                    "academic_year__name", "term__name"))

    def safe_name(obj):
        return getattr(obj, "name", "") or "None"

    items = [{
        "code":   safe_name(c.code),
        "number": safe_name(c.number),
        "section":safe_name(c.section),
        "year":   safe_name(c.academic_year),
        "term":   safe_name(c.term),
    } for c in qs]

    return JsonResponse({"count": len(items), "items": items})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_number_list(request):
    numbers = CourseNumber.objects.all()
    form = CourseNumberForm()
    return render(request, "timetable/course_number_list.html", {"numbers": numbers, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_number_create(request):
    form = CourseNumberForm(request.POST)
    if form.is_valid():
        obj = form.save()
        _log_history(
                    topic=HistoryTopic.COURSE_NUMBER,
                    user=request.user,
                    action=HistoryAction.CREATED,
                    after_value=obj.name,
        )
        messages.success(request, "Course Number created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_number")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_number_update(request, pk):
    number = get_object_or_404(CourseNumber, pk=pk)
    before = number.name
    form = CourseNumberForm(request.POST, instance=number)
    if form.is_valid():
        obj = form.save()
        after = obj.name
        _log_history(
                    topic=HistoryTopic.COURSE_NUMBER,
                    user=request.user,
                    action=HistoryAction.EDITED,
                    before_value=before,
                    after_value=after,
        )
        messages.success(request, "Course Number edited.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Edit failed: {err}")
    return redirect("scheduler:course_number")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_number_delete(request, pk):
    number = get_object_or_404(CourseNumber, pk=pk)
    before = number.name
    number.delete()
    _log_history(
                topic=HistoryTopic.COURSE_NUMBER,
                user=request.user,
                action=HistoryAction.DELETED,
                before_value=before,
    )
    messages.success(request, "Course Number deleted.")
    return redirect("scheduler:course_number")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_section_affected(request, pk):
    """
    Return all courses currently pointing at this CourseSection.
    Used by the preview modal for both edit and delete of CourseSection.
    """
    section = get_object_or_404(CourseSection, pk=pk)
    qs = (Course.objects
          .filter(section=section)
          .select_related("code", "number", "section", "academic_year", "term")
          .order_by("code__name", "number__name", "section__name",
                    "academic_year__name", "term__name"))

    def safe_name(obj):
        return getattr(obj, "name", "") or "None"

    items = [{
        "code":   safe_name(c.code),
        "number": safe_name(c.number),
        "section":safe_name(c.section),
        "year":   safe_name(c.academic_year),
        "term":   safe_name(c.term),
    } for c in qs]

    return JsonResponse({"count": len(items), "items": items})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_section_list(request):
    sections = CourseSection.objects.all()
    form = CourseSectionForm()
    return render(request, "timetable/course_section_list.html", {"sections": sections, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_section_create(request):
    form = CourseSectionForm(request.POST)
    if form.is_valid():
        obj = form.save()
        _log_history(
                    topic=HistoryTopic.COURSE_SECTION,
                    user=request.user,
                    action=HistoryAction.CREATED,
                    after_value=obj.name,
        )
        messages.success(request, "Course Section created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_section")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_section_update(request, pk):
    section = get_object_or_404(CourseSection, pk=pk)
    before = section.name
    form = CourseSectionForm(request.POST, instance=section)
    if form.is_valid():
        obj = form.save()
        after = obj.name
        _log_history(
                    topic=HistoryTopic.COURSE_SECTION,
                    user=request.user,
                    action=HistoryAction.EDITED,
                    before_value=before,
                    after_value=after,
        )
        messages.success(request, "Course Section edited.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Edit failed: {err}")
    return redirect("scheduler:course_section")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_section_delete(request, pk):
    section = get_object_or_404(CourseSection, pk=pk)
    before = section.name
    section.delete()
    _log_history(
                topic=HistoryTopic.COURSE_SECTION,
                user=request.user,
                action=HistoryAction.DELETED,
                before_value=before,
    )
    messages.success(request, "Course Section deleted.")
    return redirect("scheduler:course_section")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_time_affected(request, pk):
    """
    Return all courses referencing this CourseTime as start_time or end_time.
    Used by the preview modal for both edit and delete of CourseTime.
    """
    t = get_object_or_404(CourseTime, pk=pk)
    qs = (Course.objects
          .filter(Q(start_time=t) | Q(end_time=t))
          .select_related("code", "number", "section", "academic_year", "term")
          .order_by("code__name", "number__name", "section__name",
                    "academic_year__name", "term__name"))

    def safe_name(obj):
        return getattr(obj, "name", "") or "None"

    items = [{
        "code":   safe_name(c.code),
        "number": safe_name(c.number),
        "section":safe_name(c.section),
        "year":   safe_name(c.academic_year),
        "term":   safe_name(c.term),
    } for c in qs]

    return JsonResponse({"count": len(items), "items": items})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_time_list(request):
    times = CourseTime.objects.all()
    form = CourseTimeForm()
    hours   = [f"{i:02d}" for i in range(24)]
    minutes = [f"{i:02d}" for i in range(60)]
    return render(
        request,
        "timetable/course_time_list.html",
        {"times": times, "form": form, "hours": hours, "minutes": minutes},
    )

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_time_create(request):
    form = CourseTimeForm(request.POST)
    if form.is_valid():
        obj = form.save()
        _log_history(
                    topic=HistoryTopic.COURSE_TIME,
                    user=request.user,
                    action=HistoryAction.CREATED,
                    after_value=obj.name,
        )
        messages.success(request, "Course Time created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_time")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_time_update(request, pk):
    t = get_object_or_404(CourseTime, pk=pk)
    before = t.name
    form = CourseTimeForm(request.POST, instance=t)
    if form.is_valid():
        obj = form.save()
        after = obj.name
        _log_history(
                    topic=HistoryTopic.COURSE_TIME,
                    user=request.user,
                    action=HistoryAction.EDITED,
                    before_value=before,
                    after_value=after,
        )
        messages.success(request, "Course Time edited.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Edit failed: {err}")
    return redirect("scheduler:course_time")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_time_delete(request, pk):
    t = get_object_or_404(CourseTime, pk=pk)
    before = t.name
    t.delete()
    _log_history(
                topic=HistoryTopic.COURSE_TIME,
                user=request.user,
                action=HistoryAction.DELETED,
                before_value=before,
    )
    messages.success(request, "Course Time deleted.")
    return redirect("scheduler:course_time")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_year_affected(request, pk):
    """
    Return all courses currently pointing at this CourseYear.
    Used by the preview modal for both edit and delete.
    """
    y = get_object_or_404(CourseYear, pk=pk)
    qs = (Course.objects
          .filter(academic_year=y)
          .select_related("code", "number", "section", "academic_year", "term")
          .order_by("code__name", "number__name", "section__name",
                    "academic_year__name", "term__name"))

    def safe_name(obj):
        return getattr(obj, "name", "") or "None"

    items = [{
        "code":   safe_name(c.code),
        "number": safe_name(c.number),
        "section":safe_name(c.section),
        "year":   safe_name(c.academic_year),
        "term":   safe_name(c.term),
    } for c in qs]

    return JsonResponse({"count": len(items), "items": items})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def course_year_list(request):
    years = CourseYear.objects.all()
    form = CourseYearForm()
    # pass choices to template for the Edit modal's select
    year_choices = [str(y) for y in range(2024, 2043)]
    return render(request, "timetable/course_year_list.html",
                  {"years": years, "form": form, "year_choices": year_choices})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_year_create(request):
    form = CourseYearForm(request.POST)
    if form.is_valid():
        obj = form.save()
        _log_history(
                    topic=HistoryTopic.COURSE_YEAR,
                    user=request.user,
                    action=HistoryAction.CREATED,
                    after_value=obj.name,
        )
        messages.success(request, "Course Year created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_year")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_year_update(request, pk):
    y = get_object_or_404(CourseYear, pk=pk)
    before = y.name
    form = CourseYearForm(request.POST, instance=y)
    if form.is_valid():
        obj = form.save()
        after = obj.name
        _log_history(
                    topic=HistoryTopic.COURSE_YEAR,
                    user=request.user,
                    action=HistoryAction.EDITED,
                    before_value=before,
                    after_value=after,
        )
        messages.success(request, "Course Year edited.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Edit failed: {err}")
    return redirect("scheduler:course_year")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def course_year_delete(request, pk):
    y = get_object_or_404(CourseYear, pk=pk)
    before = y.name
    y.delete()
    _log_history(
                topic=HistoryTopic.COURSE_YEAR,
                user=request.user,
                action=HistoryAction.DELETED,
                before_value=before,
    )
    messages.success(request, "Course Year deleted.")
    return redirect("scheduler:course_year")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def major_name_affected(request, pk):
    """
    Return all majors currently pointing to this MajorName.
    Used by the preview modal for both edit and delete.
    """
    major_name = get_object_or_404(MajorName, pk=pk)
    qs = (Major.objects
          .filter(name=major_name)
          .select_related("name", "year_level")
          .order_by("name__name", "year_level__name"))

    def safe_name(obj):
        return getattr(obj, "name", "") or "None"

    items = [{
        "major_name": safe_name(m.name),            
        "year_level":   safe_name(m.year_level),     
    } for m in qs]

    return JsonResponse({"count": len(items), "items": items})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def major_name_list(request):
    names = MajorName.objects.all()
    form = MajorNameForm()
    return render(request, "timetable/major_name_list.html", {"names": names, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def major_name_create(request):
    form = MajorNameForm(request.POST)
    if form.is_valid():
        obj = form.save()
        _log_history(
                    topic=HistoryTopic.MAJOR_NAME,
                    user=request.user,
                    action=HistoryAction.CREATED,
                    after_value=obj.name,
        )
        messages.success(request, "Major Name created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:major_name")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def major_name_update(request, pk):
    name = get_object_or_404(MajorName, pk=pk)
    before = name.name
    form = MajorNameForm(request.POST, instance=name)
    if form.is_valid():
        obj = form.save()
        after = obj.name
        _log_history(
                    topic=HistoryTopic.MAJOR_NAME,
                    user=request.user,
                    action=HistoryAction.EDITED,
                    before_value=before,
                    after_value=after,
        )
        messages.success(request, "Major Name edited.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Edit failed: {err}")
    return redirect("scheduler:major_name")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def major_name_delete(request, pk):
    name = get_object_or_404(MajorName, pk=pk)
    before = name.name
    name.delete()
    _log_history(
                topic=HistoryTopic.MAJOR_NAME,
                user=request.user,
                action=HistoryAction.DELETED,
                before_value=before,
    )
    messages.success(request, "Major Name deleted.")
    return redirect("scheduler:major_name")

# --- AJAX: year levels available for a given major name ---
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_GET
def ajax_levels_for_major(request):
    major_name = request.GET.get("major", "").strip()
    if not major_name:
        return JsonResponse({"levels": []})

    name_obj = get_object_or_404(MajorName, name=major_name)
    levels = (
        Major.objects
        .filter(name=name_obj)
        .select_related("year_level")
        .order_by("year_level__name")
        .values_list("year_level__name", flat=True)
        .distinct()
    )
    return JsonResponse({"levels": list(levels)})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def requirements(request):
    """
    Renders the Requirements page with two required filters:
    - Major Name
    - Major Year Level

    After both are chosen and Search is clicked, we show the table of courses
    linked to that major, or “No such major exists.”
    """
    # dynamic dropdown data
    major_names = MajorName.objects.order_by("name")

    # read selection (GET)
    selected_major_name = request.GET.get("major", "").strip()
    selected_level_name = request.GET.get("level", "").strip()
    submitted = "search" in request.GET

    # preload year levels options for the selected name, this make UI more beautiful than client fetch available_levels_for_name
    available_levels_for_name = []
    if selected_major_name:
        name_obj = MajorName.objects.filter(name=selected_major_name).first()
        if name_obj:
            available_levels_for_name = list(
                Major.objects
                .filter(name=name_obj)
                .values_list("year_level__name", flat=True)
                .distinct()
                .order_by("year_level__name")
            )

    courses = None
    major_obj = None
    not_found = False

    if submitted:
        if not selected_major_name or not selected_level_name:
            messages.error(request, "You have to select both Major Name and Major Year Level.")
        else:
            level_obj = get_object_or_404(MajorYearLevel, name=selected_level_name)
            major_name_obj = get_object_or_404(MajorName, name=selected_major_name)
            major_obj = Major.objects.filter(name=major_name_obj, year_level=level_obj).first()
            if major_obj:
                # one id per (code, number) pair inside this major
                subq = (
                    major_obj.courses
                    .values("code", "number")
                    .annotate(min_id=Min("id"))
                    .values("min_id")
                )

                courses = (
                    Course.objects
                    .filter(id__in=subq)
                    .select_related("code", "number")
                    .order_by("code__name", "number__name")
                )
            else:
                not_found = True
                courses = []

    course_codes = CourseCode.objects.order_by("name")

    return render(request, "timetable/requirements.html", {
        "major_names": major_names,
        "selected_major_name": selected_major_name,  
        "selected_level_name": selected_level_name,      
        "submitted": submitted,
        "major_obj": major_obj,
        "courses": courses,
        "not_found": not_found,
        "course_codes": course_codes,
        "available_levels_for_name": available_levels_for_name,
    })

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def requirements_detach_course(request):
    """
    Detach ALL courses that share (code, number) from a given (MajorName, MajorYearLevel).
    Redirects back to the Requirements page showing the updated table.
    """
    major_name = request.POST.get("major_name", "").strip()
    level_name   = request.POST.get("level_name", "").strip()
    code_name    = request.POST.get("code_name", "").strip()
    number_name  = request.POST.get("number_name", "").strip()

    # Resolve major
    name_obj  = get_object_or_404(MajorName, name=major_name)
    level_obj = get_object_or_404(MajorYearLevel, name=level_name)
    major   = Major.objects.filter(name=name_obj, year_level=level_obj).first()

    # Find all matching courses already attached to this major
    qs = major.courses.filter(code__name=code_name, number__name=number_name)

    # Detach them all from the M2M
    major.courses.remove(*qs)
    messages.success(request, "Course removed.")

    # Send the user back to the same results view
    url = (f"{reverse('scheduler:requirements')}"
           f"?major={major_name}&level={level_name}&search=1")
    return redirect(url)

# --- AJAX: numbers available for a given code ---
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_GET
def ajax_numbers_for_code(request):
    code_name = request.GET.get("code", "").strip()
    if not code_name:
        return JsonResponse({"numbers": []})

    nums = (Course.objects
            .filter(code__name=code_name)
            .exclude(number__name__isnull=True)
            .order_by("number__name")
            .values_list("number__name", flat=True)
            .distinct())
    return JsonResponse({"numbers": list(nums)})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def requirements_attach_course(request):
    major_name = request.POST.get("major_name", "").strip()
    level_name   = request.POST.get("level_name", "").strip()
    code_name    = request.POST.get("code_name", "").strip()
    number_name  = request.POST.get("number_name", "").strip()

    # Resolve the major
    name_obj  = get_object_or_404(MajorName, name=major_name)
    level_obj = get_object_or_404(MajorYearLevel, name=level_name)
    major   = Major.objects.filter(name=name_obj, year_level=level_obj).first()

    # If already present, block with a message
    already = major.courses.filter(code__name=code_name, number__name=number_name).exists()
    if already:
        messages.error(request, "Add failed: A Course with this code and this number already exists.")
    else:
        # Attach ALL matching Course rows to this major
        to_add = Course.objects.filter(code__name=code_name, number__name=number_name)
        major.courses.add(*to_add)
        messages.success(request, "Course added.")

    # Return to the same results view (table will show the new row)
    url = (f"{reverse('scheduler:requirements')}"
           f"?major={major_name}&level={level_name}&search=1")
    return redirect(url)

def _human_readable_size(num_bytes):
    if num_bytes < 1024:
        return f"{num_bytes} B"
    kb = num_bytes / 1024.0
    if kb < 1024:
        return f"{kb:.1f} KB".rstrip("0").rstrip(".")
    mb = kb / 1024.0
    return f"{mb:.1f} MB".rstrip("0").rstrip(".")


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
def import_page(request):
    upload_success = False
    uploaded_file_name = ""
    uploaded_file_size = ""

    if request.method == "POST":
        f = request.FILES.get("requirements_file")

        if not f:
            messages.error(request, "An error occurred, please upload again.")
        else:
            try:
                # Clean up any previous temp file for this session
                old_path = request.session.get("import_temp_path")
                if old_path and os.path.exists(old_path):
                    os.remove(old_path)
                
                suffix = os.path.splitext(f.name)[1] or ".xlsx"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    for chunk in f.chunks():
                        tmp.write(chunk)
                    temp_path = tmp.name

                # Store metadata in session so Populate can use it
                request.session["import_temp_path"] = temp_path
                request.session["import_original_name"] = f.name
                request.session["import_size_bytes"] = f.size

                upload_success = True
                uploaded_file_name = f.name
                uploaded_file_size = _human_readable_size(f.size)

                messages.success(request, "Upload successful.")
            except Exception:
                # fallback
                request.session.pop("import_temp_path", None)
                request.session.pop("import_original_name", None)
                request.session.pop("import_size_bytes", None)
                messages.error(request, "An error occurred, please upload again.")

    context = {
        "upload_success": upload_success,
        "uploaded_file_name": uploaded_file_name,
        "uploaded_file_size": uploaded_file_size,
    }
    return render(request, "timetable/import.html", context)

def _parse_time_token(raw):
    if not raw:
        return None
    parts = str(raw).strip().split()
    if not parts:
        return None

    time_part = parts[0] # e.g. "9:30"
    meridian = parts[1].lower() if len(parts) > 1 else ""

    # Split hour and minute
    if ":" in time_part:
        hour_str, minute_str = time_part.split(":", 1)
    else:
        hour_str, minute_str = time_part, "00"

    try:
        hour = int(hour_str)
        minute = int(minute_str)
    except ValueError:
        return None

    if meridian in ("p.m.", "pm", "p.m"):
        if hour != 12:
            hour += 12

    return f"{hour:02d}:{minute:02d}"

def _parse_import_excel(path):
    """
    Read the uploaded Excel and return a list of parsed course dicts.

    Each item looks like:
    {
        "code": "APBI",
        "number": "200" or "200SpecialTopic",
        "section": "001",
        "year": "2025",
        "term": "W1",
        "days": ["Mon", "Wed"],
        "start_time": "11:00",
        "end_time": "13:00",
    }
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    # Map column headers to indices
    header_row = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {name: header_row.index(name) for name in header_row if name}

    required_cols = [
        "Course Subject",
        "Course Number",
        "Special Topic",
        "Section Number",
        "Academic Period",
        "Term",
        "Meeting Pattern and Location",
    ]
    for col in required_cols:
        if col not in idx:
            raise ValueError(f"Missing column {col} in Excel file.")

    parsed = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue

        def val(col_name):
            v = row[idx[col_name]]
            if v is None:
                return ""
            return str(v).strip()

        subject = val("Course Subject")
        course_number = val("Course Number")
        special_topic = val("Special Topic")
        section_number = val("Section Number")
        academic_period = val("Academic Period")
        term = val("Term")
        meeting = val("Meeting Pattern and Location")

        # CourseCode
        code_name = subject or None

        # CourseNumber
        if special_topic:
            number_name = f"{course_number}{special_topic}" or None
        else:
            number_name = course_number or None

        # CourseSection
        raw_section = section_number or ""
        if special_topic and "_" in raw_section:
            section_name = raw_section.split("_", 1)[1].strip() or None
        else:
            section_name = raw_section or None

        # CourseYear
        year_name = (academic_period[:4].strip() if academic_period else None)

        # Term
        term_name = term or None

        # Meeting pattern / day / time
        raw_day = None
        raw_time = None
        if meeting:
            parts = [p.strip() for p in str(meeting).split("|") if p and str(p).strip()]
            if parts:
                if parts[0] == "UBCV":
                    # UBCV | ... | ... | ... | day | time
                    if len(parts) >= 6:
                        raw_day = parts[4]
                        raw_time = parts[5]
                else:
                    if len(parts) >= 2:
                        raw_day = parts[0]
                        raw_time = parts[1]

        day_names = []
        if raw_day:
            day_names = [d.strip() for d in raw_day.split(" ") if d.strip()]

        start_token = None
        end_token = None
        if raw_time:
            time_parts = [t.strip() for t in raw_time.split("-") if t.strip()]
            if len(time_parts) >= 2:
                start_token, end_token = time_parts[0], time_parts[1]

        start_name = _parse_time_token(start_token) if start_token else None
        end_name = _parse_time_token(end_token) if end_token else None

        parsed.append({
            "code": code_name or None,
            "number": number_name or None,
            "section": section_name or None,
            "year": year_name or None,
            "term": term_name or None,
            "days": day_names,
            "start_time": start_name or None,
            "end_time": end_name or None,
        })

    return parsed

DISTINCT_COLORS = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # gray
    "#bcbd22",  # olive
    "#17becf",  # cyan
]

def _next_code_color(used_colors: set):
    # Pick a color that is not already used
    for c in DISTINCT_COLORS:
        if c not in used_colors:
            used_colors.add(c)
            return c
    # Fallback: random unique color
    while True:
        c = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        if c not in used_colors:
            used_colors.add(c)
            return c

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def import_populate_preview(request):
    temp_path = request.session.get("import_temp_path")
    if not temp_path or not os.path.exists(temp_path):
        messages.error(request, "An error occurred, please try again.")
        return JsonResponse({"ok": False, "redirect": reverse("scheduler:import_page")})

    try:
        parsed_courses = _parse_import_excel(temp_path)
    except Exception:
        messages.error(request, "An error occurred, please try again.")
        return JsonResponse({"ok": False, "redirect": reverse("scheduler:import_page")})

    # Store the parsed data in the session for the commit step
    request.session["import_parsed_courses"] = parsed_courses

    existing_codes = set(CourseCode.objects.values_list("name", flat=True))
    existing_numbers = set(CourseNumber.objects.values_list("name", flat=True))
    existing_sections = set(CourseSection.objects.values_list("name", flat=True))
    existing_years = set(CourseYear.objects.values_list("name", flat=True))
    existing_terms = set(CourseTerm.objects.values_list("name", flat=True))
    existing_days = set(CourseDay.objects.values_list("name", flat=True))
    existing_times = set(CourseTime.objects.values_list("name", flat=True))

    codes = set()
    numbers = set()
    sections = set()
    years = set()
    terms = set()
    days = set()
    times = set()

    for c in parsed_courses:
        if c["code"]:
            codes.add(c["code"])
        if c["number"]:
            numbers.add(c["number"])
        if c["section"]:
            sections.add(c["section"])
        if c["year"]:
            years.add(c["year"])
        if c["term"]:
            terms.add(c["term"])
        for d in c["days"]:
            days.add(d)
        if c["start_time"]:
            times.add(c["start_time"])
        if c["end_time"]:
            times.add(c["end_time"])

    new_fields = {
        "codes": sorted(n for n in codes if n not in existing_codes),
        "numbers": sorted(n for n in numbers if n not in existing_numbers),
        "sections": sorted(n for n in sections if n not in existing_sections),
        "years": sorted(n for n in years if n not in existing_years),
        "terms": sorted(n for n in terms if n not in existing_terms),
        "days": sorted(n for n in days if n not in existing_days),
        "times": sorted(n for n in times if n not in existing_times),
    }

    # Determine courses that will be new
    new_courses_preview = []
    
    for c in parsed_courses:
        # If any of the fields are new, the course is automatically new
        if (
            (c["code"] in new_fields["codes"])
            or (c["number"] in new_fields["numbers"])
            or (c["section"] in new_fields["sections"])
            or (c["year"] in new_fields["years"])
            or (c["term"] in new_fields["terms"])
        ):
            is_new = True
        else:
            # All fields already exist in DB: check if course exists
            filters = {}
            if c["code"]:
                filters["code__name"] = c["code"]
            else:
                filters["code__isnull"] = True

            if c["number"]:
                filters["number__name"] = c["number"]
            else:
                filters["number__isnull"] = True

            if c["section"]:
                filters["section__name"] = c["section"]
            else:
                filters["section__isnull"] = True

            if c["year"]:
                filters["academic_year__name"] = c["year"]
            else:
                filters["academic_year__isnull"] = True

            if c["term"]:
                filters["term__name"] = c["term"]
            else:
                filters["term__isnull"] = True

            is_new = not Course.objects.filter(**filters).exists()

        if is_new:
            new_courses_preview.append({
                "code": c["code"] or None,
                "number": c["number"] or None,
                "section": c["section"] or None,
                "year": c["year"] or None,
                "term": c["term"] or None,
            })

    return JsonResponse({
        "ok": True,
        "course_fields": new_fields,
        "courses": new_courses_preview,
    })

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@require_POST
def import_populate_commit(request):
    parsed_courses = request.session.get("import_parsed_courses")
    if not parsed_courses:
        messages.error(request, "An error occurred, please try again.")
        return JsonResponse({"ok": False, "redirect": reverse("scheduler:import_page")})

    # Build caches of existing objects
    code_cache = {c.name: c for c in CourseCode.objects.all()}
    number_cache = {n.name: n for n in CourseNumber.objects.all()}
    section_cache = {s.name: s for s in CourseSection.objects.all()}
    year_cache = {y.name: y for y in CourseYear.objects.all()}
    term_cache = {t.name: t for t in CourseTerm.objects.all()}
    day_cache = {d.name: d for d in CourseDay.objects.all()}
    time_cache = {t.name: t for t in CourseTime.objects.all()}

    used_colors = set(CourseCode.objects.values_list("color", flat=True))

    def get_code(name):
        if not name:
            return None
        if name in code_cache:
            return code_cache[name]
        color = _next_code_color(used_colors)
        obj = CourseCode.objects.create(name=name, color=color)
        code_cache[name] = obj
        return obj

    def get_simple(model_cache, ModelClass, name):
        if not name:
            return None
        if name in model_cache:
            return model_cache[name]
        obj = ModelClass.objects.create(name=name)
        model_cache[name] = obj
        return obj

    for c in parsed_courses:

        code_obj = get_code(c["code"])
        number_obj = get_simple(number_cache, CourseNumber, c["number"])
        section_obj = get_simple(section_cache, CourseSection, c["section"])
        year_obj = get_simple(year_cache, CourseYear, c["year"])
        term_obj = get_simple(term_cache, CourseTerm, c["term"])

        start_time_obj = None
        end_time_obj = None
        if c["start_time"]:
            if c["start_time"] in time_cache:
                start_time_obj = time_cache[c["start_time"]]
            else:
                start_time_obj = CourseTime.objects.create(name=c["start_time"])
                time_cache[c["start_time"]] = start_time_obj

        if c["end_time"]:
            if c["end_time"] in time_cache:
                end_time_obj = time_cache[c["end_time"]]
            else:
                end_time_obj = CourseTime.objects.create(name=c["end_time"])
                time_cache[c["end_time"]] = end_time_obj

        day_objs = []
        for d in c["days"]:
            if d in day_cache:
                day_objs.append(day_cache[d])
            else:
                obj = CourseDay.objects.create(name=d)
                day_cache[d] = obj
                day_objs.append(obj)

        # Check if course already exists
        filters = {}
        if code_obj:
            filters["code"] = code_obj
        else:
            filters["code__isnull"] = True

        if number_obj:
            filters["number"] = number_obj
        else:
            filters["number__isnull"] = True

        if section_obj:
            filters["section"] = section_obj
        else:
            filters["section__isnull"] = True

        if year_obj:
            filters["academic_year"] = year_obj
        else:
            filters["academic_year__isnull"] = True

        if term_obj:
            filters["term"] = term_obj
        else:
            filters["term__isnull"] = True

        course = Course.objects.filter(**filters).first()
        if course is None:
            course = Course.objects.create(
                code=code_obj,
                number=number_obj,
                section=section_obj,
                academic_year=year_obj,
                term=term_obj,
                start_time=start_time_obj,
                end_time=end_time_obj,
            )
            if day_objs:
                course.day.set(day_objs)

    # Clean up data
    request.session.pop("import_parsed_courses", None)
    request.session.pop("import_temp_path", None)
    request.session.pop("import_original_name", None)
    request.session.pop("import_size_bytes", None)

    messages.success(request, "Populate successful.")
    return JsonResponse({"ok": True, "redirect": reverse("scheduler:import_page")})
