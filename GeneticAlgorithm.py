import random, copy, time


# Genetic Algorithm for the optimisation of timetables
class timetable():
    def __init__(self, lessons, fitness):
        self.lessons = lessons
        self.fitness = fitness

    # class method to evaluate the fitness of a function and then assign this value as the timetable class attribute, fitness
    def get_fitness(self, lesson_teacher_dict, lesson_student_dict, max_class_size, event_dict, preferences,
                    updated_weights=None):

        max_fitness = 10000000
        total_penalty = 0

        weights = {
            "Hard Violation": 5000,
            "Soft Violation": 20,
            "Empty Period": 10
        }

        # changing the weights of penalties if necessary
        if updated_weights != None:
            weights = updated_weights

        # lesson_list is a list of tuples containing the lessons occuring in each event/period
        lesson_list = []  # expected length 48

        for code in self.lessons:
            lesson_list.append(tuple(event_dict[code]))

        # --HARD CONSTRAINT 1: Teacher Double Booking--
        for event in lesson_list:  # check each event for the same teacher teaching twice
            teachers = []
            for lesson in event:
                teacher = lesson_teacher_dict[lesson]  # lesson_teacher_dict maps lesson codes to teacher codes
                teachers.append(teacher)

            seen = set()
            for teacher in teachers:
                if teacher in seen:
                    total_penalty = total_penalty + weights["Hard Violation"]
                else:
                    seen.add(teacher)

        # --HARD CONSTRAINT 2: Student Double Booking--
        for event in lesson_list:
            seen = set()
            for lesson in event:
                for student in lesson_student_dict[lesson]:
                    if student in seen:
                        total_penalty = total_penalty + weights["Hard Violation"]
                    else:
                        seen.add(student)

        # --HARD CONSTRAINT 3: Max Class Size Exceeded--
        for event in lesson_list:
            for lesson in event:
                num_students = len(lesson_student_dict[lesson])
                if num_students > max_class_size:
                    total_penalty = total_penalty + weights["Hard Violation"]

        if preferences[0]:
            # --SOFT CONSTRAINT 1: Avoid Double Lessons--
            i = 0
            j = 1
            while j <= 47:  # total length of timetable in periods/event = 48, so last index is 47
                if (i + 1) % 8 == 0:  # if i is the last period of the day, do not penalise across days
                    i = i + 1
                    j = j + 1
                    continue
                for lesson in lesson_list[i]:
                    if lesson in lesson_list[j]:
                        total_penalty = total_penalty + weights["Soft Violation"]
                i = i + 1
                j = j + 1

        if preferences[1]:
            # --SOFT CONSTRAINT 2: Avoid Triple Lessons For Teachers--
            teachers = []  # expected length 48
            for event in lesson_list:
                period = set()
                for lesson in event:
                    teacher = lesson_teacher_dict[lesson]  # lesson_teacher_dict maps lesson code -> teacher code
                    # creating a set of teachers teaching in each period
                    period.add(teacher)
                teachers.append(period)
            for i in range(46):
                if (i + 2) % 8 in (0, 1):
                    continue
                # find the intersection between sets of teachers teaching three consecutive periods
                period1 = teachers[i]
                period2 = teachers[i + 1]
                period3 = teachers[i + 2]
                num_tripple_bookings = len(period1.intersection(period2, period3))
                # the length of the reulting set is the number of teachers that are tripple booked
                total_penalty = total_penalty + num_tripple_bookings * weights["Soft Violation"]

        if preferences[2]:
            # --SOFT CONSTRAINT 3: Avoid Triple Lessons For Students--
            students = []
            for event in lesson_list:
                period = set()
                for lesson in event:
                    period.update(lesson_student_dict[lesson])
                students.append(period)
            for i in range(46):
                if (i + 2) % 8 in (0, 1):
                    continue
                period1 = students[i]
                period2 = students[i + 1]
                period3 = students[i + 2]
                num_tripple_bookings = len(period1.intersection(period2, period3))
                total_penalty = total_penalty + weights["Soft Violation"] * num_tripple_bookings

        if preferences[3]:
            # --SOFT CONSTRAINT 4: Avoid Empty periods--
            num_empty_penalty = 0
            for event in lesson_list:
                # an empty event in the lesson list appears as an empty tuple ()
                if len(event) == 0:
                    num_empty_penalty = num_empty_penalty + 1

            total_penalty = total_penalty + weights["Empty Period"] * num_empty_penalty

        # subtract the total penalty from the maximum fitness to get the timetable's fitness score
        max_fitness -= total_penalty
        if max_fitness < 0:
            self.fitness = 0
        else:
            self.fitness = max_fitness

    # class method to perform crossover between two timetables
    def crossover(self, timetable_B, num_lessonsDict, event_dict, event_lessons_to_code, maxLessons_perPeriod):
        first = self.lessons
        second = timetable_B.lessons
        # if either lesson list has somehow not ended up being of length 48, then a random timetable is returned
        if len(first) != 48 or len(second) != 48:
            return generate_random_timetable(num_lessonsDict, maxLessons_perPeriod, event_dict, event_lessons_to_code)

        # the child timetable is produced as a result of combining the first half of one parent's lessons with the second half of the other parent's lessons
        random_num = random.randint(1, 46)
        new_list = first[:random_num] + second[random_num:]
        return repair(timetable(new_list, 0), num_lessonsDict, event_dict, event_lessons_to_code, maxLessons_perPeriod)


class event():
    def __init__(self, code, event_lessons):
        self.code = code
        self.event_lessons = event_lessons

    # class method for event class to create a new event and update the relevant data structures
    @classmethod
    def create_event(self, lesson_list, event_dict, event_lessons_to_code):
        # sort each lesson list, so identical events are treated the same
        # i.e. [6, 8] is not different to [8, 6] for this representation
        key = tuple(sorted(lesson_list))

        # if the desired event already exists, it can be returned
        if key in event_lessons_to_code:
            return event_lessons_to_code[key]

        # otherwise a new event is create
        max_value = max(event_dict.keys(), default=0)  # default=0 is given to prevent a crash in the instance len(event_dict) = 0
        event_code = max_value + 1
        event_dict[event_code] = list(key)  # update event_dict with the new event
        event_lessons_to_code[key] = event_code

        return event_code


# function to sort a population of timetables in descending fitness
def sort_population(population):
    new_population = []

    for timetable in population:
        inserted = False
        index = 0
        # walk through new population to find a place to insert
        while index < len(new_population):
            if timetable.fitness > new_population[index].fitness:
                # insert before current item
                new_population = new_population[:index] + [timetable] + new_population[index:]
                inserted = True
                break
            else:
                index = index + 1

        if not inserted:
            new_population.append(timetable)

    return new_population


# function to select the fittest timetable from random groups of size three
def tournament_selection(sorted_pop):
    # randomising the order of the timetables
    random_pop = sorted_pop[:]
    random.shuffle(random_pop)
    tournament_pop = []

    # tournament_pop will be a list, of lists, of size three - containing the groups for the tournament
    # if any timetables are leftover, they will be placed into a tournament of less than three timetables
    i = 0
    n = len(random_pop)
    while i < n:
        tournament_pop.append(random_pop[i:i + 3])
        i = i + 3

    winners_pop = []

    for tournament in tournament_pop:
        winner = sort_population(tournament)  # each tournament is sorted by fitness
        # the timetables are in order of descending fitness, so the timetable at index 0 is the winner of the tournament
        winners_pop.append(winner[0])

    return winners_pop


# function to perform crossover between tournament selection winning timetables
def crossover_pop(population, num_lessonsDict, event_dict, event_lessons_to_code, maxLessons_perPeriod):
    new_pop = []
    i = 0
    n = len(population)
    while i < n - 1:
        first_half = population[i]
        second_half = population[i + 1]
        new_timetable = first_half.crossover(second_half, num_lessonsDict, event_dict, event_lessons_to_code,
                                             maxLessons_perPeriod)
        new_pop.append(new_timetable)
        i = i + 2
    if n % 2 == 1:
        new_pop.append(population[n - 1])

    return new_pop


# function to perform mutation to a timetable
def mutation(timetable, num_lessonsDict, event_dict, event_lessons_to_code, maxLessons_perPeriod):
    # random lessons are selected from the 1st and 2nd half of the timetable
    i = random.randint(0, 23)
    j = random.randint(24, 47)

    # create a deep copy to avoid editing the original across multiple places
    new_timetable = copy.deepcopy(timetable)

    # lessons are swapped using a temporary value
    temp = new_timetable.lessons[i]
    new_timetable.lessons[i] = new_timetable.lessons[j]
    new_timetable.lessons[j] = temp
    return repair(new_timetable, num_lessonsDict, event_dict, event_lessons_to_code, maxLessons_perPeriod)


# function to select timetables for mutation
def select_for_mutation(population, num_lessonsDict, event_dict, event_lessons_to_code, maxLessons_perPeriod, rate):
    # initial mutation rate set to 5%
    if rate == None:
        rate = 0.05

    new_population = []
    # walking through each timetable to apply a 5% chance of mutation
    for timetable in population:
        # random.random() produces a random floating point value between 1 and 0
        if rate > random.random():
            # mutation occurs via the separate mutation function
            new_population.append(
                mutation(timetable, num_lessonsDict, event_dict, event_lessons_to_code, maxLessons_perPeriod))
        else:
            new_population.append(timetable)

    return new_population


# function to repair damage done to timetable during crossover/mutation (restores correct number of each lesson)
def repair(timetable, num_lessonsDict, event_dict, event_lessons_to_code, maxLessons_perPeriod):
    # first, build the dictionary occurrences, of the form {lesson code[int] : List[Tuple(event_index, lesson_index), ...]}
    occurrences = {}

    for event_index, event_code in enumerate(timetable.lessons):
        for lesson_index, lesson in enumerate(event_dict[event_code]):
            # updates the occurrences dict with where lessons are, indexes required to address each lesson stored as tuple
            # .setdefault() method adds a new lesson to the dictionary if the lesson is not already present
            occurrences.setdefault(lesson, []).append((event_index, lesson_index))

            # stores the key-value pairs in the numLessons_dict as tuples in a list
    # numLessons_dict maps lesson codes -> number of lessons required per week
    requirements_tuples = list(num_lessonsDict.items())

    # remove surplus lessons
    for lesson, required in requirements_tuples:
        # compute current number of each lesson
        current = len(occurrences.get(lesson, []))
        if current > required:
            surplus = current - required
            removed = random.sample(occurrences[lesson], surplus)
            for event_index, lesson_index in removed:
                # change the event code in the lesson list to a different event without the lesson that is to be removed
                event_code = timetable.lessons[event_index]
                event_lessons = list(event_dict[event_code])

                if lesson not in event_lessons:
                    continue

                # remove one occurance of the lesson
                event_lessons.remove(lesson)
                # create new event code for this set of lessons
                new_code = event.create_event(event_lessons, event_dict, event_lessons_to_code)
                # assign new code to the lessons attribute
                timetable.lessons[event_index] = new_code

    occurrences = {}
    # identify the updated occurrences of lessons after the removal of surplus lessons
    for event_index, event_code in enumerate(timetable.lessons):
        for lesson_index, lesson in enumerate(event_dict[event_code]):
            occurrences.setdefault(lesson, []).append((event_index, lesson_index))

            # empty_slots keeps track of where the empty lesson slots are in the timetable once lessons have been removed
    empty_slots = []

    # build empty_slots
    for index, code in enumerate(timetable.lessons):
        if len(event_dict[code]) == 0:  # event_dict maps code -> lessons and an empty event has [] lessons
            empty_slots.append(index)

    # insert lessons that are at a deficit into the timetable
    for lesson, required in requirements_tuples:
        # find the current number of the lesson in the timetable
        current = len(occurrences.get(lesson, []))
        # if there is no deficit, then move onto the next iteration of the for loop
        if current >= required:
            continue
        # the deficit in lessons is the difference between the current and required totals
        # if we have got to this point then we know that there is a deficit because of the if statement above
        deficit = required - current

        # we want to use up all existing empty slots first before adding new lesson slots
        # the smaller value between empty slots availiable and the total lessons to be added is the maximum number of empty slots that can be filled
        # i.e. we fill all of the empty slots that we can now, then deal with any remaining lessons to be added after
        num_replacements = min(deficit, len(empty_slots))
        # only enter this block of code if there are empty_slots availiable
        if len(empty_slots) > 0:
            # .sample() guarantees unique slots are chosen, no repeats
            replacement_slots = random.sample(empty_slots, num_replacements)
            for event_index in replacement_slots:
                event_code = timetable.lessons[event_index]
                new_event = event.create_event([lesson], event_dict, event_lessons_to_code)
                timetable.lessons[event_index] = new_event
                empty_slots.remove(event_index)
                deficit = deficit - 1

        # if the lesson cannot be inserted into an existing empty slot, we create a new slot for that lesson
        # this is done by randomly selecting an event and adding the lessons to the event if it does not already appear in this event
        sample_list = list(range(0, 48))
        while deficit > 0 and sample_list != []:
            trial_index = random.choice(sample_list)
            event_code = timetable.lessons[trial_index]
            # event lessons is made a copy using list() - so as to not edit the global event defenition
            event_lessons = list(event_dict[event_code])
            # if the lesson is already present at the index, or the event is full to the max number of lessons, the lesson must be placed elsewhere
            if lesson in event_lessons or len(event_lessons) >= maxLessons_perPeriod:
                sample_list.remove(trial_index)
            else:
                # if it is possible to add the lesson, then a new event can be created featuring the new lesson
                event_lessons.append(lesson)
                new_event = event.create_event(event_lessons, event_dict, event_lessons_to_code)
                timetable.lessons[trial_index] = new_event
                # update the occurences dictionary after adding a lesson successfully
                occurrences.setdefault(lesson, []).append((trial_index, len(event_lessons) - 1))
                deficit = deficit - 1

    return timetable


# function to create a random timetable with the correct number of each lesson type
def generate_random_timetable(num_lessonsDict, maxLessons_perPeriod, event_dict, event_lessons_to_code):
    # num_lessonsDict is a dictionary of the form {lessons code: number of lesson each week}
    # create a copy of num_lessonsDict, so as to not modify the original
    lesson_occurences = num_lessonsDict.copy()

    # this will form the 'lessons' class attribute of the timetable that is instantiated by the function (i.e. eventually a list of 48 event codes)
    lessons = [[] for _ in range(48)]

    # if a lesson/key in lesson_occurences has a value zero, it needs to be added zero times, so can be removed from the dictionary
    for key in list(lesson_occurences.keys()):
        if lesson_occurences[key] == 0:
            lesson_occurences.pop(key)  # remove any lessons from the dictionary that do not need to be added

    while lesson_occurences != {}:

        # can select a random lesson to add from lesson_occurences, as there are no lessons in this dict that do not need to be added/have a value of zero
        lesson_to_add = random.choice(list(lesson_occurences))

        # add the randomly selected lesson to a slot that does not already contain too many lessons
        possible_indexes = []
        for event_index, lesson_list in enumerate(lessons):
            if len(lesson_list) < maxLessons_perPeriod:
                possible_indexes.append(event_index)

        # select a random index from the ones which are possible to add to
        chosen_index = random.choice(possible_indexes)
        lessons[chosen_index].append(lesson_to_add)
        lesson_occurences[lesson_to_add] -= 1
        if lesson_occurences[lesson_to_add] == 0:
            lesson_occurences.pop(lesson_to_add)

    # convert 2D list of lesson codes to a 1D list of event codes
    lesson_list_to_return = []
    for event_lessons in lessons:
        event_code = event.create_event(event_lessons, event_dict, event_lessons_to_code)
        lesson_list_to_return.append(event_code)

    # instanciate the timetable object with the randomly generated events/lessons
    return timetable(lesson_list_to_return, 0)


def run_genetic_algorithm(INITIAL_POP_SIZE, num_lessonsDict, maxLessons_perPeriod, event_dict, event_lessons_to_code,
                          lesson_teacher_dict,
                          lesson_student_dict, max_class_size, preferences, max_generations, required_fitness,
                          max_run_time,
                          convergence_generations, minimum_improvement, elitism_percent, mutation_rate=None):
    initial_population = []
    pop_size = INITIAL_POP_SIZE
    # initialise the population with 200 random timetables
    while pop_size != 0:
        random_timetable = generate_random_timetable(num_lessonsDict, maxLessons_perPeriod, event_dict,
                                                     event_lessons_to_code)
        initial_population.append(random_timetable)
        pop_size = pop_size - 1

    population = initial_population
    generations_count = 0
    fittest_timetables = []
    stop_reason = ""

    start = time.perf_counter()  # start parameter equals the time since the GA started running
    while True:
        # time-based stop as fails-safe measure, so the algorithm cannot run forever
        if time.perf_counter() - start >= max_run_time:
            stop_reason = "time-based stop"
            break

        # evaluate fitness for each timetable in the population
        for timetable in population:
            timetable.get_fitness(lesson_teacher_dict, lesson_student_dict, max_class_size, event_dict, preferences)

        # compute highest and average fitness of timetables in the population
        population = sort_population(population)
        fittest_timetable = population[0]
        total_fitness = 0
        for timetable in population:
            total_fitness += timetable.fitness
        average_fitness = total_fitness / len(population)
        print(f"Generation {generations_count}:\nHighest Fitness ~ {fittest_timetable.fitness}\nAverage Fitness ~ {average_fitness}")

        # check if the fittest timetable has hit the required fitness threshold
        if fittest_timetable.fitness >= required_fitness:
            if count_hard_violations(fittest_timetable, lesson_teacher_dict, lesson_student_dict, max_class_size, event_dict) == 0:
                stop_reason = "required fitness reached"
            break

        # check to see if the maximum number of generations have occured
        if generations_count >= max_generations:
            stop_reason = "max generations reached"
            break

        # check to see if convergence has occured (population has become too similar and fitness is not improving) after a number of generations have occured
        fittest_timetables.append(fittest_timetable.fitness)
        # allow a number of generations to pass before convergence is tested for
        if len(fittest_timetables) > convergence_generations:
            # if the highest fitness timetable has not improved by a suitable amount for N generations, then the algorithm can be stopped
            if fittest_timetables[-1] - fittest_timetables[-convergence_generations] <= minimum_improvement:
                stop_reason = "convergence detected"
                break

        # --STOPPING CONDITIONS HAVE NOT BEEN MET--
        # by this point, another generation of the algorithm will occur as none of the conditions for stopping the algorithm have been met

        # select best timetables to move directly into the next generation as part of elitism
        num_elite_timetables = int(INITIAL_POP_SIZE * elitism_percent)
        elite_timetables = population[:num_elite_timetables]
        remaining_population = population[num_elite_timetables:]

        # tournament selection occurs, to select timetables for crossover
        tournament_winners = tournament_selection(remaining_population)

        # crossover occurs among the timetables that won their respective tournaments
        crossed_over_pop = crossover_pop(tournament_winners, num_lessonsDict, event_dict, event_lessons_to_code,
                                         maxLessons_perPeriod)

        # a small percent of the timetables are mutated, to promote diversity
        mutated_pop = select_for_mutation(crossed_over_pop, num_lessonsDict, event_dict, event_lessons_to_code,
                                          maxLessons_perPeriod, mutation_rate)

        # fill up the population with randomly generated timetables
        current_pop_size = len(mutated_pop) + len(elite_timetables)
        num_required_timetables = INITIAL_POP_SIZE - current_pop_size
        random_timetables = []
        while num_required_timetables != 0:
            random_timetable = generate_random_timetable(num_lessonsDict, maxLessons_perPeriod, event_dict,
                                                         event_lessons_to_code)
            random_timetables.append(random_timetable)
            num_required_timetables -= 1

        population = elite_timetables + mutated_pop + random_timetables
        generations_count += 1

    print(stop_reason)
    # final fitness evaluation before best timetable reached is returned
    for timetable in population:
        timetable.get_fitness(lesson_teacher_dict, lesson_student_dict, max_class_size, event_dict, preferences)

    final_timetable = sort_population(population)[0]

    return final_timetable, generations_count, stop_reason

def count_hard_violations(timetable, lesson_teacher_dict, lesson_student_dict, max_class_size, event_dict):

    hard_violations_count = 0

    # lesson_list is a list of tuples containing the lessons occuring in each event/period
    lesson_list = []  # expected length 48

    for code in timetable.lessons:
        lesson_list.append(tuple(event_dict[code]))

    # --HARD CONSTRAINT 1: Teacher Double Booking--
    for event in lesson_list:  # check each event for the same teacher teaching twice
        teachers = []
        for lesson in event:
            teacher = lesson_teacher_dict[lesson]  # lesson_teacher_dict maps lesson codes to teacher codes
            teachers.append(teacher)

        seen = set()
        for teacher in teachers:
            if teacher in seen:
                hard_violations_count += 1
            else:
                seen.add(teacher)

    # --HARD CONSTRAINT 2: Student Double Booking--
    for event in lesson_list:
        seen = set()
        for lesson in event:
            for student in lesson_student_dict[lesson]:
                if student in seen:
                    hard_violations_count += 1
                else:
                    seen.add(student)

    # --HARD CONSTRAINT 3: Max Class Size Exceeded--
    for event in lesson_list:
        for lesson in event:
            num_students = len(lesson_student_dict[lesson])
            if num_students > max_class_size:
                hard_violations_count += 1

    return hard_violations_count