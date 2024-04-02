# ### TODO
# - implement scenarios. first run them by hand. start from simple single step and continue with more complex:
#     - adding task (1 step)
#         - "can you add task a and b to my homework list?"
#     - listing tasks (1 step)
#         - "can you list my items in games wish list?"
#     - moving tasks to new context (1 step)
#         - "can you move the items in study context to hardwork context?"
#     - modifying task attributes (2 step)
#         - "can you change the name of elden ring to elden lord?"
#     - removing context (1 step)
#         - "can you remove my study list?"
#     - removing task (2 steps)
#         - 'can you remove the second item in my games wish list?'
#     - merging contexts (2 steps)
#         - "can you merge best games context and games wish list context?"
#     - adding deadline, start, period or any sort of time (2 step)
#         - "can you add a deadline for my study list for tomorrow?"
#     - mark task as done (2 steps)
#         - "can you mark elden ring from my games wish list as done?"
# - json won't parse if a character is extra or missing. make it robust.
# - read some blog posts about the same software solutions
# - connect function calling with llm and test a few basic scenarios
# - enhance prompt:
#     - tune tempereture. Start with 0 temperature
# - Frontend: use streamlit

# ### Helper functions
# - find a task by name -> get_task_id(task_name) returns success ? task_id : None

# ### Notes:
# - spell checking. may need to first find the correct task title and id.
# - may be good to store the last n characters of the conversation and input it as context to the model.
# - best way for remote function calling in python
# - model may perform repetitive operations. when asked to merge, it added some tasks first which is wrong.
# - can pass history in each request to enrich the propmt.
# - can pass the output of todo --flat in each request to enrich the promp.
# - can let the model hallucinate to see other scenarios and test cases and the model's response
# - can specify the steps the model needs to take to respond for each specific query and command

# ### Questions:
# - design a feedback loop. how the model is meant to know the meaning of errors?

import json
import datetime
import subprocess
import re
import shutil
from pathlib import Path
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("debug.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def process_bash_output(o):
    # TODO
    return o


def log_and_exec_process(command, func_name):
    logging.info(f"running command: {command}")
    p = subprocess.run(["bash", "-c", command], capture_output=True, text=True)
    logging.info(f"{func_name} finished")
    output = process_bash_output(p.stdout)
    if output:
        logging.info(
            f"command output:\n{output}",
        )
        return output


def todo(context="", flat=False, tidy=False):
    """
    Print undone tasks based on context.

    Parameters:
        context (str): The path of the context the task belongs to. It's a sequence of strings separated by dots where each string indicate the name of a context in the contexts hierarchy.
        flat (bool): Whether to list subcontexts below tasks (False) or integrate tasks of subcontexts with general tasks (True). Defaults to False.
        tidy (bool): Alternative way to specify whether to list subcontexts below tasks (False) or integrate tasks of subcontexts with general tasks (True). Defaults to False.

    Returns:
        None
    """
    command = f"todo"
    if context:
        command += f"""\"{context}\""""
    if flat or tidy:
        command += " --flat" if flat else "--tidy"

    return log_and_exec_process(command, "todo")


def todo_add(
    title,
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
        command += f" --deadline {deadline}"
    if start:
        command += f" --start {start}"
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


def todo_done(ids):
    """
    Set tasks identified by IDs as done.

    Parameters:
        ids (list of str): List of task IDs to mark as done.

    Returns:
        None
    """
    command = f"todo done {' '.join(ids)}"

    log_and_exec_process(command, "todo_done")


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
    command = f"todo task {id}"
    if deadline:
        command += f" --deadline {deadline}"
    if start:
        command += f" --start {start}"
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
    term, context=None, done=True, undone=False, before=None, after=None, case=False
):
    """
    Search for tasks whose title contains the substring <term> based on the specified criteria.

    Parameters:
        term (str): Search term.
        context (str): Context for the search. Defaults to None.
        done (bool): Whether to search for done tasks. Defaults to True.
        undone (bool): Whether to search for undone tasks. Defaults to False.
        before (str): Limit search to tasks created before this moment. MOMENT can be a specific moment in time, in the following format: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, YYYY-MM-DDTHH:MM:SS. It can also be a delay, such as 2w which means "2 weeks from now". Other accepted characters are s, m, h, d, w, which respectively correspond to seconds, minutes, hours, days and weeks. An integer must preeced the letter. Defaults to None.
        after (str): Limit search to tasks created after this moment. MOMENT can be a specific moment in time, in the following format: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, YYYY-MM-DDTHH:MM:SS. It can also be a delay, such as 2w which means "2 weeks from now". Other accepted characters are s, m, h, d, w, which respectively correspond to seconds, minutes, hours, days and weeks. An integer must preeced the letter. Defaults to None.
        case (bool): Whether the search is case sensitive. Defaults to False.

    Returns:
        None
    """
    # TODO: return proper output and edit the func doc
    command = f"todo search '{term}'"
    if context:
        command += f""" --context \"{context}\""""
    if done:
        command += " --done"
    elif undone:
        command += " --undone"
    if before:
        command += f" --before {before}"
    if after:
        command += f" --after {after}"
    if case:
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
    command = f"todo rm {' '.join(ids)}"

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


def todo_ctx(
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

    log_and_exec_process(command, "todo_ctx")


def todo_mv(ctx1, ctx2):
    """
    Move all tasks and subcontexts from one context to another.

    Parameters:
        ctx1 (str): Source context.
        ctx2 (str): Destination context.

    Returns:
        None
    """
    command = f"todo mv '{ctx1}' '{ctx2}'"

    log_and_exec_process(command, "todo_mv")


def todo_rmctx(context, force=False):
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

    # logging
    command = "todo --location"

    return log_and_exec_process(command, "todo_location")


def parse_llm_output(text):
    return text.split("<JSON>")[1].split("<JSON/>")[0].strip()


# TODO: communication between functions needed. Can use stack.
def execution_process(queue):
    functions_dict = {
        "todo": todo,
        "todo_add": todo_add,
        "todo_ctx": todo_ctx,
        "todo_done": todo_done,
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

    execution_queue = json.loads(queue)

    for f in execution_queue:
        func = (
            functions_dict[f["function"]] if f["function"] in functions_dict else None
        )
        if func:
            logging.info(f["log"])
            args = f["parameters"]
            output = func(**args)


def llama_generate(prompt, api_token, max_gen_len=640, temperature=0.2, top_p=0.9):
    global aws_api_quota_remaining
    url = "https://6xtdhvodk2.execute-api.us-west-2.amazonaws.com/dsa_llm/generate"
    body = {
        "prompt": prompt,
        "max_gen_len": max_gen_len,
        "temperature": temperature,
        "top_p": top_p,
        "api_token": api_token,
    }
    res = requests.post(url, json=body)

    aws_api_quota_remaining -= 1
    with open("./aws_api_quota_remaining", "w") as f:
        f.write(str(aws_api_quota_remaining))
    logging.info(f"ramining AWS API calls: {aws_api_quota_remaining}")

    return json.loads(res.text)["body"]["generation"]


if __name__ == "__main__":
    # Reading config variables
    with open("./aws_api_quota_remaining", "r") as f:
        aws_api_quota_remaining = int(f.readlines()[0].strip())

    with open("./aws_api.key", "r") as f:
        AWS_API_KEY = f.readlines()[0].strip()

    with open("./base_prompt.txt", "r") as f:
        BASE_PROMPT = f.read()

    cleanup = False
    todo_loc = todo_location().strip()
    if cleanup and Path.exists(Path(todo_loc)):
        shutil.rmtree(todo_loc)
        logger.info(f"removed {todo_loc}")

    inputs = []
    print("Prompt (when finished, write cooknow): ")
    while True:
        inputs.append(input())
        if "cooknow" in inputs[-1]:
            inputs[-1] = inputs[-1].split("cooknow")[0]
            USER_PROMPT = "\n".join(inputs)
            break
    logging.info(f"user prompt: {USER_PROMPT}")

    FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"

    response = llama_generate(FULL_PROMPT, AWS_API_KEY)
    # print(parse_llm_output(response))

    execution_process(parse_llm_output(response))
