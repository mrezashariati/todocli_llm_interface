from dotenv import load_dotenv

load_dotenv()
import json
import subprocess
import shutil
import os
from pathlib import Path
import logging
import requests
from difflib import SequenceMatcher
import inspect
import re
from collections import defaultdict
import time

from langchain_utils import OpenWeatherMapAPIWrapper, LLAMA2

from langchain.agents import AgentExecutor, Tool, create_json_chat_agent
from langchain.prompts.prompt import PromptTemplate

import numpy as np

from app_utils import get_user_confirmation, set_raw_llm_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        # logging.StreamHandler()
    ],
)

OPENWEATHERMAP_API_KEY = os.environ["OPENWEATHERMAP_API_KEY"]
execution_queue = []
confirmation_mechanism_enabled = True

with open("./base_prompt.txt", "r") as f:
    BASE_PROMPT = f.read()


def process_bash_output(o):
    # Remove ANSI escape characters
    ansi_escape_pattern = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")
    o = ansi_escape_pattern.sub("", o)
    return o


def log_and_exec_process(command, func_name):
    logging.info(f"running command: {command}")

    p = subprocess.run(["bash", "-c", command], capture_output=True, text=True)
    # logging.info(f"{func_name} finished")
    output = process_bash_output(p.stdout)
    if output:
        # logging.info(
        #     f"command output:\n-----\n{output}\n-----",
        # )
        return output


def get_tasks_data():
    tasks_data = defaultdict(dict)
    tasks_flat_list = ""
    temp_str = todo_search("", is_done=False)
    if temp_str:
        tasks_flat_list += temp_str
    temp_str = todo_search("", is_done=True)
    if temp_str:
        tasks_flat_list += temp_str
    tasks_history = todo_history()

    # Parse todo --flat output
    pattern = re.compile(
        # r"^\s(\w+)\s+\|\s+([^★#]+)(?:★(\d+))?\s?(?:#(\w+))?",
        r"^\s(\w+)\s+\|\s+(\[DONE\])?([^★#\U0000231b\n]+)(?:\U0000231b[^★#]+)?(?:★(\d+))?\s?(?:#(\w+))?",
        re.MULTILINE,
    )
    for i, match in enumerate(pattern.finditer(tasks_flat_list)):
        id = match.group(1)
        tasks_data[id]["sort_by"] = i
        tasks_data[id]["priority"] = match.group(4)
        tasks_data[id]["context"] = match.group(5)
        tasks_data[id]["title"] = match.group(3).strip()

    # Parse todo --history output
    lines = tasks_history.strip().split("\n")
    if not lines == ["No history."]:
        header_line = lines[1]  ## This line contains the dashes under the headers
        ## Find all start and end indices of '-' sections to determine column boundaries
        field_bounds = []
        last_pos = 0
        while True:
            start = header_line.find("-", last_pos)
            if start == -1:
                break
            end = header_line.find(" ", start)
            if end == -1:
                end = len(header_line)
            field_bounds.append((start, end))
            last_pos = end

        ## Parse each data line using the detected field boundaries
        for line in lines[2:]:  # Skip headers and dashes line
            id = line[field_bounds[0][0] : field_bounds[0][1]].strip()
            # tasks_data[id]["created"] = line[
            #     field_bounds[2][0] : field_bounds[2][1]
            # ].strip()
            if len(field_bounds) > 4:
                tasks_data[id]["status"] = line[
                    field_bounds[4][0] : field_bounds[4][1]
                ].strip()
            if not tasks_data[id]["status"]:
                tasks_data[id]["status"] = "UNDONE"

    # Format the result
    tasks_data = [{"id": key, **value} for key, value in tasks_data.items()]
    return json.dumps(tasks_data)


def todo_list(context="", flat=False, tidy=False):
    """
    Print the list of the tasks based on the context and formatted flat or tidy.

    Parameters:
        context (str, optional): The path of the context the task belongs to. It's a sequence of strings separated by dots where each string indicate the name of a context in the contexts hierarchy.
        flat (bool, optional): Whether to list subcontexts below tasks (False) or integrate tasks of subcontexts with general tasks (True). Defaults to False.
        tidy (bool, optional): Alternative way to specify whether to list subcontexts below tasks (False) or integrate tasks of subcontexts with general tasks (True). Defaults to False.

    Returns:
        None
    """
    command = f"todo"
    if context:
        command += f""" \"{context}\""""
    if flat or tidy:
        command += " --flat" if flat else "--tidy"

    result = log_and_exec_process(command, "todo")

    return result


def todo_add(
    title,
    ask_confirmation=False,
    deadline=None,
    start=None,
    context=None,
    priority=1,
    depends_on=None,
    period=None,
    front=False,
):
    """
    Add a task with the specified options.

    Parameters:
        title (str): The title of the task.
        deadline (str): Deadline for the task. MOMENT can be a specific moment in time, in the following format: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, YYYY-MM-DDTHH:MM:SS. It can also be a delay, such as 2w which means "2 weeks from now". Other accepted characters are s, m, h, d, w, which respectively correspond to seconds, minutes, hours, days and weeks. An integer must preeced the letter. Defaults to None.
        start (str): Time at which the task starts. MOMENT can be a specific moment in time, in the following format: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, YYYY-MM-DDTHH:MM:SS. It can also be a delay, such as 2w which means "2 weeks from now". Other accepted characters are s, m, h, d, w, which respectively correspond to seconds, minutes, hours, days and weeks. An integer must preeced the letter. Defaults to None.
        context (str): The path of the context the task belongs to. It's a sequence of strings separated by dots where each string indicate the name of a context in the contexts hierarchy. Defaults to None.
        priority (int): Priority of the task. Defaults to 1. The highest the integer the highest the priority.
        depends_on (list of str): List of task IDs this task depends on. Defaults to None.
        period (str): Period for recurring tasks, such as 2w which means "2 weeks from now". Other accepted characters are s, m, h, d, w, which respectively correspond to seconds, minutes, hours, days and weeks. An integer must preeced the letter. Defaults to None.
        front (bool): Whether to set the task as a front task. Sometimes, you want a specific task in a specific context to always appear on the main todo listing, as it would with the --flat display, but while keeping other tasks tidied in their context. Defaults to False.

    Returns:
        None
    """
    command = f"""todo add \"{title}\""""
    if deadline:
        command += f""" --deadline \"{deadline}\""""
    if start:
        command += f""" --start \"{start}\""""
    if context:
        command += f""" --context \"{context}\""""
    if priority:
        command += f" --priority {priority}"
    if depends_on:
        command += " --depends-on"
        for dep in depends_on:
            command += f" {dep}"
    if period:
        command += f" --period {period}"
    if front:
        command += " --front"

    log_and_exec_process(command, "todo_add")


def todo_mark_as_done(ids):
    """
    Set tasks identified by IDs as done.

    Parameters:
        ids (list of str): List of task IDs to mark as done.

    Returns:
        None
    """

    ids_int = []
    # Convert a single string into a list with lenght one.
    if type(ids) == str:
        ids = [ids]
    for task_name in ids:
        task_id = get_task_id(task_name)
        if task_id:
            ids_int.append(str(task_id))
    if ids_int:
        command = f"todo done {' '.join(ids_int)}"

        log_and_exec_process(command, "todo_mark_as_done")


def todo_task(
    id,
    deadline=None,
    start=None,
    context=None,
    priority=None,
    title=None,
    depends_on=None,
    period=None,
    front=None,
):
    """
    Edit the specified task with the given options or print its contents.

    Parameters:
        id (str): ID of the task to edit or print.
        deadline (str): New deadline for the task. Defaults to None.
        start (str): New start time for the task. Defaults to None.
        context (str): The New path of the context the task belongs to. Defaults to None.
        priority (int): New priority for the task. Defaults to None.
        title (str): New title for the task. Defaults to None.
        depends_on (list of str): New list of task IDs this task depends on. Defaults to None.
        period (str): New period for recurring tasks. Defaults to None.
        front (bool): New front status for the task. Defaults to None.

    Returns:
        None
    """
    id = get_task_id(id)
    if not id:
        return

    command = f"todo task {id}"
    if deadline:
        command += f""" --deadline \"{deadline}\""""
    if start:
        command += f""" --start \"{start}\""""
    if context:
        command += f""" --context \"{context}\""""
    if priority:
        command += f" --priority {priority}"
    if title:
        command += f""" --title \"{title}\""""
    if depends_on:
        command += " --depends-on"
        for dep in depends_on:
            command += f" {dep}"
    if period:
        command += f" --period {period}"
    if front is not None:
        command += f" --front {'true' if front else 'false'}"

    return log_and_exec_process(command, "todo_task")


def todo_history():
    """
    Print the list of all tasks sorted by creation date, along with their properties.

    Returns:
        None
    """

    command = "todo history"

    return log_and_exec_process(command, "todo_history")


def todo_search(
    term, is_done=True, context=None, before=None, after=None, case_sensitive=False
):
    """
    Search for tasks whose title contains the substring <term> based on the specified criteria.

    Parameters:
        term (str): Search term.
        context (str): Context for the search. Defaults to None.
        is_done (bool): Whether to search for done tasks. Defaults to True.
        before (str): Limit search to tasks created before this moment. MOMENT can be a specific moment in time, in the following format: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, YYYY-MM-DDTHH:MM:SS. It can also be a delay, such as 2w which means "2 weeks from now". Other accepted characters are s, m, h, d, w, which respectively correspond to seconds, minutes, hours, days and weeks. An integer must preeced the letter. Defaults to None.
        after (str): Limit search to tasks created after this moment. MOMENT can be a specific moment in time, in the following format: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, YYYY-MM-DDTHH:MM:SS. It can also be a delay, such as 2w which means "2 weeks from now". Other accepted characters are s, m, h, d, w, which respectively correspond to seconds, minutes, hours, days and weeks. An integer must preeced the letter. Defaults to None.
        case_sensitive (bool): Whether the search is case sensitive. Defaults to False.

    Returns:
        None
    """
    command = f"todo search '{term}'"
    if context:
        command += f""" --context \"{context}\""""
    if is_done:
        command += " --done"
    else:
        command += " --undone"
    if before:
        command += f" --before {before}"
    if after:
        command += f" --after {after}"
    if case_sensitive:
        command += " --case"

    return log_and_exec_process(command, "todo_search")


def todo_rm(ids):
    """
    Remove tasks identified by the specified IDs.

    Parameters:
        ids (list of str): List of task IDs to remove.

    Returns:
        None
    """

    ids_int = []
    # Convert a single string into a list with lenght one.
    if type(ids) == str:
        ids = [ids]
    for task_name in ids:
        task_id = get_task_id(task_name)
        if task_id:
            ids_int.append(str(task_id))
    if ids_int:
        command = f"todo rm {' '.join(ids_int)}"

        log_and_exec_process(command, "todo_rm")


def todo_ping(ids):
    """
    Increment the ping counter of the given tasks. The ping counter is the second-to-last criterion used to rank tasks, having precedence over the added date. By default, tasks have a ping of 0, and whenever you use the ping command on a task, its ping counter is increased by one. The idea is that whenever you are reminded of the need of a pending task, you "ping" it, organically increasing its importance in comparison to other tasks.

    Parameters:
        ids (list of str): List of task IDs to ping.

    Returns:
        None
    """
    command = f"todo ping {' '.join(ids)}"

    log_and_exec_process(command, "todo_ping")


def todo_purge(force=False, before=None):
    """
    Remove done tasks from history created before the specified moment.

    Parameters:
        force (bool): Whether to force removal without confirmation. Defaults to False.
        before (str): Moment,  before which to remove tasks. Defaults to None.

    Returns:
        None
    """
    command = "todo purge"
    if force:
        command += " --force"
    if before:
        command += f" --before {before}"

    log_and_exec_process(command, "todo_purge")


def todo_edit_ctx(
    context, flat=False, tidy=False, priority=None, visibility=None, name=None
):
    """
    Manipulate contexts.

    Parameters:
        context (str): The context to manipulate.
        flat (bool): Whether to list subcontexts below tasks (False) or integrate tasks of subcontexts with general tasks (True). Defaults to False.
        tidy (bool): Alternative way to specify whether to list subcontexts below tasks (False) or integrate tasks of subcontexts with general tasks (True). Defaults to False.
        priority (int): New priority for the context. Defaults to None.
        visibility (str): New visibility setting for the context. Contexts have a visibility which is either normal or hidden. Hidden contexts aren't shown when using todo on their parent context. However, they still exists and their tasks can be seen as regular contexts by doing todo <context>. Defaults to None.
        name (str): New name for the context. An error is printed if the new name contains a dot or if the destination context already exists. Defaults to None.

    Returns:
        None
    """
    command = f"""todo ctx \"{context}\""""
    if flat or tidy:
        command += "--flat" if flat else "--tidy"
    if priority is not None:
        command += f" --priority {priority}"
    if visibility:
        command += f" --visibility {visibility}"
    if name:
        command += f" --name '{name}'"

    log_and_exec_process(command, "todo_edit_ctx")


def todo_mv(source_ctx, destination_ctx):
    """
    Move all tasks and subcontexts from source context to destination context.

    Parameters:
        source_ctx (str): Source context.
        destination_ctx (str): Destination context.

    Returns:
        None
    """
    command = f"todo mv '{source_ctx}' '{destination_ctx}'"

    log_and_exec_process(command, "todo_mv")


def todo_rmctx(context, force=True):
    """
    Remove a context and its contents recursively.

    Parameters:
        context (str): The context to be removed.
        force (bool): Whether to force removal without confirmation. Defaults to False.

    Returns:
        None
    """
    command = f"""todo rmctx \"{context}\""""
    if force:
        command += " --force"

    log_and_exec_process(command, "todo_rmctx")


def todo_future():
    """
    Show tasks that have not yet started.

    Parameters:
        None

    Returns:
        None
    """
    command = "todo future"

    return log_and_exec_process(command, "todo_future")


def todo_location():
    """
    Print the path of the data directory.

    Parameters:
        None

    Returns:
        None
    """

    command = "todo --location"

    return log_and_exec_process(command, "todo_location")


functions_dict = {
    "todo_list": todo_list,
    "todo_add": todo_add,
    "todo_edit_ctx": todo_edit_ctx,
    "todo_mark_as_done": todo_mark_as_done,
    "todo_future": todo_future,
    "todo_history": todo_history,
    "todo_location": todo_location,
    "todo_mv": todo_mv,
    "todo_ping": todo_ping,
    "todo_purge": todo_purge,
    "todo_rm": todo_rm,
    "todo_rmctx": todo_rmctx,
    "todo_search": todo_search,
    "todo_task": todo_task,
}


def empty_execution_queue():
    global execution_queue
    execution_queue = []


def parse_llm_output_and_populate_commands(text):
    global functions_dict
    global execution_queue
    execution_queue = []
    try:
        processed = text.split("<JSON>")[1].split("</JSON>")[0].strip()
    except Exception as e:
        logging.info("Bad LLM response structure.")
        return

    # correct some common mistakes in json formatting
    # Replace 'True' with 'true' and 'False' with 'false'
    processed = re.sub(r"\bTrue\b", "true", processed)
    processed = re.sub(r"\bFalse\b", "false", processed)

    # Replace "None" with "null"
    processed = re.sub(r"None", "null", processed)

    # changes the formatting of datetime to the specified format
    processed = standardize_date_format(processed)
    processed = json.loads(processed)

    confirmation_needed = False
    confirmation_message = "It seems your are going to participate in an outdoor activity and the weather condition is not suitable. I recommend to reschedule your task. Are you sure you want to add the task anyway?"

    for f in processed:
        func = (
            functions_dict[f["function"]] if f["function"] in functions_dict else None
        )
        if func:
            llm_named_args = list(f["parameters"].keys())
            actual_named_args = inspect.getfullargspec(func).args
            matching = string_matcher(llm_named_args, actual_named_args)
            func_params = {matching[k]: val for k, val in f["parameters"].items()}
            if "ask_confirmation" in func_params and func_params["ask_confirmation"]:
                # TODO: add weather check to log message
                confirmation_needed = True
                # confirmation_message += f["log"] + "\n"
            execution_queue.append((func, func_params, f.get("log", "")))

    if confirmation_needed and confirmation_mechanism_enabled:
        # first callback: confiremd, second callback: not confirmed
        # second callback can be discarded, but emptying execution queue won't hurt.
        get_user_confirmation(
            message=confirmation_message,
            callbacks=(execute_commands, empty_execution_queue),
        )

    return


def execute_commands():
    global execution_queue
    if execution_queue:
        for func, func_params, log in execution_queue:
            logging.info(log)
            output = func(**func_params)


def string_matcher(list_a, list_b):
    similarities = np.zeros((len(list_a), len(list_b)))
    for i, item_a in enumerate(list_a):
        for j, item_b in enumerate(list_b):
            similarities[i, j] = SequenceMatcher(None, item_a, item_b).ratio()

    similarities_agg = np.argmax(similarities, 1)
    return {item_a: list_b[similarities_agg[i]] for i, item_a in enumerate(list_a)}


def get_task_id(task_name):
    # Fetch the ID of the corresponding task_name
    ## if task_name is identical to an ID, it is treated as an ID, else I'll search the task names for it.
    task_name = str(task_name)

    ids, names = zip(
        *[(task["id"], task["title"]) for task in json.loads(get_tasks_data())]
    )

    if task_name in ids:
        return task_name

    found_names = [task for task in names if task_name.lower() in task.lower()]
    if len(found_names) > 1:
        logging.info("multiple tasks found!")
        return False
    elif len(found_names) == 0:
        logging.info(f"no tasks found searching for {task_name}!")
        return False
    else:
        return ids[names.index(found_names[0])].strip()


def reset_todocli():
    todo_loc = todo_location().strip()
    if Path.exists(Path(todo_loc)):
        shutil.rmtree(todo_loc)
        logging.info(f"removed {todo_loc}")


def standardize_date_format(text):
    # Define a regex pattern to match dates in MM/DD/YYYY, DD-MM-YYYY, YYYY/MM/DD formats, etc.
    # This pattern also matches optional time in HH:MM:SS format after the date.
    date_pattern = re.compile(
        r"(?P<year>\d{4})[/-](?P<month>\d{1,2})[/-](?P<day>\d{1,2})|"  # Matches YYYY-MM-DD and variants
        r"(?P<month2>\d{1,2})[/-](?P<day2>\d{1,2})[/-](?P<year2>\d{4})|"  # Matches MM/DD/YYYY and variants
        r"(?P<day3>\d{1,2})[/-](?P<month3>\d{1,2})[/-](?P<year3>\d{4})"  # Matches DD-MM-YYYY and variants
        r"(?:\s+(?P<hours>\d{1,2}):(?P<minutes>\d{2}):(?P<seconds>\d{2}))?",  # Optional time
        re.VERBOSE,
    )

    def replace_with_standard_format(match):
        # Extract date components from the match object
        year = match.group("year") or match.group("year2") or match.group("year3")
        month = match.group("month") or match.group("month2") or match.group("month3")
        day = match.group("day") or match.group("day2") or match.group("day3")
        hours = match.group("hours")
        minutes = match.group("minutes")
        seconds = match.group("seconds")

        # Format month and day to ensure two digits
        month = f"{int(month):02d}"
        day = f"{int(day):02d}"

        # Construct the standard date format
        standard_date = f"{year}-{month}-{day}"
        if hours and minutes and seconds:
            return f"{standard_date} {hours}:{minutes}:{seconds}"
        else:
            return standard_date

    # Replace all found dates with the standard format
    return date_pattern.sub(replace_with_standard_format, text)


def student_llm(input_prompt, cleanup=False):
    if cleanup:
        reset_todocli()

    logging.info("-----Request Start-----")

    llm = LLAMA2()

    # Agent with tools such as weather
    tools = [
        Tool(
            name="weather",
            func=OpenWeatherMapAPIWrapper().run,
            description="""Can be used to get the forecast weather at a particular CITY and DATE.\
                  Only use it when an outdoor activity has been mentioned EXPLICITLY in user's task.\
                      the city and date have to be visibly present and immediately in user's request.\
                        It is based on your judgement whether an activity belongs to outdoor activities.""",
        ),
    ]
    with open("./agent_prompt_template.txt", "r") as f:
        agent_prompt_template = f.read()
    agent_prompt = PromptTemplate.from_template(agent_prompt_template)
    agent = create_json_chat_agent(llm, tools, agent_prompt)
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, handle_parsing_errors=False
    )
    result = agent_executor.invoke({"input": input_prompt})
    agent_output = result["output"]

    ## Task Manager
    USER_PROMPT = (
        "here is the list of my current tasks in JSON format:\n"
        + f"{get_tasks_data()}\n"
        + f"instruction: {input_prompt}\n"
        + f"<<weather check report>>: {agent_output}"
    )
    logging.info(f"\nuser prompt:\n-----{USER_PROMPT}\n-----")
    FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
    response = llm.invoke(FULL_PROMPT)
    set_raw_llm_response(response)

    # Execute commands
    parse_llm_output_and_populate_commands(response)
    ## Warning:  this part of code and everything after is not guranteed to run. the flow of the program may change in parse_llm_output_and_populate_commands. Reason: streamlit and user confirmation.
    execute_commands()
    return
