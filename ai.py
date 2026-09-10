import os
import json

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from google import genai
from google.genai import types

from database import (
    add_memory,
    get_memories,
    update_memory,
    delete_memory,
    CATEGORIES
)

SYSTEM_PROMPT = """
You are a personal productivity assistant.

Your job is to help the user manage their tasks, projects, preferences,
and other useful personal information. You have access to a persistent
local memory database.

The database has five categories:

1. Tasks
   Things the user needs to do, including assignments, errands,
   deadlines, and other actionable items.

2. Projects
   Larger or ongoing efforts. This can include project descriptions,
   requirements, expected difficulty, time requirements, dependencies,
   and other useful information.

3. Preferences
   Information about what the user likes, dislikes, enjoys, or prefers,
   particularly regarding how they work and what kinds of activities
   they prefer.

4. Context
   Temporary or situational information that may affect your
   recommendations, such as how much time the user has, their current
   workload, or what they are currently dealing with.

5. Miscellaneous
   Useful information that does not naturally belong in the other
   categories.

MEMORY RULES:

- Save information when the user explicitly asks you to remember it.
- You may also save information that is clearly useful for helping the
  user in future conversations, but do not save every casual statement.
- When deciding what the user should work on, retrieve relevant memories
  before making recommendations.
- Consider information across multiple categories when it is relevant.
- Use the user's preferences and project information when appropriate,
  rather than considering only their tasks.
- If information in memory is outdated or the user provides a correction,
  update the existing memory rather than unnecessarily creating a new one.
- Do not delete information unless the user asks you to delete it or it
  is clearly being replaced by newer information.
- Never invent memories or claim to remember something that is not in the
  database.

PRODUCTIVITY REASONING:

When making recommendations, consider factors such as:

- deadlines and urgency
- how much time the user currently has
- estimated time or effort required
- dependencies between tasks or projects
- the user's stated preferences
- whether a task can reasonably be completed in the available time
- whether starting a task would be useful even if it cannot be completed
- the user's current context

The goal is not simply to tell the user what is most urgent. Help the
user make practical decisions about how to spend their available time.

TOOL USE:

Use the database tools whenever persistent information needs to be
stored, retrieved, modified, or deleted.

When the user asks a question that could be answered using their stored
information, retrieve the relevant information rather than guessing.

Keep responses natural and conversational. Do not mention internal
database IDs, tool calls, or implementation details unless the user
asks about them.
"""

load_dotenv()

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


TOOLS = [
    {
        "type": "function",
        "name": "add_memory",
        "description": "Store a new piece of information in the user's personal memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": CATEGORIES,
                    "description": "The category this memory belongs to."
                },
                "content": {
                    "type": "string",
                    "description": "The information to remember."
                }
            },
            "required": ["category", "content"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_memories",
        "description": "Retrieve memories from the user's personal memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": ["string", "null"],
                    "enum": CATEGORIES + [None],
                    "description": "The category to retrieve. Use null to retrieve all categories."
                }
            },
            "required": ["category"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "update_memory",
        "description": "Change an existing memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "integer",
                    "description": "The ID of the memory to update."
                },
                "content": {
                    "type": "string",
                    "description": "The new content for the memory."
                },
                "category": {
                    "type": ["string", "null"],
                    "enum": CATEGORIES + [None],
                    "description": "The new category, or null to keep the existing category."
                }
            },
            "required": ["memory_id", "content", "category"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "delete_memory",
        "description": "Delete an existing memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "integer",
                    "description": "The ID of the memory to delete."
                }
            },
            "required": ["memory_id"],
            "additionalProperties": False
        }
    }
]


def execute_tool(name, arguments):
    if name == "add_memory":
        return add_memory(
            arguments["category"],
            arguments["content"]
        )

    if name == "get_memories":
        memories = get_memories(arguments["category"])
        return memories

    if name == "update_memory":
        update_memory(
            arguments["memory_id"],
            arguments["content"],
            arguments["category"]
        )
        return "Memory updated successfully."

    if name == "delete_memory":
        delete_memory(arguments["memory_id"])
        return "Memory deleted successfully."

    raise ValueError(f"Unknown tool: {name}")


def ask_openai(message):
    response = openai_client.responses.create(
        model="gpt-4o-mini",
        instructions=SYSTEM_PROMPT,
        input=message,
        tools=TOOLS
    )

    while True:
        tool_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            return response.output_text

        tool_outputs = []

        for tool_call in tool_calls:
            arguments = json.loads(tool_call.arguments)

            result = execute_tool(
                tool_call.name,
                arguments
            )

            tool_outputs.append({
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": str(result)
            })

        response = openai_client.responses.create(
            model="gpt-4o-mini",
            instructions=SYSTEM_PROMPT,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=TOOLS
        )


def ask_gemini(message):
    gemini_tools = [
        types.Tool(
            function_declarations=TOOLS
        )
    ]

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=gemini_tools
        )
    )

    while True:
        function_calls = []

        for part in response.candidates[0].content.parts:
            if part.function_call:
                function_calls.append(part.function_call)

        if not function_calls:
            return response.text

        function_responses = []

        for function_call in function_calls:
            arguments = dict(function_call.args)

            result = execute_tool(
                function_call.name,
                arguments
            )

            function_responses.append(
                types.Part.from_function_response(
                    name=function_call.name,
                    response={
                        "result": result
                    }
                )
            )

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                response.candidates[0].content,
                types.Content(
                    role="user",
                    parts=function_responses
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=gemini_tools
            )
        )


def ask_ai(message):
    try:
        return ask_openai(message)

    except RateLimitError:
        print("OpenAI limit reached. Switching to Gemini.")
        return ask_gemini(message)


if __name__ == "__main__":
    response = ask_ai(
        "Remember that I really enjoy working on quantum computing projects."
    )

    print(response)