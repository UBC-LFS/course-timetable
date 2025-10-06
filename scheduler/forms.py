from django import forms
from datetime import datetime 
from .models import (
    Course, CourseTerm, CourseCode, CourseNumber,
    CourseSection, CourseYear, CourseTime, CourseDay
)
from .models import Program, ProgramYearLevel

class CourseForm(forms.Form):
    # User inputs (required fields have asterisk in label)
    code = forms.CharField(max_length=20, required=True, label="Code *")
    number = forms.CharField(max_length=20, required=True, label="Number *")
    section = forms.CharField(max_length=20, required=True, label="Section *")
    term = forms.CharField(max_length=20, required=True, label="Term *")
    academic_year = forms.CharField(max_length=20, required=True, label="Academic Year *")

    # Optional fields
    day = forms.CharField(max_length=50, required=False, label="Day")            # e.g. "Monday_Tuesday"
    start_time = forms.CharField(max_length=20, required=False, label="Start")   # "HH:MM"
    end_time = forms.CharField(max_length=20, required=False, label="End")       # "HH:MM"

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end   = cleaned.get("end_time")

        # Only validate the order if both are provided
        if start and end:
            try:
                s_dt = datetime.strptime(start.strip(), "%H:%M")
            except ValueError:
                # should not come here
                self.add_error("start_time", "Use HH:MM (e.g., 08:00).")
                return cleaned

            try:
                e_dt = datetime.strptime(end.strip(), "%H:%M")
            except ValueError:
                # should not come here
                self.add_error("end_time", "Use HH:MM (e.g., 09:30).")
                return cleaned

            if not e_dt > s_dt:
                self.add_error("end_time", "End time must be later than start time.")

        return cleaned


    def save(self, instance: Course | None = None):
        """
        Create or update a Course by mapping the user strings to FK instances.
        """
        data = self.cleaned_data
        course = instance or Course()

        # Required FKs
        course.code, _ = CourseCode.objects.get_or_create(name=data["code"].strip())
        course.number, _ = CourseNumber.objects.get_or_create(name=data["number"].strip())
        course.section, _ = CourseSection.objects.get_or_create(name=data["section"].strip())
        course.term, _ = CourseTerm.objects.get_or_create(name=data["term"].strip())
        course.academic_year, _ = CourseYear.objects.get_or_create(name=data["academic_year"].strip())

        # Optional FKs
        if data.get("day"):
            course.day, _ = CourseDay.objects.get_or_create(name=data["day"].strip())
        else:
            course.day = None

        if data.get("start_time"):
            course.start_time, _ = CourseTime.objects.get_or_create(name=data["start_time"].strip())
        else:
            course.start_time = None

        if data.get("end_time"):
            course.end_time, _ = CourseTime.objects.get_or_create(name=data["end_time"].strip())
        else:
            course.end_time = None

        course.save()
        return course


class CourseTermForm(forms.ModelForm):
    class Meta:
        model = CourseTerm
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. T1"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        # enforce case-insensitive uniqueness
        qs = CourseTerm.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Term with this name already exists.")
        return name
    

class CourseCodeForm(forms.ModelForm):
    class Meta:
        model = CourseCode
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. LFS"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = CourseCode.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Code with this name already exists.")
        return name
    

class CourseNumberForm(forms.ModelForm):
    class Meta:
        model = CourseNumber
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 100"}),
        }

    def clean_name(self):
        raw = self.cleaned_data["name"].strip()
        if not raw.isdigit():
            raise forms.ValidationError("Course Number must contain digits only (e.g. 100).")
        qs = CourseNumber.objects.filter(name__exact=raw)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Number with this value already exists.")
        return raw


class CourseSectionForm(forms.ModelForm):
    class Meta:
        model = CourseSection
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 001"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = CourseSection.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Section with this value already exists.")
        return name
    

class CourseTimeForm(forms.ModelForm):
    class Meta:
        model = CourseTime
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),  # hidden via template; still needed for server
        }

    def clean_name(self):
        val = (self.cleaned_data.get("name") or "").strip()
        try:
            dt = datetime.strptime(val, "%H:%M")
            normalized = dt.strftime("%H:%M")
        except Exception:
            raise forms.ValidationError("Enter a valid time in HH:MM (e.g., 08:00).")

        qs = CourseTime.objects.filter(name__exact=normalized)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Time with this value already exists.")
        return normalized


class CourseDayForm(forms.Form):
    DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    DAY_CHOICES = [(d, d) for d in DAY_ORDER]

    # Render as horizontal checkboxes; the class helps us style in the template
    days = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "day-checks"}),
        required=True,
        label="Days",
        error_messages={  
            "required": "Please select at least one day."
        },
    )

    def __init__(self, *args, **kwargs):
        # current_name allows “no-op” edit without tripping uniqueness
        self.current_name = kwargs.pop("current_name", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        selected = cleaned.get("days", [])

        # If nothing selected, reinforce friendly message (covers edge cases)
        if not selected:
            return cleaned

        # Canonicalize order to Mon→Fri regardless of user click order
        order_index = {d: i for i, d in enumerate(self.DAY_ORDER)}
        selected_sorted = sorted(selected, key=lambda d: order_index[d])
        name = "_".join(selected_sorted)

        # Uniqueness (case-sensitive to match other settings forms)
        qs = CourseDay.objects.filter(name__exact=name)
        if self.current_name:
            qs = qs.exclude(name__exact=self.current_name)
        if qs.exists():
            self.add_error("days", "A Course Day with this value already exists.")

        cleaned["name"] = name
        return cleaned

YEAR_CHOICES = [(str(y), str(y)) for y in range(2024, 2043)]  # 2024..2042 inclusive
class CourseYearForm(forms.ModelForm):
    class Meta:
        model = CourseYear
        fields = ["name"]
        widgets = {
            "name": forms.Select(attrs={"class": "form-select"}, choices=YEAR_CHOICES),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = CourseYear.objects.filter(name__exact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A Course Year with this value already exists.")
        return name


class ProgramNameForm(forms.Form):
    name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Food Science"}),
        label="Program Name",
    )

    def __init__(self, *args, **kwargs):
        # optional: pass current_name when editing to allow “no-op” rename
        self.current_name = kwargs.pop("current_name", None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        new = self.cleaned_data["name"].strip()
        qs = Program.objects.filter(name__exact=new)
        if self.current_name:
            qs = qs.exclude(name__exact=self.current_name)
        if qs.exists():
            raise forms.ValidationError("A Program Name with this value already exists.")
        return new

