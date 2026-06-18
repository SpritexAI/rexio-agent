import re
import ast
import json
import uuid
import os
from typing import Dict, Any, Generator, List, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from rexio_agent.core.llm import LlmClient
from rexio_agent.tools.registry import ToolRegistry
from rexio_agent.core.memory_store import MemoryStore
from rexio_agent.core.background_review import spawn_background_review
from rexio_agent.db.connection import save_conversation, save_message, update_message_steps, get_messages

SOUL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SOUL.md")

def load_soul() -> str:
    """Loads SOUL.md persona file, strips HTML comments, returns persona text."""
    try:
        with open(SOUL_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
        import re as _re
        # Strip HTML comments
        raw = _re.sub(r'<!--.*?-->', '', raw, flags=_re.DOTALL)
        # Strip markdown heading
        raw = _re.sub(r'^#.*\n', '', raw)
        return raw.strip()
    except FileNotFoundError:
        return ""

console = Console()

SYSTEM_INSTRUCTION_TEMPLATE = """You are RexiO Agent, an advanced, self-improving, persistent AI agent framework.
You think steps through, select tools to interact with the system or search the web, learn from results, and compile reusable functions.

Today's date and time: {current_datetime}

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

        # Load memory store and wire into registry
        self.memory = MemoryStore()
        self.memory.load()
        self.registry.memory_store = self.memory

        # Optional callback for background review notifications (e.g. Telegram)
        self.background_review_callback = None

        # Save new conversation to DB
        save_conversation(self.conversation_id, self.platform, self.channel_id)
        
    def _generate_summary_if_new(self, user_input: str, history: list) -> None:
        """Generates a dynamic 3-5 word summary for the chat title on the first user query."""
        if len(history) == 0:
            try:
                summary_prompt = f"Summarize the following user request into a short, descriptive 3-5 word title for a chat thread. Do not include quotes, markdown, or punctuation. Request: {user_input}"
                summary = self.llm.generate(
                    system_instruction="You are a helpful assistant that summarizes user prompts into short, clean titles.",
                    prompt=summary_prompt
                ).strip()
                summary = summary.replace('"', '').replace("'", "")
                if len(summary) > 40:
                    summary = summary[:37] + "..."
                save_conversation(self.conversation_id, self.platform, self.channel_id, summary)
            except Exception:
                fallback_summary = user_input[:30] + "..." if len(user_input) > 30 else user_input
                save_conversation(self.conversation_id, self.platform, self.channel_id, fallback_summary)

    def run(self, user_input: str, max_steps: int = 10) -> str:
        """Executes the agent loop for a user query."""
        self.execution_log: List[Dict[str, Any]] = []
        
        # 1. Fetch history from DB
        history = get_messages(self.conversation_id)
        self._generate_summary_if_new(user_input, history)
        save_message(self.conversation_id, "user", user_input)
        
        # Build chat history representation for LLM prompt
        history_prompt = ""
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            history_prompt += f"{role_label}: {msg['content']}\n"
        history_prompt += f"User: {user_input}\n"
        
        # Prepare system instruction
        from datetime import datetime
        soul = load_soul()
        markdown_context = self.registry.get_markdown_context()
        memory_block = self.memory.system_prompt_block()
        system_instruction = SYSTEM_INSTRUCTION_TEMPLATE.format(
            tool_definitions=self.registry.get_tool_definitions(),
            current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M")
        ) + (f"\n\n## Persona\n{soul}" if soul else "") + (f"\n\n{memory_block}" if memory_block else "") + markdown_context
        
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
            
        msg_id = save_message(self.conversation_id, "assistant", final_answer)
        if self.execution_log:
            update_message_steps(msg_id, json.dumps(self.execution_log))
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
        self._generate_summary_if_new(user_input, history)
        save_message(self.conversation_id, "user", user_input)

        history_prompt = ""
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            history_prompt += f"{role_label}: {msg['content']}\n"
        history_prompt += f"User: {user_input}\n"

        from datetime import datetime
        soul = load_soul()
        markdown_context = self.registry.get_markdown_context()
        memory_block = self.memory.system_prompt_block()
        system_instruction = SYSTEM_INSTRUCTION_TEMPLATE.format(
            tool_definitions=self.registry.get_tool_definitions(),
            current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M")
        ) + (f"\n\n## Persona\n{soul}" if soul else "") + (f"\n\n{memory_block}" if memory_block else "") + markdown_context

        trace = history_prompt + "\nAssistant:\n"
        step = 0

        try:
            while step < max_steps:
                step += 1
                # Non-streaming call — needed so stop sequences work correctly
                response_text = self.llm.generate(
                    system_instruction=system_instruction,
                    prompt=trace,
                    stop_sequences=["Observation:"]
                )
                trace += response_text

                thought, action = extract_action_and_thought(response_text)

                if action:
                    tool_name, tool_args = action
                    # Emit thought + action preview so the UI can show a live trace card
                    if thought:
                        yield f"data: {json.dumps({'type': 'thinking', 'thought': thought, 'tool': tool_name, 'args': str(tool_args)})}\n\n"

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
                    # No more tool calls — extract or stream the final answer.
                    final_match = re.search(r'Final Answer:\s*(.*)', response_text, re.DOTALL)

                    if final_match:
                        # Model already produced the full answer — stream it word-by-word
                        # without a second LLM call to avoid re-running the ReAct loop.
                        final_answer = final_match.group(1).strip()
                        words = final_answer.split(' ')
                        for i, word in enumerate(words):
                            chunk = word + (' ' if i < len(words) - 1 else '')
                            yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
                    else:
                        # Model stopped mid-generation — ask it to continue, strictly
                        # as plain answer text with no ReAct formatting.
                        answer_prompt = trace.rstrip() + "\nFinal Answer:"
                        final_tokens: List[str] = []
                        for chunk in self.llm.generate_stream(
                            system_instruction=system_instruction,
                            prompt=answer_prompt,
                            stop_sequences=["Thought:", "Action:", "Observation:"],
                        ):
                            final_tokens.append(chunk)
                            yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
                        final_answer = "".join(final_tokens).strip()

                    if not final_answer:
                        final_answer = "Sorry, I could not complete the request within the step limit."
                        yield f"data: {json.dumps({'type': 'token', 'text': final_answer})}\n\n"

                    msg_id = save_message(self.conversation_id, "assistant", final_answer)
                    if self.execution_log:
                        update_message_steps(msg_id, json.dumps(self.execution_log))
                    yield f"data: {json.dumps({'type': 'done', 'conversation_id': self.conversation_id, 'execution_log': self.execution_log})}\n\n"
                    spawn_background_review(
                        llm=self.llm,
                        memory_store=self.memory,
                        registry=self.registry,
                        user_input=user_input,
                        assistant_response=final_answer,
                        history=history,
                        execution_log=self.execution_log,
                        callback=self.background_review_callback,
                    )
                    return


            # Exhausted max steps without a final answer
            fallback = "Sorry, I could not complete the request within the step limit."
            msg_id = save_message(self.conversation_id, "assistant", fallback)
            if self.execution_log:
                update_message_steps(msg_id, json.dumps(self.execution_log))
            yield f"data: {json.dumps({'type': 'token', 'text': fallback})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': self.conversation_id, 'execution_log': self.execution_log})}\n\n"
            spawn_background_review(
                llm=self.llm,
                memory_store=self.memory,
                registry=self.registry,
                user_input=user_input,
                assistant_response=fallback,
                history=history,
                execution_log=self.execution_log,
                callback=self.background_review_callback,
            )

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

