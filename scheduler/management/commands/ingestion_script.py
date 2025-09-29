import pandas as pd
from django.core.management.base import BaseCommand
from scheduler.models import (
    Course, CourseCode, CourseNumber, CourseSection, CourseTerm,
    CourseDay, CourseTime, CourseYear, ProgramYearLevel, Program
)
from datetime import datetime, timedelta

def normalize_days(raw):
        if raw == "Mon":
            return "Monday"
        elif raw == "Wed":
            return "Wednesday"
        elif raw == "Fri":
            return "Friday"
        elif raw == "Mon, Wed, Fri":
            return "Monday_Wednesday_Friday"
        elif raw == "Tue, Thurs":
            return "Tuesday_Thursday"
        elif raw == "Thurs":
            return "Thursday"
        elif raw == "Tues, Thurs":
            return "Tuesday_Thursday"
        elif raw == "M, W, F":
            return "Monday_Wednesday_Friday"
        elif raw == "T, TH":
            return "Tuesday_Thursday"
        elif raw == "MWF":
            return "Monday_Wednesday_Friday"
        elif raw == "Tue Thur":
            return "Tuesday_Thursday"
        elif raw == "Mon, Fri":
            return "Monday_Friday"
        elif raw == "Wed, Fri":
            return "Wednesday_Friday"
        elif raw == "Tue, Thur":
            return "Tuesday_Thursday"
        elif raw == "Wednesday":
            return "Wednesday"
        elif raw == "Thursday":
            return "Thursday"
        elif raw == "Mon, Wed":
            return "Monday_Wednesday"
        elif raw == "Friday":
            return "Friday"
        elif raw == "Mon.":
            return "Monday"
        elif raw == "Monday":
            return "Monday"
        elif raw == "Tue Thurs":
            return "Tuesday_Thursday"
        elif raw == "Tue, Thus":
            return "Tuesday_Thursday"
        elif raw == "Mon, Tues, Wed, Thurs, Fri":
            return "Monday_Tuesday_Wednesday_Thursday_Friday"
        elif raw == "Tu Th":
            return "Tuesday_Thursday"
        elif raw == "Mon Wed":
            return "Monday_Wednesday"
        elif raw == "M W":
            return "Monday_Wednesday"
        elif raw == "Tue Thu":
            return "Tuesday_Thursday"
        elif raw == "Tu Thu":
            return "Tuesday_Thursday"
        elif raw == "W":
            return "Wednesday"
        elif raw == "Tue":
            return "Tuesday"
        else:
            # add nee checking if needed
            return raw
        
class Command(BaseCommand):
    help = "Ingest courses and program relationships from Excel file"
    
    # note: 
    # For the course day, use the format "Monday_Wednesday" 
    # (spell out the full day names and separate them with a comma). 
    # For example, a course held on Monday and Wednesday should be written as "Monday,Wednesday". 
    # For courses, format them as GRS_V 497B-001, 
    # use a space to separate the code and number, and a dash to separate the number and section.
    def handle(self, *args, **kwargs):
        path = "scheduler/source_data/Course Map Raw Data 2.xlsx" # change if needed
        xl = pd.ExcelFile(path)

        for sheet_name in xl.sheet_names:
            df = xl.parse(sheet_name)

            # --- 1. Ensure ProgramYearLevel 1–5 exist ---
            for lvl in range(1, 6):
                ProgramYearLevel.objects.get_or_create(name= f"Year {lvl}")

            # --- 2. Ensure ProgramName from header row (after 'Duration') ---
            program_names = list(df.columns)[df.columns.get_loc("Duration") + 1 :]

            # --- 3. Ensure CourseYear 2025 exists ---
            course_year_obj, _ = CourseYear.objects.get_or_create(name="2025")

            # --- 4. Iterate through rows ---
            for _, row in df.iterrows():
                subject = row.get("Subject", "")
                full_code = row.get("Course Code", "")
                term_str = row.get("Term", "")
                days = row.get("Days", None)
                start_str = row.get("Start time", None)
                duration_str = row.get("Duration", None)

                # Parse course term
                if pd.isna(term_str):
                    #Skip courses with section XMT 
                    continue
                elif "&" in term_str:
                    term_val = "T1_T2"
                elif "1" in term_str:
                    term_val = "T1"
                elif "2" in term_str:
                    term_val = "T2"
                else:
                    # for future, if include summer term
                    term_val = str(term_str)

                term_obj, _ = CourseTerm.objects.get_or_create(name=term_val)

                # Parse number + section
                try:
                    parts = full_code.split(" ")  # e.g. "100-001"
                    num_section = parts[1]
                    number, section = num_section.split("-")
                except Exception:
                    # should not come here
                    number, section = "Unknown", "Unknown"


                code_obj, _ = CourseCode.objects.get_or_create(name=subject.strip())
                number_obj, _ = CourseNumber.objects.get_or_create(name=number.strip())
                section_obj, _ = CourseSection.objects.get_or_create(name=section.strip())

                # Parse day + enforce time null if day is null
                day_obj, start_obj, end_obj = None, None, None

                if not pd.isna(days) and days:
                    # Day exists → create CourseDay
                    # although "Monday,Friday", I change it to "Monday_Friday"
                    day_val = str(days).strip().replace(",", "_")
                    day_obj, _ = CourseDay.objects.get_or_create(name=day_val)

                    # Only parse times if day is valid
                    if start_str and not pd.isna(start_str):
                        start_val = str(start_str).strip()
                        try:
                            start_time = datetime.strptime(start_val, "%H:%M")
                            if duration_str and "hr" in duration_str:
                                hours = float(duration_str.replace("hrs", "").replace("hr", "").strip())
                                delta = timedelta(hours=hours)
                            end_time = (start_time + delta).strftime("%H:%M")
                        except Exception:
                            end_time = None

                        start_obj, _ = CourseTime.objects.get_or_create(name=start_val)
                        if end_time:
                            end_obj, _ = CourseTime.objects.get_or_create(name=end_time)

                # Build Course
                course, _ = Course.objects.get_or_create(
                    code=code_obj,
                    number=number_obj,
                    section=section_obj,
                    academic_year=course_year_obj,
                    term=term_obj,
                    defaults={
                        "day": day_obj,
                        "start_time": start_obj,
                        "end_time": end_obj,
                    }
                )

                # --- 5. Link course to programs ---
                for pname in program_names:
                    cell_val = row.get(pname, None)
                    if pd.isna(cell_val) or str(cell_val).strip() == "Not Required":
                        continue

                    level_obj = ProgramYearLevel.objects.get(name=cell_val.strip())  # "Year 1", "Year 2", etc.
                    program, _ = Program.objects.get_or_create(name=pname.strip(), year_level=level_obj)
                    program.courses.add(course)

        self.stdout.write(self.style.SUCCESS("Ingestion complete"))
