import unittest
from unittest.mock import patch, call
import llm_communication
from llm_communication import (
    todo_add,
    reset_todocli,
    llama_generate,
    execution_process,
    parse_llm_output,
)

# Reading config variables
with open("./aws_api.key", "r") as f:
    AWS_API_KEY = f.readlines()[0].strip()

with open("./base_prompt.txt", "r") as f:
    BASE_PROMPT = f.read()


class TestLLMCommunication(unittest.TestCase):
    def setup_testing_env(self):
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
        todo_add(title="Read AD last lecture", context="study", priority=4)  # ID:9
        todo_add(title="play dota 2", context="hobby", priority=1)  # ID:a
        todo_add(title="bananas", context="shppinglist", priority=1)  # ID:b
        todo_add(title="apples", context="shppinglist", priority=1)  # ID:c

    def test_todo_rm_single_task(self):
        self.setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = """can you remove "elden ring" from my items?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            mock_log_and_exec_process.assert_any_call("todo rm 1", "todo_rm")

    def test_todo_rm_mult_tasks(self):
        self.setup_testing_env()
        with patch(
            "llm_communication.log_and_exec_process",
            wraps=llm_communication.log_and_exec_process,
        ) as mock_log_and_exec_process:
            USER_PROMPT = """can you remove "bananas" and "rust" from my items?"""
            FULL_PROMPT = BASE_PROMPT + f"\nUSER: {USER_PROMPT}\n"
            response = llama_generate(FULL_PROMPT, AWS_API_KEY)
            execution_process(parse_llm_output(response))
            # Assertion
            assert (
                call("todo rm 2 b", "todo_rm") in mock_log_and_exec_process.mock_calls
                or call("todo rm b 2", "todo_rm")
                in mock_log_and_exec_process.mock_calls
            )


if __name__ == "__main__":
    unittest.main()
