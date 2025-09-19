import pandas as pd
from django.core.management.base import BaseCommand
from scheduler.models import (
    Course, CourseCode, CourseNumber, CourseSection, CourseTerm,
    CourseDay, CourseTime, CourseYear, ProgramYearLevel, ProgramName, Program
)
from django.utils.text import slugify
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = "Ingest courses and program relationships from Excel file"

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
            for pname in program_names:
                ProgramName.objects.get_or_create(name=pname.strip())

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
                    num_section = full_code.split(" ")[1]  # e.g. "100-001"
                    number, section = num_section.split("-")
                except Exception:
                    number, section = "Unknown", "Unknown"


                code_obj, _ = CourseCode.objects.get_or_create(name=subject.strip())
                number_obj, _ = CourseNumber.objects.get_or_create(name=number.strip())
                section_obj, _ = CourseSection.objects.get_or_create(name=section.strip())

                # Parse day + enforce time null if day is null
                day_obj, start_obj, end_obj = None, None, None

                if not pd.isna(days) and days:
                    # Day exists → create CourseDay
                    day_val = str(days).strip()
                    day_obj, _ = CourseDay.objects.get_or_create(name=day_val)

                    # Only parse times if day is valid
                    if start_str and not pd.isna(start_str):
                        start_val = str(start_str).strip()
                        try:
                            start_time = datetime.strptime(start_val, "%H:%M")
                            if duration_str and "hr" in duration_str:
                                hours = float(duration_str.replace("hr", "").strip())
                                delta = timedelta(hours=hours)
                            elif duration_str and "min" in duration_str:
                                minutes = int(duration_str.replace("min", "").strip())
                                delta = timedelta(minutes=minutes)
                            else:
                                delta = timedelta(hours=1)
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

                    pname_obj = ProgramName.objects.get(name=pname.strip())
                    level_obj = ProgramYearLevel.objects.get(name=cell_val.strip())  # "Year 1", "Year 2", etc.
                    program, _ = Program.objects.get_or_create(name=pname_obj, year_level=level_obj)
                    program.courses.add(course)

        self.stdout.write(self.style.SUCCESS("Ingestion complete"))
