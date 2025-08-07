import pandas as pd
from django.core.management.base import BaseCommand
from scheduler.models import Course, CourseCode, CourseNumber, CourseTerm, CourseSection, CourseTime, CourseDay
from django.utils.text import slugify
from datetime import datetime, timedelta

def parse_term(term_str):
    if not pd.isna(term_str):
        if '&' in term_str:
            return "T1_T2"
        elif "1" in term_str:
            return "T1"
        elif "2" in term_str:
            return "T2"
        return term_str
    else:
        return "Unknown"

def parse_code_and_number(course_code):
    # Ex: LFS_V 101-D01
    
    if "GRS" in course_code:
        try:
            code, rest = course_code.split(' ', 1)
            number, section = rest.split(' ', 1)
            return number.strip(), section.strip()
        except Exception as e:
            print(f"Failed to parse course_code {course_code}: {e}")
            return None, None
    
    try:
        prefix, rest = course_code.split(' ', 1)
        code = prefix.split('_')[0]
        number = rest[0:3].strip()
        section = rest.split('-')[1]
        return number.strip(), section.strip()
    except Exception as e:
        print(f"Failed to parse course_code {course_code}: {e}")
        return None, None

def get_or_create_instance(model, name):
    obj, _ = model.objects.get_or_create(name=name)
    return obj

def parse_end_time(start_str, duration_str) -> str:
    '''Parse the end time from start time and duration'''
    if not start_str or pd.isna(start_str):
        return "Unknown"
    if not duration_str or pd.isna(duration_str):
        return "Unknown"

    try:
        start_time = datetime.strptime(start_str, "%H:%M")
        end_time = start_time  # Default to start time if parsing fails
        if "hr" in duration_str:
            if ".5" in duration_str:
                hours = int(duration_str.replace("hr", "").strip().split(".")[0])
                minutes = 30
            else:
                hours = int(duration_str.replace("hr", "").strip())
                minutes = 0
            delta = timedelta(hours=hours, minutes=minutes)
        elif "min" in duration_str:
            minutes = int(duration_str.replace("min", "").strip())
            delta = timedelta(minutes=minutes)
        else:
            delta = timedelta(hours=1)
        end_time = (start_time + delta).strftime("%H:%M")
        return end_time
    except Exception as e:
        print(f"Error parsing time: {start_str}, {duration_str}: {e}")
        return None

class Command(BaseCommand):
    help = 'Ingest courses from Excel file into the database'

    def handle(self, *args, **kwargs):    
        path = "../timetable/scheduler/course_data_xls/Course_Map_Raw_Data (1).xlsx"  # update if different
        xl = pd.ExcelFile(path)
        
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)

            for _, row in df.iterrows():
                full_code = row.get("Course Code", "")
                course_code = row.get("Subject", "")
                term = parse_term(row.get("Term", ""))
                days = row.get("Days", "")
                start = row.get("Start time", "")
                duration = row.get("Duration", "")
                
                if pd.isna(start):
                    continue

                number, section = parse_code_and_number(full_code)
                if not all([number, section, start]):
                    continue

                end = parse_end_time(start, duration)
                if isinstance(days, str):
                    day = days.replace(", ", "_")
                elif pd.isna(days):
                    day = "Unknown"
                else:
                    day = str(days).replace(", ", "_")

                print(f"Parsed Course - Code: {course_code}, Number: {number}, Section: {section}, Term: {term}, Day: {day}, Start: {start}, End: {end}")

                # Get or create related objects
                term_obj = get_or_create_instance(CourseTerm, term)
                code_obj = get_or_create_instance(CourseCode, course_code)
                number_obj = get_or_create_instance(CourseNumber, number)
                section_obj = get_or_create_instance(CourseSection, section)
                start_obj = get_or_create_instance(CourseTime, start)
                end_obj = get_or_create_instance(CourseTime, end)
                day_obj = get_or_create_instance(CourseDay, day)

                # Create course name and slug
                course_name = f"{course_code}-{number}-{section}-{term}"
                slug = slugify(course_name)

                # Create course if not exists
                Course.objects.get_or_create(
                    name=course_name,
                    slug=slug,
                    defaults={
                        'term': term_obj,
                        'code': code_obj,
                        'number': number_obj,
                        'section': section_obj,
                        'start': start_obj,
                        'end': end_obj,
                        'day': day_obj
                    }
                )

        print('✅ Course ingestion complete')