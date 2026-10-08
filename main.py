import flet as ft
import time
import GeneticAlgorithm as ga


#stores app data while the program is running
class AppState:
    def __init__(self):
        self.subjects = []
        self.teachers = []
        self.students = []

        #Setting the default values for the constraints
        self.constraints = {
            "max_class_size": 30,
            "max_lessons_per_period": 4,
        }

        #Setting all soft constraints on as a default
        self.preferences = {
            "avoid_double_lessons": True,
            "avoid_triple_teacher": True,
            "avoid_triple_students": True,
            "avoid_empty_periods": True,
        }

        #Holding important settings for the genetic algorithm
        #These values are NOT to be edited
        self.settings = {
            "INITIAL_POP_SIZE": 200,
            "max_generations": 300,
            "required_fitness": 10000000,
            "max_run_time": 60,
            "convergence_generations": 25,
            "minimum_improvement": 100,
            "elitism_percent": 0.05,
            "mutation_rate": 0.1,
        }

        #Initialising variables to hold output data from the algorithm
        self.display_timetable = None
        self.classes = []
        self.summary = {}
        self.stop_reason = ""


#converts data from the Appstate into format expected by the genetic algorithm
def create_input_data(state):

    #raise value error if the user has not entered any subject, students or teachers
    if len(state.subjects) == 0:
        raise ValueError("no subjects added.")

    if len(state.teachers) == 0:
        raise ValueError("no teachers added.")

    if len(state.students) == 0:
        raise ValueError("no students added.")

    #master_teacher_dict allows lookup for the following:
    #teacher codes, teacher names and max lessons for each teacher
    master_teacher_dict = {}
    for code, teacher in enumerate(state.teachers, start=1):
        subject = teacher["subject"]

        #if the subject has already been added, then there are two teachers for one lesson
        #this would cause the algorithm not to function correctly, so a value error is raised
        if subject in master_teacher_dict:
            raise ValueError(f"more than one teacher assigned to '{subject}'.")

        master_teacher_dict[subject] = {
            "teacher_code": code,
            "teacher_name": teacher["name"],
        }

    #Checking that every subject has a teacher, if not a value error is raised
    for subject in state.subjects:
        if subject["name"] not in master_teacher_dict:
            raise ValueError(f"'{subject['name']}' does not have a teacher assigned to it.")

    #Building the master_student_dict
    #allows lookup for student codes and subjects for each student
    master_student_dict = {}
    for index, student in enumerate(state.students, start=1):
        master_student_dict[student["name"]] = {
            "student_code": index,
            "subjects": student["subjects"],
        }

    #---VALIDATION CHECKS PASSED---
    #If this point has been reached, there is sufficient data to run the algorithm
    num_lessons_dict = {}
    lesson_teacher_dict = {}
    lesson_student_dict = {}
    lesson_information_dict = {}

    lesson_code = 1

    #Building the main data structures for the algorithm
    for subject in state.subjects:
        name = subject["name"]
        code = subject["code"]
        lessons_per_week = int(subject["lessons_per_week"])
        
        teacher_information = master_teacher_dict[name]
        teacher_code = teacher_information["teacher_code"]
        teacher_name = teacher_information["teacher_name"]

        student_codes = []
        student_names = []

        #.items() returns a list of tuples containing (key, value) for each pair in the dict
        for student_name, student_information in master_student_dict.items():
            if name in student_information["subjects"]:
                student_codes.append(student_information["student_code"])
                student_names.append(student_name)

        num_lessons_dict[lesson_code] = lessons_per_week
        lesson_teacher_dict[lesson_code] = teacher_code
        lesson_student_dict[lesson_code] = student_codes

        #lesson_information_dict is used for display in the GUI
        lesson_information_dict[lesson_code] = {
            "subject_name": name,
            "subject_code": code,
            "teacher_code": teacher_code,
            "teacher_name": teacher_name,
            "student_codes": student_codes,
            "student_names": student_names,
            "lessons_per_week": lessons_per_week,
        }

        lesson_code = lesson_code + 1

    #Calculating the user's required number of lessons and the maximum that can fit given the constraints
    required_lessons = 0
    for value in num_lessons_dict.values():
        required_lessons = required_lessons + int(value)

    capacity = 48*int(state.constraints["max_lessons_per_period"])

    #If too many lessons have been requested, a value error is raised
    if required_lessons > capacity:
        raise ValueError(f"Too many lessons to fit in the timetable")

    return {
        "num_lessons_dict": num_lessons_dict,
        "lesson_teacher_dict": lesson_teacher_dict,
        "lesson_student_dict": lesson_student_dict,
        "lesson_information_dict": lesson_information_dict,
    }


#Function to run the genetic algorithm on the data in the AppState
def run_algorithm(state):
    #data is put into the correct format by create_input_data function
    data = create_input_data(state)

    #event_dict and event_lessons_to_code are initialised with default values for empty periods
    event_dict = {0: []}
    event_lessons_to_code = {(): 0}

    #preferences list is read from the AppState
    preferences = [
        bool(state.preferences["avoid_double_lessons"]),
        bool(state.preferences["avoid_triple_teacher"]),
        bool(state.preferences["avoid_triple_students"]),
        bool(state.preferences["avoid_empty_periods"]),
    ]

    #time when the algorithm started running is saved
    start = time.perf_counter()

    #---ALGORITHM IS RUN---
    final_timetable, generations_count, stop_reason = ga.run_genetic_algorithm(
        state.settings["INITIAL_POP_SIZE"],
        data["num_lessons_dict"],
        state.constraints["max_lessons_per_period"],
        event_dict,
        event_lessons_to_code,
        data["lesson_teacher_dict"],
        data["lesson_student_dict"],
        state.constraints["max_class_size"],
        preferences,
        state.settings["max_generations"],
        state.settings["required_fitness"],
        state.settings["max_run_time"],
        state.settings["convergence_generations"],
        state.settings["minimum_improvement"],
        state.settings["elitism_percent"],
        state.settings["mutation_rate"],
    )

    #The difference between when the algorithm started and finished is saved as the run time
    runtime = time.perf_counter() - start

    #hard violations within the timetable are counted
    #this will be displayed in the UI
    num_violations = ga.count_hard_violations(
        final_timetable,
        data["lesson_teacher_dict"],
        data["lesson_student_dict"],
        state.constraints["max_class_size"],
        event_dict,
    )

    #output dictionary is returned - provides fast lookup for key variables
    output = {
        "final_timetable": final_timetable,
        "event_dict": event_dict,
        "lesson_information_dict": data["lesson_information_dict"],
        "runtime": runtime,
        "num_violations": num_violations,
        "generations_count": generations_count,
        "stop_reason": stop_reason,
    }
    return output

def convert_timetable_for_display(output):
    #Data created by the algorithm is accessed via the 'output' dictionary
    final_timetable = output["final_timetable"]
    event_dict = output["event_dict"]
    lesson_information_dict = output["lesson_information_dict"]

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    #displayed_timetable will map Tuple(day, period) -> list[info for lessons on that day and period (see below...)]
    displayed_timetable = {}

    for index, event_code in enumerate(final_timetable.lessons):
        #using floor division (//) the correct day for each period is found
        #By dividing by the number of periods each day (8) and rounding down to the nearest whole number
        day = days[index // 8]
        #the period (out of 8) can be found by taking mod 8 and adding 1
        period = (index % 8) + 1

        #event_dict maps event codes -> lesson codes
        lesson_codes = event_dict[event_code]
        displayed_lessons = []

        #displayed_lessons is a list of f strings detailing each subjects' code and teacher name
        for code in lesson_codes:
            lesson_information = lesson_information_dict[code]
            displayed_lessons.append(f"{lesson_information['subject_code']} - {lesson_information['teacher_name']}")

        #info for each lesson in a given period is added to the displayed_timetable dictionary
        displayed_timetable[(day, period)] = displayed_lessons

    #subject details dictionary stores all key info on subjects
    subject_details = []
    for code, information in lesson_information_dict.items():
        subject_details.append(
            {"name": information["subject_name"],
             "code": information["subject_code"],
             "teacher": information["teacher_name"],
             "students": information["student_names"],
             "sessions_per_week": information["lessons_per_week"],
            }
        )

    #algorithm_details stores values from the output from the algorithm to be displayed in the UI (separately from the timetable)
    algorithm_details = {
        "fitness" : final_timetable.fitness,
        "generations" : output["generations_count"],
        "runtime" : f"{output['runtime']:.2f}s",
        "num_violations" : output["num_violations"],
        "stop_reason" : output["stop_reason"],
    }

    return displayed_timetable, subject_details, algorithm_details

#---main entry point for the program---
def main(page: ft.Page):
    page.title = "JYGSAW"
    page.window.full_screen = True
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.theme_mode = ft.ThemeMode.LIGHT

    state = AppState()

    #Defining the routing between both views (windows) of the program
    def route_change(e):
        page.views.clear()

        if page.route == "/":
            page.views.append(setup_view(page, state))
        elif page.route == "/timetable":
            page.views.append(timetable_view(page, state))

        page.update()

    page.on_route_change = route_change
    page.go("/")

#--Creating the timetable setup view--
def setup_view(page, state):
    #Initialising UI components, to be placed inside Cards
    subject_name_input = ft.TextField(label="Subject Name", width=250)
    subject_code_input = ft.TextField(label="Subject Code", width=180)
    subject_lessons_per_week_input = ft.TextField(label="Lessons per Week", width=180)
    teacher_name_input = ft.TextField(label="Teacher Name", width=250)
    teacher_subjects_input = ft.Dropdown(label="Subject Taught", width=250)
    student_name_input = ft.TextField(label="Student Name", width=250)

    #Where checkboxes to select student subjects will be displayed
    student_subjects_input_column = ft.Column(spacing=4)

    #Textfields for constraints and preferences card are instantiated
    max_class_size_input = ft.TextField(label="Max Class Size",
                                        value=str(state.constraints["max_class_size"]),
                                        width=180)
    max_lessons_per_period_input = ft.TextField(label="Max Lessons per Period",
                                                value=str(state.constraints["max_lessons_per_period"]),
                                                width=220)

    #All preferences switches are instantiated and turned on as a default
    avoid_double_lessons_switch = ft.Switch(label="Avoid double lessons",
                                            value=True,
                                            adaptive=True,)
    avoid_triple_teacher_switch = ft.Switch(label="Avoid triple lessons for teachers",
                                            value=True,
                                            adaptive=True,)
    avoid_triple_student_switch = ft.Switch(label="Avoid triple lessons for students",
                                            value=True,
                                            adaptive=True,)
    avoid_empty_periods_switch = ft.Switch(label="Avoid empty periods",
                                           value=True,
                                           adaptive=True,)

    #where inputted subjects/teachers/student will be displayed
    subjects_column = ft.Column(spacing=6)
    teachers_column = ft.Column(spacing=6)
    students_column = ft.Column(spacing=6)

    #where messages will be displayed to the user
    error_text = ft.Text("", color=ft.Colors.RED)

    #re-establishing the dropdown options for teacher subjects, based on data in the Appstate
    def refresh_teacher_dropdown():
         teacher_subjects_input.options = [
             ft.dropdown.Option(subject["name"]) for subject in state.subjects
         ]
    #re-establishing the inputted subjects column, based on data in the Appstate
    def refresh_subjects_column():
        subjects_column.controls.clear()

        for index, subject in enumerate(state.subjects):
            subjects_column.controls.append(
                ft.Container(
                    padding=8,
                    border=ft.border.all(1, ft.Colors.BLACK12),
                    border_radius=8,
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                f"{subject['code']} - {subject['name']} ({subject['lessons_per_week']}/week)",
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Delete subject",
                                on_click=lambda e, idx=index: remove_subject(idx),
                            ),
                        ]
                    ),
                )
            )

    # re-establishing the inputted teachers column, based on data in the Appstate
    def refresh_teachers_column():
        teachers_column.controls.clear()

        for index, teacher in enumerate(state.teachers):
            teachers_column.controls.append(
                ft.Container(
                    padding=8,
                    border=ft.border.all(1, ft.Colors.BLACK12),
                    border_radius=8,
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                f"{teacher['name']} - {teacher['subject']}",
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Delete teacher",
                                on_click=lambda e, idx=index: remove_teacher(idx),
                            ),
                        ]
                    ),
                )
            )

    #re-establishing the inputted teachers column, based on data in the Appstate
    def refresh_students_column():
        students_column.controls.clear()

        for index, student in enumerate(state.students):
            #.join adds the name of each subject the student is taking after a comma adn whitespace
            subject_text = ", ".join(student["subjects"])
            students_column.controls.append(
                ft.Container(
                    padding=8,
                    border=ft.border.all(1, ft.Colors.BLACK12),
                    border_radius=8,
                    content=ft.Row(
                        controls=[
                            ft.Text(
                               f"{student['name']} - {subject_text}",
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Delete student",
                                on_click=lambda e, idx=index: remove_student(idx),
                            )
                        ]
                    ),
                )
            )

    #re-establishing the options of checkboxes for student subjects, based on data in the Appstate
    def reload_subject_boxes():
        student_subjects_input_column.controls.clear()

        for subject in state.subjects:
            student_subjects_input_column.controls.append(
                ft.Checkbox(label=f"{subject['name']} ({subject['code']})"))

    #helper function to remove a subject and refresh relevant UI components to show the change
    def remove_subject(i):
        del state.subjects[i]
        refresh_subjects_column()
        refresh_teacher_dropdown()
        reload_subject_boxes()
        page.update()

    # helper function to remove a teacher and refresh relevant UI components to show the change
    def remove_teacher(i):
        del state.teachers[i]
        refresh_teachers_column()
        page.update()

    # helper function to remove a student and refresh relevant UI components to show the change
    def remove_student(i):
        del state.students[i]
        refresh_students_column()
        page.update()

    #Function to validate the input of a name
    def validate_name(input_text):
        if not input_text:
            return False
        #.stripped() is used to remove whitespaces
        stripped_text = input_text.strip()

        if len(stripped_text) == 0:
            return False
        if len(stripped_text) > 40:
            return False

        #Checking for invalid characters (full stops, blank spaces, hyphens and apostrophes are allowed)
        for char in input_text:
            #.isalnum() returns True if all characters are alphanumeric
            #i.e. letters (a-z) or numbers (0-9), so no emojis/other characters
            if not char.isalnum() and char not in [" ", ".", "-", "'"]:
                return False

        return True

    #Function to check if a data input is a valid integer
    def validate_integer(input_num):
        if input_num.isdigit() and int(input_num) > 0:
            return True
        else:
            return False

    #Event handler for clicking 'add subject'
    def add_subject(e):
        #Values for subject name, code and number of lessons are read from their respective text fields
        subject_name = subject_name_input.value.strip()
        subject_code = subject_code_input.value.strip()
        num_subject_lessons = subject_lessons_per_week_input.value.strip()

        #if the name input is not valid, an error message is displayed and the function is exited
        if not validate_name(subject_name):
            error_text.value = "Enter a valid subject name (1-40 characters)"
            page.update()
            return

        #if the code input is not valid, an error message is displayed and the function is exited
        if not validate_integer(subject_code):
            error_text.value = "Enter a valid subject code"
            page.update()
            return

        #if the number of lessons per week input is not valid, an error message is displayed and the function is exited
        if not validate_integer(num_subject_lessons):
            error_text.value = "Subject lessons per week should be a positive integer."
            page.update()
            return

        #if the subject name input already exists for another subject, an error message is displayed and the function is exited
        for subject in state.subjects:
            if subject["name"].lower() == subject_name.lower():
                error_text.value = "That subject already exists."
                page.update()
                return
            # if the subject code input already exists for another subject, an error message is displayed and the function is exited
            if subject["code"].lower() == subject_code.lower():
                error_text.value = "That subject code already exists."
                page.update()
                return

        #---BY THIS POINT, VALIDATION CHECKS HAVE BEEN PASSED---
        state.subjects.append(
            {
                "name": subject_name,
                "code": subject_code,
                "lessons_per_week": num_subject_lessons,
            }
        )

        #text field inputs are cleared
        subject_name_input.value = ""
        subject_code_input.value = ""
        subject_lessons_per_week_input.value = ""

        #UI components are refreshed and the page updated
        refresh_subjects_column()
        refresh_teacher_dropdown()
        reload_subject_boxes()
        page.update()

    #Event handler for clicking 'Add Teacher'
    def add_teacher(e):
        teacher_name = teacher_name_input.value.strip()
        teacher_subject = (teacher_subjects_input.value or "").strip()

        #if the teacher name input is not valid, an error message is displayed and the function is exited
        if not validate_name(teacher_name):
            error_text.value = "Enter a valid teacher name (1-40 characters)"
            page.update()
            return

        #if no teacher subject has been selected from the dropdown, an error message is displayed and the function is exited
        if not teacher_subject:
            error_text.value = "Select a teacher subject."
            page.update()
            return

        # ---BY THIS POINT, VALIDATION CHECKS HAVE BEEN PASSED---
        state.teachers.append(
            {
                "name": teacher_name,
                "subject": teacher_subject,
            }
        )

        #input fields are cleared of any value
        teacher_name_input.value = ""
        teacher_subjects_input.value = None
        error_text.value = ""

        #the teachers column is refreshed and the page is updated to show the addition of the teacher
        refresh_teachers_column()
        page.update()

    #Event handler for clicking 'Add Student'
    def add_student(e):
        student_name = student_name_input.value.strip()

        #if the student name input is not valid, an error message is displayed and the function is exited
        if not validate_name(student_name):
            error_text.value = "Enter a valid student name (1-40 characters)"
            page.update()
            return

        #names of subjects are read from the labels of selected checkboxes in the student_subjects_input_column
        chosen_subjects = []
        for checkbox in student_subjects_input_column.controls:
            if checkbox.value:
                #.split() splits a string into a two part list about the specified point
                subject_name = checkbox.label.split(" (")[0] #This extracts just the subject name from the checkbox label
                chosen_subjects.append(subject_name)

        #If the user has not selected 3-5 subjects from the checkboxes, an error message is displayed and the function is exited
        if not 3 <= len(chosen_subjects) <= 5:
            error_text.value = "Each student must have between 3 - 5 subjects."
            page.update()
            return

        #---BY THIS POINT, VALIDATION CHECKS HAVE BEEN PASSED---
        state.students.append(
            {
                "name": student_name,
                "subjects": chosen_subjects,
            }
        )

        #UI components are cleared
        student_name_input.value = ""
        for checkbox in student_subjects_input_column.controls:
            checkbox.value = False
        error_text.value = ""

        #The UI is updated to show the addition of the student
        refresh_students_column()
        page.update()

    #Event handler for clicking 'Save Constraints'
    def save_constraints(e):
        #if the max class size input is not valid, an error message is displayed and the function is exited
        if not validate_integer(max_class_size_input.value.strip()):
            error_text.value = "Max class size must be a positive integer."
            page.update()
            return

        #if the max lessons per period input is not valid, an error message is displayed and the function is exited
        if not validate_integer(max_lessons_per_period_input.value.strip()):
            error_text.value = "Max lessons per period must be a positive integer."
            page.update()
            return

        #---BY THIS POINT, VALIDATION CHECKS HAVE BEEN PASSED---
        #Appstate is updated with new input data
        state.constraints["max_class_size"] = int(max_class_size_input.value.strip())
        state.constraints["max_lessons_per_period"] = int(max_lessons_per_period_input.value.strip())

        state.preferences["avoid_double_lessons"] = avoid_double_lessons_switch.value
        state.preferences["avoid_triple_teacher"] = avoid_triple_teacher_switch.value
        state.preferences["avoid_triple_student"] = avoid_triple_student_switch.value
        state.preferences["avoid_empty_periods"] = avoid_empty_periods_switch.value

        #The UI is updated, to indicate to the user that the constraints and preferences were saved successfully
        error_text.value = "Constraints and preferences saved."
        page.update()

    #Event handler for clicking 'generate timetable'
    def generate_timetable(e):
        save_constraints(None)

        #Do not generate a timetable if the last input was not valid
        #This prevents the algorithm from running on bad data
        if error_text.value not in ("", "Constraints and preferences saved."):
            return


        try:
            #Updating the UI, so the user knows that the algorithm is running
            error_text.value = "Running genetic algorithm..."
            page.update()

            #Running the algorithm on data in the Appstate
            algorithm_output = run_algorithm(state)

            #Updating the Appstate with data from the algorithm, so it can be displayed
            state.display_timetable, state.classes, state.summary = (
                convert_timetable_for_display(algorithm_output)
            )
            state.stop_reason = algorithm_output["stop_reason"]

            #Removes any error messages and navigates to the timetable display view
            error_text.value = ""
            page.go("/timetable")

        #exect prevents the program from crashing if an error occurs running the algorithm
        except Exception as ex:
            # Any error that occurs is displayed as error text to the user
            error_text.value=str(ex) #ex variable is an exception object, so must be converted to a string using str()
            page.update()

    #---BY THIS POINT, THE ALGORITHM HAS RUN SUCCESSFULLY---

    #Left part of the setup view (JYGSAW title + instruction text) UI is created using a container
    left_side = ft.Container(
        width=210,
        bgcolor=ft.Colors.GREY_200,
        padding=12,
        content=ft.Column(
            controls=[
                ft.Text("JYGSAW", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Setup", size=16),
                ft.Divider(),
                ft.Text("1. Subjects"),
                ft.Text("2. Teachers"),
                ft.Text("3. Students"),
                ft.Text("4. Constraints"),
                ft.Text("5. Preferences"),
                ft.Divider(),
                ft.FilledButton(
                    "Generate Timetable",
                    icon=ft.Icons.AUTO_AWESOME,
                    on_click=generate_timetable,
                    width=180,
                ),
            ],
            spacing=10,
        ),
    )

    #Right part of the setup view (scrollable, where data input occurs) is created using a container
    #This container holds 'Cards' which hold the previously defined data input components - text fields, dropdowns, checkboxes and switches
    right_side = ft.Container(
        expand=True,
        padding=20,
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text("Timetable Setup", size=26, weight=ft.FontWeight.BOLD),
                error_text,
                ft.Card(
                    content=ft.Container(
                        padding=15,
                        content=ft.Column(
                            controls=[
                                ft.Text("Subjects", size=22, weight=ft.FontWeight.BOLD),
                                ft.ResponsiveRow(
                                    controls=[
                                        subject_name_input,
                                        subject_code_input,
                                        subject_lessons_per_week_input,
                                    ]
                                ),
                                ft.ElevatedButton("Add Subject", on_click=add_subject),
                                subjects_column,
                            ],
                            spacing=10,
                        ),
                    )
                ),
                ft.Card(
                    content=ft.Container(
                        padding=15,
                        content=ft.Column(
                            controls=[
                                ft.Text("Teachers", size=22, weight=ft.FontWeight.BOLD),
                                ft.ResponsiveRow(
                                    controls=[
                                        teacher_name_input,
                                        teacher_subjects_input,
                                    ]
                                ),
                                ft.ElevatedButton("Add Teacher", on_click=add_teacher),
                                teachers_column,
                            ],
                            spacing=10,
                        ),
                    )
                ),
                ft.Card(
                    content=ft.Container(
                        padding=15,
                        content=ft.Column(
                            controls=[
                                ft.Text("Students", size=22, weight=ft.FontWeight.BOLD),
                                student_name_input,
                                ft.Text("Select 3 to 5 subjects:"),
                                student_subjects_input_column,
                                ft.ElevatedButton("Add Student", on_click=add_student),
                                students_column,
                            ],
                            spacing=10,
                        ),
                    )
                ),
                ft.Card(
                    content=ft.Container(
                        padding=15,
                        content=ft.Column(
                            controls=[
                                ft.Text("Constraints", size=22, weight=ft.FontWeight.BOLD),
                                ft.ResponsiveRow(
                                    controls=[
                                        max_class_size_input,
                                        max_lessons_per_period_input,
                                    ]
                                ),
                                ft.Text("Soft Constraint Preferences", size=18, weight=ft.FontWeight.W_500),
                                ft.Column(
                                    controls=[
                                        avoid_double_lessons_switch,
                                        avoid_triple_teacher_switch,
                                        avoid_triple_student_switch,
                                        avoid_empty_periods_switch,
                                    ],
                                    spacing=6,
                                ),
                                ft.ElevatedButton(
                                    "Save Constraints", on_click=save_constraints
                                ),
                            ],
                            spacing=10,
                        ),
                    )
                ),
            ],
        )
    )

    #All UI components are refreshed, to show up-to-date data from the Appstate
    refresh_subjects_column()
    refresh_teachers_column()
    refresh_students_column()
    refresh_teacher_dropdown()
    reload_subject_boxes()

    #The setup view is returned
    return ft.View(
        "/",
        controls=[
            ft.Row(
                controls=[
                    left_side, right_side,
                ],
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.START
            )
        ],
    )

def create_timetable_display(state):
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    periods = range(1,9)

    #Colours to be used for each coloured brick (period) in the timetable
    colours = [
        ft.Colors.BLUE_200,
        ft.Colors.GREEN_200,
        ft.Colors.ORANGE_200,
        ft.Colors.PURPLE_200,
        ft.Colors.PINK_200,
        ft.Colors.TEAL_200,
        ft.Colors.CYAN_200,
        ft.Colors.AMBER_200,
        ft.Colors.LIME_200,
        ft.Colors.INDIGO_200,
    ]

    #Each subject is assigned a colour, which corresponds to its code
    subject_colours = {} #subject_colours maps subject code -> colour
    for index, subject in enumerate(state.subjects):
        subject_colours.update({subject["code"]: colours[index % len(colours)]})

    rows = []

    #A container is created to hold the labels for each day in the timetable (mon, tues, etc...)
    headers = [
        ft.Container(
            width=70,
            height=40,
            alignment=ft.alignment.center,
            content=ft.Text("Period", weight=ft.FontWeight.BOLD),
        )
    ]


    #For each day (Mon-Sat) a header is created to display what day each row of the timetable corresponds to
    for day in days:
        headers.append(
            ft.Container(
                width=120,
                height=40,
                bgcolor=ft.Colors.GREY_300,
                border=ft.border.all(1, ft.Colors.BLACK12),
                border_radius=8,
                alignment=ft.alignment.center,
                content=ft.Text(day, weight=ft.FontWeight.BOLD),
            )
        )

    rows.append(ft.Row(controls=headers, spacing=6))

    #Containers are created to display numbers down the side of the timetable for each period (1-8)
    for period in periods:
        row_slots = [
            ft.Container(
                width=70,
                height=70,
                alignment=ft.alignment.center,
                content=ft.Text(str(period), weight=ft.FontWeight.BOLD)
            )
        ]


        for day in days:
            # the lessons on each day are retrieved from the display_timetable dictionary
            # .get() returns [], if there is no lesson for a given day and period
            day_lessons = state.display_timetable.get((day, period), [])


            if day_lessons:
                #colour code is assigned based on the lessons' codes
                colour_code = day_lessons[0].split(" - ")[0]
                #if no subject in the period, background colour is GREY_200
                background_colour = subject_colours.get(colour_code, ft.Colors.GREY_200)

                #Lesson controls holds ft.Text() elements for each lesson name/code to  be displayed
                lesson_controls = []
                for lesson in day_lessons:
                    lesson_controls.append(
                        ft.Text(lesson, size=11, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_500)
                    )

                slot = ft.Container(
                    width=120,
                    height=70,
                    bgcolor=background_colour,
                    border=ft.border.all(1, ft.Colors.BLACK12),
                    border_radius=10,
                    padding=6,
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        controls=lesson_controls,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                )
            else:
                slot = ft.Container(
                    width=120,
                    height=70,
                    bgcolor=ft.Colors.GREY_100,
                    border=ft.border.all(1, ft.Colors.BLACK12),
                    border_radius=10,
                    alignment=ft.alignment.center,
                    content=ft.Text("-", color=ft.Colors.GREY_200),
                )

            row_slots.append(slot)

        rows.append(ft.Row(controls=row_slots, spacing=6))

    #reutrn a column containing the rows of created containers/periods that form the timetable
    return ft.Column(controls=rows, spacing=6)

#Function to create the expansion tiles used to display class lists in the UI
def create_class_lists_display(state):
    expansion_tiles = []

    #an expansion tile is created for each lesson - featuring a subtitle containing its code, teacher and number of students
    #
    for lesson in state.classes:
        subtitle = f"{lesson['code']} - {lesson['teacher']} ({len(lesson['students'])} students)"
        expansion_tiles.append(
            ft.ExpansionTile(
                title=ft.Text(f"{lesson['name']}"),
                subtitle=ft.Text(subtitle, size=12),
                #each students' name is inside the expansion tile as a text component
                controls=[ft.Text(student) for student in lesson['students']],
            )
        )

    #A column featuring all created expansion tiles is returned
    return ft.Column(
        controls=expansion_tiles,
        scroll=ft.ScrollMode.AUTO,
        width=320,
    )


def timetable_view(page, state):
    timetable_grid = create_timetable_display(state)
    class_lists_display = create_class_lists_display(state)

    #Event handler for clicking 'Go back'
    def go_back(e):
        page.go("/")

    #creating the 'top bar' component of the timetable view, where algorithm data and the title are displayed
    #The 'back to setup' button is also within the topbar
    top_bar = ft.Row(
        controls=[
            ft.Text("Generated Timetable", size=24, weight=ft.FontWeight.BOLD),
            ft.ElevatedButton("Back to Setup", on_click=go_back),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    #algorithm data is read from the Appstate,to be displayed in the UI
    algorithm_info = ft.Text(
        f"Fitness: {state.summary.get('fitness')}   "
        f"Generations: {state.summary.get('generations')}   "
        f"Runtime: {state.summary.get('runtime')}   "
        f"Hard Violation: {state.summary.get('num_violations')}   "
        f"Stop Reason: {state.summary.get('stop_reason')}"
    )

    return ft.View(
        "/timetable",
        controls=[
            ft.Column(
                controls=[
                    top_bar,
                    algorithm_info,
                    ft.Row(
                        controls=[
                            timetable_grid,
                            class_lists_display,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        expand=True,
                    ),
                ],
                expand=True
            )
        ]
    )


ft.app(target=main)