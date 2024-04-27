import unittest
from unittest.mock import patch, call
import logging
from itertools import permutations
from functools import reduce
import re

import llm_communication
from llm_communication import (
    todo_list,
    todo_add,
    todo_search,
    todo_mark_as_done,
    reset_todocli,
    execute_commands,
    parse_llm_output_and_populate_commands,
    get_tasks_data,
)
from langchain_utils import LLAMA2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        # logging.StreamHandler()
    ],
)

with open("./base_prompt.txt", "r") as f:
    BASE_PROMPT = f.read()


def setup_testing_env():
    reset_todocli()
    # Add some tasks to further run some tests on them.
    todo_add(title="Elden Ring", context="games", priority=5)  # ID:1
    todo_add(title="Rust", context="games_wishlist", priority=1)  # ID:2
    todo_add(title="Study Math", context="study", priority=2)  # ID:3
    todo_add(title="Planning", context="work", priority=3)  # ID:4
    todo_add(title="Write Test", context="work", priority=4)  # ID:5
    todo_add(title="Write Diary", context="personal", priority=2)  # ID:6
    todo_add(title="cleaning", context="home", priority=5)  # ID:7
    todo_add(title="water the pots", context="home", priority=3)  # ID:8
    todo_add(title="bananas", context="shoppinglist", priority=1)  # ID:9
    todo_add(title="apples", context="shoppinglist", priority=1)  # ID:a
    todo_add(title="Deutsch Schreiben", context="homework", priority=1)  # ID:b
    todo_add(title="Apply", context="work", priority=3)  # ID:c
    todo_add(title="washing the dishes", context="home", priority=5)  # ID:d

    # todo_add(title="Planning", context="work", priority=3)
    # todo_add(title="Write Test", context="work", priority=4)
    # todo_add(title="Apply", context="work", priority=3)
    # todo_add(title="Ride to office", context="work", priority=1)


class TestLLM_nonportfolio(unittest.TestCase):
    def test_todo_rm_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you remove "elden ring" from my items?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            mock_log_and_exec_process.assert_any_call("todo rm 1", "todo_rm")

    def test_todo_rm_mult_tasks(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you remove "bananas" and "rust" from my items?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            assert (
                call("todo rm 2 b", "todo_rm") in mock_log_and_exec_process.mock_calls
                or call("todo rm b 2", "todo_rm")
                in mock_log_and_exec_process.mock_calls
            )

    def test_todo_add_mult_task(self):
        # TODO: case sensitive task title
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: I want to add some new tasks. add "mamala" and "coding session" to my homeworks?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            mock_log_and_exec_process.assert_has_calls(
                any_order=True,
                calls=[
                    call(
                        """todo add "coding session" --context "homework" --priority 1""",
                        "todo_add",
                    ),
                    call(
                        """todo add "mamala" --context "homework" --priority 1""",
                        "todo_add",
                    ),
                ],
            )

    def test_todo_list_context(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you list my items in games list?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            mock_log_and_exec_process.assert_any_call("""todo \"games\"""", "todo")

    def test_todo_task_rename_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you change the name of "elden ring" to "elden lord"? """
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                'todo task 1 --title "elden lord"', "todo_task"
            )

    def test_todo_task_change_priority_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you change the priority of elden ring to 7?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                """todo task 1 --priority 7""", "todo_task"
            )

    def test_todo_task_change_priority_mult_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you change the priority of elden ring and cleaning to 10?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            mock_log_and_exec_process.assert_has_calls(
                any_order=True,
                calls=[
                    call(
                        """todo task 1 --priority 10""",
                        "todo_task",
                    ),
                    call(
                        """todo task 7 --priority 10""",
                        "todo_task",
                    ),
                ],
            )

    def test_todo_task_change_context_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you change the context of "writing test" to homework?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                """todo task 5 --context \"homework\"""", "todo_task"
            )

    def test_todo_task_set_deadline_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you set the deadline of study math to September 10 2025?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                """todo task 3 --deadline \"2025-09-10\"""", "todo_task"
            )

    def test_todo_task_set_start_single_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you set the start of planning to 2024/10/11 12:34:22?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            mock_log_and_exec_process.assert_any_call(
                """todo task 4 --start \"2024-10-11 12:34:22\"""", "todo_task"
            )

    def test_todo_done_mult_task(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you mark elden ring, writing test and water the pots as done?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            ids = [1, 5, 8]
            perms = [" ".join([str(j) for j in i]) for i in list(permutations(ids))]
            perms = [f"todo done {i}" for i in perms]
            perms_exist = [
                call(i, "todo_mark_as_done") in mock_log_and_exec_process.mock_calls
                for i in perms
            ]
            assert reduce(lambda a, b: a or b, perms_exist)

    def test_todo_rmctx_mult_ctx(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: remove my home, work, and shoppinglist contexts please."""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            mock_log_and_exec_process.assert_has_calls(
                calls=[
                    call("""todo rmctx "work" --force""", "todo_rmctx"),
                    call("""todo rmctx "home" --force""", "todo_rmctx"),
                    call("""todo rmctx "shoppinglist" --force""", "todo_rmctx"),
                ],
                any_order=True,
            )

    def test_todo_search(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: I am looking for undone tasks having study in them. can you do that for me please? I neeeeeeeeeed taht really"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            assert (
                call(
                    "todo search 'study' --undone",
                    "todo_search",
                )
                in mock_log_and_exec_process.mock_calls
                or call(
                    "todo search 'study' --undone --case",
                    "todo_search",
                )
                in mock_log_and_exec_process.mock_calls
            )

    def test_todo_done_based_on_order(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Mark the first and third items on my 'work' context as done."""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            ids = ["5", "c"]
            perms = [" ".join([str(j) for j in i]) for i in list(permutations(ids))]
            perms = [f"todo done {i}" for i in perms]
            perms_exist = [
                call(i, "todo_mark_as_done") in mock_log_and_exec_process.mock_calls
                for i in perms
            ]
            assert reduce(lambda a, b: a or b, perms_exist)

    def test_irrelevant_command_1(self):
        setup_testing_env()
        tasks_data = todo_list(flat=True)
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: can you tell me the capital of US in plain text?"""
            logging.info(f"\nuser prompt:\n-----{USER_PROMPT}\n-----")
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            ## Checking that nothing has changed:
            assert tasks_data == todo_list(flat=True)
            assert mock_log_and_exec_process.mock_calls == [
                call("todo search '' --undone", "todo_search"),
                call("todo search '' --done", "todo_search"),
                call("todo history", "todo_history"),
                call("todo search 'US' --undone --case", "todo_search"),
            ]

    def test_irrelevant_command_2(self):
        setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: what is the meaning of life? tell me I desperately need it."""
            logging.info(f"\nuser prompt:\n-----{USER_PROMPT}\n-----")
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()
            # Assertion
            ## Checking for 'Doing nothing':
            assert mock_log_and_exec_process.mock_calls == [
                call("todo search '' --undone", "todo_search"),
                call("todo search '' --done", "todo_search"),
                call("todo history", "todo_history"),
                call("todo search 'meaning of life' --undone --case", "todo_search"),
            ]


class TestLLM_portfolio(unittest.TestCase):

    def test_portfolio_case_1(self):

        reset_todocli()
        todo_add(title="LLM Homework", context="homework_list")  # ID:1
        todo_add(title="NLP Homework", context="homework_list")  # ID:2
        todo_add(title="Math Homework", context="homework_list")  # ID:3
        todo_add(title="ML Homework", context="homework_list")  # ID:4

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Mark the first and third items on my homework_list as done"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()

            # Assertion
            final_state = todo_list(flat=True)
            assert "ML Homework" in final_state and "NLP Homework" in final_state
            assert (
                "LLM Homework" not in final_state and "Math Homework" not in final_state
            )
            # searching for undone tasks with term LLM or Math should yield nothing
            assert "LLM Homework" in todo_search("LLM Homework", is_done=True)
            assert "Math Homework" in todo_search("Math Homework", is_done=True)

    def test_portfolio_case_2(self):
        reset_todocli()
        todo_add(title="Two bottles of milk", context="shopping_list")  # ID:1
        todo_add(title="Three cans of SinaCola", context="shopping_list")  # ID:2
        todo_add(title="Fifty eggs", context="shopping_list")  # ID:3

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Prioritize the first item in my shopping list"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()

            # Assertion
            final_state = todo_list(flat=True)
            assert bool(re.search(r"Two bottles of milk ★[1-9]\d*", final_state))
            assert final_state.count("★") == 1

    def test_portfolio_case_3(self):
        reset_todocli()
        todo_add(title="NLP Project", context="project_list")  # ID:1
        todo_add(title="Math Project", context="project_list")  # ID:2
        todo_add(title="ML Project", context="project_list")  # ID:3
        todo_add(title="Algebra I Project", context="archive_list")  # ID:4
        todo_mark_as_done([1, 2])

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Move all completed tasks from my project_list to an archive_list"""
            logging.info(f"\nuser prompt:\n-----{USER_PROMPT}\n-----")
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()

            # Assertion
            # The two completed tasks should now be in the archive list
            assert "[DONE] NLP Project #archive_list" in todo_search(
                "", is_done=True, context="archive_list"
            )
            assert "[DONE] Math Project #archive_list" in todo_search(
                "", context="archive_list", is_done=True
            )
            # There should be no done projects
            assert not todo_search("", context="project_list", is_done=True)
            # There should be one undone project
            assert "ML Project" in todo_search(
                "", context="project_list", is_done=False
            )

    def test_portfolio_case_4(self):
        reset_todocli()
        todo_add(title="Mathematics", context="study_list1")  # ID:1
        todo_add(title="Buy chocolate", context="shopping_list")  # ID:2
        todo_add(title="Buy bread", context="shopping_list")  # ID:3
        todo_add(title="History", context="study_list2")  # ID:4
        todo_add(title="Arts", context="study_list2")  # ID:5

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Prioritize all tasks that have to do with my studies"""
            logging.info(f"\nuser prompt:\n-----{USER_PROMPT}\n-----")
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()

            # Assertion
            final_state = todo_list(flat=True)
            # The study related items should be prioritized
            assert bool(re.search(r"Mathematics ★[1-9]\d*", final_state))
            assert bool(re.search(r"History ★[1-9]\d*", final_state))
            assert bool(re.search(r"Arts ★[1-9]\d*", final_state))
            # Only they should be prioritized
            assert final_state.count("★") == 3

    def test_portfolio_case_5(self):
        reset_todocli()
        todo_add(title="Write these tests", context="work_list")  # ID:1
        todo_add(title="Write more tests", context="work_list")  # ID:2
        todo_add(title="Hang out with friends", context="personal_list")  # ID:3
        todo_add(title="Go to the dentist", context="personal_list")  # ID:4

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Merge my work_list and personal_list together into a combined_list"""
            logging.info(f"\nuser prompt:\n-----{USER_PROMPT}\n-----")
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()

            # Assertion
            final_state = todo_list(flat=True)
            # work_list and personal_list should not be in final_state
            assert "#work_list" not in final_state
            assert "#personal_list" not in final_state
            # combined_list should appear four times in final_state
            assert final_state.count("#combined_list") == 4
            # check that a random task is in the combined_list
            assert "Hang out with friends #combined_list" in final_state

    def test_portfolio_case_6(self):
        reset_todocli()
        todo_add(title="Matrix Calculus", context="study_list")  # ID:1
        todo_add(title="Convex Optimization", context="study_list")  # ID:2
        todo_add(title="Differential Equations", context="study_list")  # ID:3
        todo_add(title="League of Legends", context="gaming_list")  # ID:4
        todo_add(title="Heros of the Storm", context="gaming_list")  # ID:5
        todo_add(title="Study Quizzes", context="study_list")  # ID:6

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Set all items in my study_list to maximum importance"""
            logging.info(f"\nuser prompt:\n-----{USER_PROMPT}\n-----")
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()

            # Assertion
            final_state = todo_list(flat=True)
            # Check that all items in study_list have maximum priority
            assert bool(re.search(r"Matrix Calculus ★99", final_state))
            assert bool(re.search(r"Convex Optimization ★99", final_state))
            assert bool(re.search(r"Differential Equations ★99", final_state))
            assert bool(re.search(r"Study Quizzes ★99", final_state))
            # There must be only three ★99
            assert final_state.count("★99") == 4

            # gaming items must occur with no priority
            assert "League of Legends #gaming_list" in final_state
            assert "Heros of the Storm #gaming_list" in final_state

    def test_portfolio_case_7(self):
        reset_todocli()
        todo_add(title="Eat lunch together", context="meeting_agenda_list")  # ID:1
        todo_add(
            title="Review notes on quantum mechanics", context="study_list"
        )  # ID:2
        todo_add(
            title="Solve practice problems for organic chemistry", context="study_list"
        )  # ID:3
        todo_add(
            title="Watch tutorial videos on machine learning algorithms",
            context="study_list",
        )  # ID:4
        todo_add(
            title="Complete project proposal for client X",
            context="work_list",
            priority=9,
        )  # ID:5
        todo_add(
            title="Respond to emails from stakeholders", context="work_list", priority=9
        )  # ID:6
        todo_add(
            title="Schedule follow-up meetings with collaborators",
            context="work_list",
            priority=9,
        )  # ID:7
        todo_add(title="Go for a 30-minute jog", context="health_list")  # ID:8
        todo_add(title="Do yoga for 20 minutes", context="health_list")  # ID:9
        todo_add(
            title="Schedule a check-up appointment with the doctor",
            context="health_list",
            priority=9,
        )  # ID:a
        todo_add(
            title="Organize closet and donate old clothes", context="personal_list"
        )  # ID:b
        todo_add(
            title="Start learning a new language with Duolingo", context="personal_list"
        )  # ID:c

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Prepare for the team meeting by moving all high priority tasks to the meeting_agenda_list"""
            logging.info(f"\nuser prompt:\n-----{USER_PROMPT}\n-----")
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            llm.max_gen_len = 1024
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()

            # Assertion
            final_state = todo_list(flat=True)
            # check that the final state has the high priority items in the agenda list
            assert (
                "Complete project proposal for client X ★9 #meeting_agenda_list"
                in final_state
            )
            assert (
                "Respond to emails from stakeholders ★9 #meeting_agenda_list"
                in final_state
            )
            assert (
                "Schedule follow-up meetings with collaborators ★9 #meeting_agenda_list"
                in final_state
            )
            assert (
                "Schedule a check-up appointment with the doctor ★9 #meeting_agenda_list"
                in final_state
            )
            # and that they no longer belong to their original lists
            assert (
                "Complete project proposal for client X ★9 #work_list"
                not in final_state
            )
            assert (
                "Respond to emails from stakeholders ★9 #work_list" not in final_state
            )
            assert (
                "Schedule follow-up meetings with collaborators ★9 #work_list"
                not in final_state
            )
            assert (
                "Schedule a check-up appointment with the doctor ★9 #health_list"
                not in final_state
            )
            # number of ★ should be 4 (no othe priorities)
            assert final_state.count("★9") == 4

    def test_portfolio_case_8(self):
        reset_todocli()
        todo_add(title="Go swimming", context="priorities_list")  # ID:1
        todo_add(
            title="Complete project proposal for client X",
            context="task_list",
            priority=99,
        )  # ID:2
        todo_add(
            title="Respond to emails from stakeholders",
            context="task_list",
            priority=99,
        )  # ID:3
        todo_add(
            title="Schedule follow-up meetings with collaborators",
            context="task_list",
            priority=90,
        )  # ID:4
        todo_add(
            title="Go to China and see the great wall",
            context="travel_list",
            priority=90,
        )  # ID:5
        todo_add(title="Fly to Paris", context="travel_list", priority=90)  # ID:6

        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = f"""
here is the list of my current tasks in JSON format:
{get_tasks_data()}
instruction: Move all high-importance items from my task_list to my priorities_list"""
            logging.info(f"\nuser prompt:\n-----{USER_PROMPT}\n-----")
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            llm = LLAMA2()
            response = llm.invoke(FULL_PROMPT)
            parse_llm_output_and_populate_commands(response)
            execute_commands()

            # Assertion
            final_state = todo_list(flat=True)
            # Check that the final state has the high priority items in the agenda list
            assert (
                "Complete project proposal for client X ★99 #priorities_list"
                in final_state
            )
            assert (
                "Respond to emails from stakeholders ★99 #priorities_list"
                in final_state
            )
            assert (
                "Schedule follow-up meetings with collaborators ★90 #priorities_list"
                in final_state
            )
            # Ensure priorities_list was not erased
            assert "Go swimming #priorities_list" in final_state
            # and that they no longer belong to their original lists
            assert (
                "Complete project proposal for client X ★99 #task_list"
                not in final_state
            )
            assert (
                "Respond to emails from stakeholders ★99 #task_list" not in final_state
            )
            assert (
                "Schedule follow-up meetings with collaborators ★90 #task_list"
                not in final_state
            )


if __name__ == "__main__":
    llm_communication.confirmation_mechanism_enabled = False
    unittest.main()
