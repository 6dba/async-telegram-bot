from aiogram.dispatcher.filters.state import State, StatesGroup

class DataState(StatesGroup):

    wait_drug_name = State() # done

    wait_course_taking = State() # done

    wait_course_taken = State() # done

    wait_inday = State() # done

    wait_dose = State() # done

    wait_utc = State() # done

    wait_time = State() # done

    wait_choose = State() # done

    wait_note = State() # done

    edit_time = State() # done

    edit_note = State() # done
    
    edit_utc = State() # done

    menu_exec = State() # done