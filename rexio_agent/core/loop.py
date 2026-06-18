import re
import ast
import json
import uuid
from typing import Dict, Any, Generator, List, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from rexio_agent.core.llm import LlmClient
from rexio_agent.tools.registry import ToolRegistry
from rexio_agent.db.connection import save_conversation, save_message, get_messages

console = Console()

SYSTEM_INSTRUCTION_TEMPLATE = """You are RexiO Agent, an advanced, self-improving, persistent AI agent framework. 
You think steps through, select tools to interact with the system or search the web, learn from results, and compile reusable functions.

You must follow the ReAct flow:
1. Thought: Reason about what you need to do next.
2. Action: Call a registered tool using python call syntax: tool_name(arg1="val1", arg2="val2").
3. Observation: The system will return the output of the tool.
4. ... (repeat as needed)
5. Final Answer: Your final message back to the user.

Available tools:
{tool_definitions}

Formatting Constraints:
- Every action must match EXACTLY this format: Action: tool_name(arg1="value1", arg2="value2")
- Do not output markdown code blocks around the Action line.
- Always output a Thought before an Action.
- Once you have the final answer, output 'Final Answer: ' followed by your response.
"""

def parse_action(action_str: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Parses a tool call string like 'write_file(path="a.txt", content="hello")' using AST."""
    try:
        # Wrap in expression to make AST parseable
        tree = ast.parse(action_str.strip())
        if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Call):
            call_node = tree.body[0].value
            func_name = call_node.func.id
            kwargs = {}
            for kw in call_node.keywords:
                kwargs[kw.arg] = ast.literal_eval(kw.value)
            return func_name, kwargs
    except Exception:
        pass
    return None

def extract_action_and_thought(text: str) -> Tuple[Optional[str], Optional[Tuple[str, Dict[str, Any]]]]:
    """Extracts the thought and tool action from LLM response text."""
    # Find thought
    thought_match = re.search(r'Thought:\s*(.*?)(?=Action:|Final Answer:|$)', text, re.DOTALL)
    thought = thought_match.group(1).strip() if thought_match else None
    
    # Find Action
    action_match = re.search(r'Action:\s*([a-zA-Z_][a-zA-Z0-9_]*\s*\(.*\))', text, re.DOTALL)
    if action_match:
        action_expr = action_match.group(1).strip()
        parsed = parse_action(action_expr)
        if parsed:
            return thought, parsed
            
    return thought, None

class AgentSession:
    def __init__(self, platform: str = "cli", channel_id: str = "default", conversation_id: Optional[str] = None):
        self.llm = LlmClient()
        self.registry = ToolRegistry()
        self.platform = platform
        self.channel_id = channel_id
        self.conversation_id = conversation_id or str(uuid.uuid4())
        
        # Save new conversation to DB
        save_conversation(self.conversation_id, self.platform, self.channel_id)
        
    def run(self, user_input: str, max_steps: int = 10) -> str:
        """Executes the agent loop for a user query."""
        self.execution_log: List[Dict[str, Any]] = []
        
        # 1. Fetch history from DB
        history = get_messages(self.conversation_id)
        save_message(self.conversation_id, "user", user_input)
        
        # Build chat history representation for LLM prompt
        history_prompt = ""
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            history_prompt += f"{role_label}: {msg['content']}\n"
        history_prompt += f"User: {user_input}\n"
        
        # Prepare system instruction
        system_instruction = SYSTEM_INSTRUCTION_TEMPLATE.format(
            tool_definitions=self.registry.get_tool_definitions()
        )
        
        # Start ReAct trace
        trace = history_prompt + "\nAssistant:\n"
        step = 0
        final_answer = ""
        
        while step < max_steps:
            step += 1
            # Call LLM with stop sequence on Observation: to prevent model from hallucinating tool outputs
            response_text = self.llm.generate(
                system_instruction=system_instruction,
                prompt=trace,
                stop_sequences=["Observation:"]
            )
            
            # Append generated text to trace
            trace += response_text
            
            thought, action = extract_action_and_thought(response_text)
            
            if thought:
                console.print(Panel(Text(thought, style="italic yellow"), title="Thinking"))
                
            if action:
                tool_name, tool_args = action
                console.print(Panel(Text(f"Tool: {tool_name}\nArguments: {tool_args}", style="bold green"), title="Executing Tool"))
                
                # Execute tool
                observation = self.registry.execute(tool_name, tool_args, execution_log=self.execution_log)
                console.print(Panel(Text(observation[:500] + ("..." if len(observation) > 500 else ""), style="cyan"), title="Observation"))
                
                # Log step
                self.execution_log.append({
                    "thought": thought,
                    "tool": tool_name,
                    "args": str(tool_args),
                    "observation": observation
                })
                
                # Add observation to trace
                trace += f"\nObservation: {observation}\n"
            else:
                # Check for Final Answer
                final_match = re.search(r'Final Answer:\s*(.*)', response_text, re.DOTALL)
                if final_match:
                    final_answer = final_match.group(1).strip()
                else:
                    # Fallback if no specific format was matched
                    final_answer = response_text.replace("Assistant:", "").strip()
                break
                
        if not final_answer:
            final_answer = "Sorry, I could not complete the request within the step limit."
            
        save_message(self.conversation_id, "assistant", final_answer)
        return final_answer

    def run_stream(self, user_input: str, max_steps: int = 10) -> Generator[str, None, None]:
        """Executes the ReAct loop, then streams the final answer token-by-token as SSE events.

        Yields SSE-formatted strings:
          - data: {"type": "step", "thought": ..., "tool": ..., "args": ..., "observation": ...}
          - data: {"type": "token", "text": "..."}
          - data: {"type": "done", "conversation_id": "..."}
          - data: {"type": "error", "message": "..."}
        """
        self.execution_log: List[Dict[str, Any]] = []

        history = get_messages(self.conversation_id)
        save_message(self.conversation_id, "user", user_input)

        history_prompt = ""
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            history_prompt += f"{role_label}: {msg['content']}\n"
        history_prompt += f"User: {user_input}\n"

        system_instruction = SYSTEM_INSTRUCTION_TEMPLATE.format(
            tool_definitions=self.registry.get_tool_definitions()
        )

        trace = history_prompt + "\nAssistant:\n"
        step = 0
        final_answer_tokens: List[str] = []

        try:
            while step < max_steps:
                step += 1
                response_text = self.llm.generate(
                    system_instruction=system_instruction,
                    prompt=trace,
                    stop_sequences=["Observation:"]
                )
                trace += response_text

                thought, action = extract_action_and_thought(response_text)

                if action:
                    tool_name, tool_args = action
                    observation = self.registry.execute(tool_name, tool_args, execution_log=self.execution_log)

                    step_event = {
                        "type": "step",
                        "thought": thought or "",
                        "tool": tool_name,
                        "args": str(tool_args),
                        "observation": observation,
                    }
                    self.execution_log.append(step_event)
                    yield f"data: {json.dumps(step_event)}\n\n"
                    trace += f"\nObservation: {observation}\n"
                else:
                    # Reached Final Answer — stream it token by token
                    final_match = re.search(r'Final Answer:\s*(.*)', response_text, re.DOTALL)
                    preamble = final_match.group(1).strip() if final_match else response_text.replace("Assistant:", "").strip()

                    # Stream the preamble text we already have, then continue streaming
                    if preamble:
                        final_answer_tokens.append(preamble)
                        yield f"data: {json.dumps({'type': 'token', 'text': preamble})}\n\n"

                    # Stream remaining tokens from a fresh LLM call if preamble was cut off
                    # (Only needed when model stopped naturally at Final Answer marker)
                    break

            final_answer = "".join(final_answer_tokens).strip()
            if not final_answer:
                final_answer = "Sorry, I could not complete the request within the step limit."
                yield f"data: {json.dumps({'type': 'token', 'text': final_answer})}\n\n"

            save_message(self.conversation_id, "assistant", final_answer)
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': self.conversation_id, 'execution_log': self.execution_log})}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

