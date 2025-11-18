import pandas as pd
from django.core.management.base import BaseCommand
from scheduler.models import (
    Course, CourseCode, CourseNumber, CourseSection, CourseTerm,
    CourseDay, CourseTime, CourseYear, ProgramYearLevel, ProgramName, Program, Role, Profile
)
from datetime import datetime, timedelta
from django.contrib.auth.models import User
        
class Command(BaseCommand):
    help = "Ingest courses and program relationships from Excel file"
    
    # note: 
    # For example, a course held on Monday and Wednesday should be written as "Monday,Wednesday". 
    # For courses, format them as GRS_V 497B-001, 
    # use a space to separate the code and number, and a dash to separate the number and section.
    def handle(self, *args, **kwargs):
        path = "scheduler/source_data/Course Map Raw Data 2.xlsx" # change if needed
        xl = pd.ExcelFile(path)

        # # add roles
        admin_role, _ = Role.objects.get_or_create(name= "Admin")
        user_role, _ = Role.objects.get_or_create(name= "User")

        # # creat Learning centre staff profile
        # # 1. jhu32
        user1 = User.objects.create_user(
                    password=None,
                    username="jhu32",
                )
        Profile.objects.get_or_create(user= user1, role= admin_role)

        for sheet_name in xl.sheet_names:
            df = xl.parse(sheet_name)

            # --- 1. Ensure ProgramYearLevel 1–5 exist ---
            for lvl in range(1, 6):
                ProgramYearLevel.objects.get_or_create(name= f"Year {lvl}")

            # --- 2. Ensure ProgramName from header row (after 'Duration'), create ProgramName ---
            program_names = list(df.columns)[df.columns.get_loc("Duration") + 1 :]
            for pname in program_names:
                ProgramName.objects.get_or_create(name= pname)    

            # --- 3. Ensure CourseYear 2025 exists ---
            course_year_obj, _ = CourseYear.objects.get_or_create(name="2025")

            # --- 4. Ensure CourseDay (Monday - Friday) exist ---
            CourseDay.objects.get_or_create(name= "Mon")
            CourseDay.objects.get_or_create(name= "Tues")
            CourseDay.objects.get_or_create(name= "Wed")
            CourseDay.objects.get_or_create(name= "Thurs")
            CourseDay.objects.get_or_create(name= "Fri")

            # --- 5. Ensure CourseCode (LFS, GRS, FNH, APBI, FRE) exist ---
            CourseCode.objects.get_or_create(name= "APBI", color= "#2BB1D6")
            CourseCode.objects.get_or_create(name= "FNH", color= "#43D7C7")
            CourseCode.objects.get_or_create(name= "FRE", color= "#E47CC0")
            CourseCode.objects.get_or_create(name= "GRS", color= "#D2B64C")
            CourseCode.objects.get_or_create(name= "LFS", color= "#F46C63")

            # --- 6. Iterate through rows ---
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

                # Enforce time null if day is null
                start_obj, end_obj = None, None
                days_val=[]

                if not pd.isna(days) and days:
                    # Day exists
                    days_val = str(days).split(",")
                    DAY_SHORT = {
                                "Monday": "Mon",
                                "Tuesday": "Tues",
                                "Wednesday": "Wed",
                                "Thursday": "Thurs",
                                "Friday": "Fri",
                    }
                    def convert_days_to_short(days_val: str):
                        parts = [p.strip() for p in days_val]
                        return [DAY_SHORT.get(p, p) for p in parts]
                    days_val = convert_days_to_short(days_val)

                    # Only parse times if day exists
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
                        "start_time": start_obj,
                        "end_time": end_obj,
                    }
                )
                for day in days_val:
                    day_obj = CourseDay.objects.get(name=day.strip()) # Mon, etc
                    course.day.add(day_obj)

                # --- 7. create program, then link course to program ---
                for pname in program_names:
                    cell_val = row.get(pname, None)
                    if pd.isna(cell_val) or str(cell_val).strip() == "Not Required":
                        continue

                    level_obj = ProgramYearLevel.objects.get(name=cell_val.strip())  # "Year 1", "Year 2", etc.
                    program_name_obj = ProgramName.objects.get(name=pname) # AANB, etc
                    program, _ = Program.objects.get_or_create(name=program_name_obj, year_level=level_obj)
                    program.courses.add(course)

        self.stdout.write(self.style.SUCCESS("Ingestion complete"))
