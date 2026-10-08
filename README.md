# JYGSAW — Genetic Algorithm Timetabling

**JYGSAW** is a Python application I developed for my OCR A-level Computer Science programming project. It uses a genetic algorithm to generate a school timetable based on the lessons, teachers and students entered by the user.

The aim was to investigate whether software could make a time-consuming timetabling task easier, while allowing the user to set constraints and view the resulting timetable in a graphical interface.

## How it works

The program represents a timetable as 48 lesson periods (six days with eight periods per day). It starts with a population of randomly generated timetables and evaluates them using a fitness score. Selection, crossover and mutation produce new candidate timetables. The algorithm also uses a repair function to preserve the required lesson counts.

The fitness calculation penalizes **hard constraints**, such as double-booking a teacher or student or exceeding the maximum class size. The user can also choose **preferences**, such as avoiding consecutive double lessons, three consecutive lessons for teachers or students, and empty periods.

The desktop interface is written using [Flet](https://flet.dev/). Users can enter subjects, assign teachers, select students' subjects, set the constraints and generate a timetable. Results are displayed in a timetable grid alongside summary information from the algorithm.

## Running the project

The original development environment used Python 3.9 and Flet 0.28.3.

1. Install Python 3 and create a virtual environment (recommended).
2. Install the dependencies: `pip install -r requirements.txt`
3. Run: `python main.py`

A graphical desktop environment is required to launch the Flet interface. Compatibility with newer Flet releases has not been verified.

## Files

- `main.py` — user interface, data input and validation, and timetable display
- `GeneticAlgorithm.py` — timetable representation, fitness evaluation, crossover, mutation, repair and optimization loop
- `assets/JYGSAW_Icon.png` — original project icon

## Background and limitations

I designed the project around the needs of school timetabling. My NEA work included an analysis of existing solutions, a stakeholder interview, design decisions and iterative testing. This repository contains the original Python application and a short explanation rather than the full assessment report.

This is an A-level project, not a finished commercial scheduling system. It uses a fixed 48-period week, and the optimization algorithm may find a satisfactory solution without finding the global optimum. Results depend on the data and constraints supplied.

## Development

**Author:** Ethan West  
**Project:** OCR A-level Computer Science NEA (2025–2026)
