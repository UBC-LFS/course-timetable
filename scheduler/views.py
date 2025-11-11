from django.shortcuts import render
from .models import CourseTerm, CourseCode, CourseNumber, CourseSection, CourseTime, CourseDay, Course, CourseYear, ProgramName
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
from .models import Program, ProgramYearLevel
from .forms import ProgramNameForm
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Min
from django.views.decorators.http import require_GET
import json
from accounts.views import staff_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control


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
@staff_required
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
@staff_required
def landing_page(request):
    if not request.user.is_authenticated:
        return redirect('accounts:ldap_login')

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
    program_names = ProgramName.objects.order_by("name")

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
            Program.objects
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
                .order_by("id")
            )

            # BY Course
            if course_filters:
                or_q = Q()
                for f in course_filters:
                    code = f.get("code", "")
                    nums = f.get("numbers", [])
                    if not code and not nums:
                        continue
                    if code and nums:
                        or_q |= Q(code__name=code, number__name__in=nums)
                    elif code:
                        or_q |= Q(code__name=code)
                if or_q:
                    base_qs = base_qs.filter(or_q)

            # By Program
            if selected_pname and not selected_plevel:
                base_qs = base_qs.filter(programs__name__name=selected_pname)
            elif selected_pname and selected_plevel:
                base_qs = base_qs.filter(programs__name__name=selected_pname,
                                          programs__year_level__name=selected_plevel)
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
        'program_names': program_names,
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
@staff_required
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
            messages.error(request, "You have to select at least one Academic Year.")
        else:
            courses = Course.objects.all().order_by("id").prefetch_related("day")

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
    order = ["Mon", "Tues", "Wed", "Thurs", "Fri"]
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
@staff_required
def create_course(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course created successfully.")
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
@staff_required
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated successfully.")
            return redirect("scheduler:view_courses")
        summary = _summarize_form_errors(form) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {summary}")
    else:
        form = CourseForm(instance=course)

    return render(request, "timetable/course_form.html", {
        "title": "Edit Course",
        "form": form,
    })

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
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
@staff_required
def course_term_list(request):
    terms = CourseTerm.objects.order_by("id")
    form = CourseTermForm()
    return render(request, "timetable/course_term_list.html", {"terms": terms, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_term_create(request):
    form = CourseTermForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Term created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_term")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_term_update(request, pk):
    term = get_object_or_404(CourseTerm, pk=pk)
    form = CourseTermForm(request.POST, instance=term)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Term updated.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_term")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_term_delete(request, pk):
    term = get_object_or_404(CourseTerm, pk=pk)
    term.delete()
    messages.success(request, "Course Term deleted.")
    return redirect("scheduler:course_term")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
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
@staff_required
def course_code_list(request):
    codes = CourseCode.objects.order_by("id")
    form = CourseCodeForm()
    return render(request, "timetable/course_code_list.html", {"codes": codes, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_code_create(request):
    form = CourseCodeForm(request.POST)
    if form.is_valid():
        form.save()
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
@staff_required
@require_POST
def course_code_update(request, pk):
    code = get_object_or_404(CourseCode, pk=pk)
    form = CourseCodeForm(request.POST, instance=code)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Code updated.")
    else:
        name_err = " ".join(form.errors.get("name", []))
        color_err = " ".join(form.errors.get("color", []))
        # Combine only non-empty error
        err_list = [msg.strip() for msg in [name_err, color_err] if msg]
        err = " ".join(err_list) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_code")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_code_delete(request, pk):
    code = get_object_or_404(CourseCode, pk=pk)
    code.delete()
    messages.success(request, "Course Code deleted.")
    return redirect("scheduler:course_code")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
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
@staff_required
def course_number_list(request):
    numbers = CourseNumber.objects.order_by("id")
    form = CourseNumberForm()
    return render(request, "timetable/course_number_list.html", {"numbers": numbers, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_number_create(request):
    form = CourseNumberForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Number created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_number")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_number_update(request, pk):
    number = get_object_or_404(CourseNumber, pk=pk)
    form = CourseNumberForm(request.POST, instance=number)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Number updated.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_number")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_number_delete(request, pk):
    number = get_object_or_404(CourseNumber, pk=pk)
    number.delete()
    messages.success(request, "Course Number deleted.")
    return redirect("scheduler:course_number")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
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
@staff_required
def course_section_list(request):
    sections = CourseSection.objects.order_by("id")
    form = CourseSectionForm()
    return render(request, "timetable/course_section_list.html", {"sections": sections, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_section_create(request):
    form = CourseSectionForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Section created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_section")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_section_update(request, pk):
    section = get_object_or_404(CourseSection, pk=pk)
    form = CourseSectionForm(request.POST, instance=section)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Section updated.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_section")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_section_delete(request, pk):
    section = get_object_or_404(CourseSection, pk=pk)
    section.delete()
    messages.success(request, "Course Section deleted.")
    return redirect("scheduler:course_section")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
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
@staff_required
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

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_time_create(request):
    form = CourseTimeForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Time created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_time")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_time_update(request, pk):
    t = get_object_or_404(CourseTime, pk=pk)
    form = CourseTimeForm(request.POST, instance=t)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Time updated.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_time")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_time_delete(request, pk):
    t = get_object_or_404(CourseTime, pk=pk)
    t.delete()
    messages.success(request, "Course Time deleted.")
    return redirect("scheduler:course_time")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
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
@staff_required
def course_year_list(request):
    years = CourseYear.objects.order_by("id")
    form = CourseYearForm()
    # pass choices to template for the Edit modal's select
    year_choices = [str(y) for y in range(2024, 2043)]
    return render(request, "timetable/course_year_list.html",
                  {"years": years, "form": form, "year_choices": year_choices})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_year_create(request):
    form = CourseYearForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Year created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:course_year")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_year_update(request, pk):
    y = get_object_or_404(CourseYear, pk=pk)
    form = CourseYearForm(request.POST, instance=y)
    if form.is_valid():
        form.save()
        messages.success(request, "Course Year updated.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:course_year")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def course_year_delete(request, pk):
    y = get_object_or_404(CourseYear, pk=pk)
    y.delete()
    messages.success(request, "Course Year deleted.")
    return redirect("scheduler:course_year")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
def program_name_affected(request, pk):
    """
    Return all programs currently pointing to this ProgramName.
    Used by the preview modal for both edit and delete.
    """
    program_name = get_object_or_404(ProgramName, pk=pk)
    qs = (Program.objects
          .filter(name=program_name)
          .select_related("name", "year_level")
          .order_by("name__name", "year_level__name"))

    def safe_name(obj):
        return getattr(obj, "name", "") or "None"

    items = [{
        "program_name": safe_name(p.name),            
        "year_level":   safe_name(p.year_level),     
    } for p in qs]

    return JsonResponse({"count": len(items), "items": items})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
def program_name_list(request):
    names = ProgramName.objects.order_by("id")
    form = ProgramNameForm()
    return render(request, "timetable/program_name_list.html", {"names": names, "form": form})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def program_name_create(request):
    form = ProgramNameForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Program Name created.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Create failed: {err}")
    return redirect("scheduler:program_name")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def program_name_update(request, pk):
    name = get_object_or_404(ProgramName, pk=pk)
    form = ProgramNameForm(request.POST, instance=name)
    if form.is_valid():
        form.save()
        messages.success(request, "Program Name updated.")
    else:
        err = " ".join(form.errors.get("name", [])) or "Please fix the errors and try again."
        messages.error(request, f"Update failed: {err}")
    return redirect("scheduler:program_name")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def program_name_delete(request, pk):
    name = get_object_or_404(ProgramName, pk=pk)
    name.delete()
    messages.success(request, "Program Name deleted.")
    return redirect("scheduler:program_name")

# --- AJAX: year levels available for a given program name ---
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_GET
def ajax_levels_for_program(request):
    program_name = request.GET.get("program", "").strip()
    if not program_name:
        return JsonResponse({"levels": []})

    name_obj = get_object_or_404(ProgramName, name=program_name)
    levels = (
        Program.objects
        .filter(name=name_obj)
        .select_related("year_level")
        .order_by("year_level__name")
        .values_list("year_level__name", flat=True)
        .distinct()
    )
    return JsonResponse({"levels": list(levels)})

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
def requirements(request):
    """
    Renders the Requirements page with two required filters:
    - Program Name
    - Program Year Level

    After both are chosen and Search is clicked, we show the table of courses
    linked to that program, or “No such program exists.”
    """
    # dynamic dropdown data
    program_names = ProgramName.objects.order_by("name")
    year_levels = ProgramYearLevel.objects.order_by("name")

    # read selection (GET)
    selected_program_name = request.GET.get("program", "").strip()
    selected_level_name = request.GET.get("level", "").strip()
    submitted = "search" in request.GET  # Search button pressed

    # preload year levels options for the selected name, this make UI more beautiful than client fetch available_levels_for_name
    available_levels_for_name = []
    if selected_program_name:
        name_obj = ProgramName.objects.filter(name=selected_program_name).first()
        if name_obj:
            available_levels_for_name = list(
                Program.objects
                .filter(name=name_obj)
                .values_list("year_level__name", flat=True)
                .distinct()
                .order_by("year_level__name")
            )

    courses = None
    program_obj = None
    not_found = False

    if submitted:
        if not selected_program_name or not selected_level_name:
            messages.error(request, "You have to select both Program Name and Program Year Level.")
        else:
            level_obj = get_object_or_404(ProgramYearLevel, name=selected_level_name)
            program_name_obj = get_object_or_404(ProgramName, name=selected_program_name)
            program_obj = Program.objects.filter(name=program_name_obj, year_level=level_obj).first()
            if program_obj:
                # one id per (code, number) pair inside this program
                subq = (
                    program_obj.courses
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
        "program_names": program_names,
        "year_levels": year_levels,
        "selected_program_name": selected_program_name,  
        "selected_level_name": selected_level_name,      
        "submitted": submitted,
        "program_obj": program_obj,
        "courses": courses,
        "not_found": not_found,
        "course_codes": course_codes,
        "available_levels_for_name": available_levels_for_name,
    })

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
@require_POST
def requirements_detach_course(request):
    """
    Detach ALL courses that share (code, number) from a given (ProgramName, ProgramYearLevel).
    Redirects back to the Requirements page showing the updated table.
    """
    program_name = request.POST.get("program_name", "").strip()
    level_name   = request.POST.get("level_name", "").strip()
    code_name    = request.POST.get("code_name", "").strip()
    number_name  = request.POST.get("number_name", "").strip()

    # Resolve program
    name_obj  = get_object_or_404(ProgramName, name=program_name)
    level_obj = get_object_or_404(ProgramYearLevel, name=level_name)
    program   = Program.objects.filter(name=name_obj, year_level=level_obj).first()

    # Find all matching courses already attached to this program
    qs = program.courses.filter(code__name=code_name, number__name=number_name)

    # Detach them all from the M2M
    program.courses.remove(*qs)
    messages.success(request, "Course removed.")

    # Send the user back to the same results view
    url = (f"{reverse('scheduler:requirements')}"
           f"?program={program_name}&level={level_name}&search=1")
    return redirect(url)

# --- AJAX: numbers available for a given code ---
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@login_required(login_url='accounts:ldap_login')
@staff_required
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
@staff_required
@require_POST
def requirements_attach_course(request):
    program_name = request.POST.get("program_name", "").strip()
    level_name   = request.POST.get("level_name", "").strip()
    code_name    = request.POST.get("code_name", "").strip()
    number_name  = request.POST.get("number_name", "").strip()

    # Resolve the program
    name_obj  = get_object_or_404(ProgramName, name=program_name)
    level_obj = get_object_or_404(ProgramYearLevel, name=level_name)
    program   = Program.objects.filter(name=name_obj, year_level=level_obj).first()

    # If already present, block with a friendly message
    already = program.courses.filter(code__name=code_name, number__name=number_name).exists()
    if already:
        messages.error(request, "Add failed: A Course with this code and this number already exists.")
    else:
        # Attach ALL matching Course rows to this program
        to_add = Course.objects.filter(code__name=code_name, number__name=number_name)
        program.courses.add(*to_add)
        messages.success(request, "Course added.")

    # Return to the same results view (table will show the new row)
    url = (f"{reverse('scheduler:requirements')}"
           f"?program={program_name}&level={level_name}&search=1")
    return redirect(url)