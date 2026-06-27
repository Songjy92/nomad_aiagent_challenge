import dotenv
dotenv.load_dotenv()
from openai import OpenAI
import streamlit as st
from agents import Agent, Runner, SQLiteSession, WebSearchTool, FileSearchTool, ImageGenerationTool, CodeInterpreterTool
import asyncio
import os
import base64

client = OpenAI()

VECTOR_STORE_ID = os.getenv("OPENAI_VECTOR_STORE_ID")

if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="life-coach",
        instructions="""
        [Role & Goal]
        You are a highly skilled, warm, empathetic, and energetic certified Life Coach. Your goal is to empower users, unlock their potential, and guide them towards their dreams using evidence-based coaching principles (such as Cognitive Behavioral Coaching, the GROW model, and Positive Psychology).

        [Core Rules & Methodologies]
        1. Empathy-First Validation: Always validate the user's feelings before jumping to solutions. Use nuanced empathy (e.g., "It takes a lot of courage to share that...", "It sounds like you've been carrying a heavy load.").
        2. Cognitive Reframing: Help users shift from limiting beliefs to a growth mindset. Assist them in reinterpreting setbacks as lessons or hidden opportunities, avoiding toxic positivity.
        3. Micro-Action Design: Never leave a session without a single, highly actionable, and frictionless micro-step (e.g., "Can we start with just 2 minutes of planning today?"). Reference habit-stacking or tiny habits principles.
        4. Dynamic Tone & Style: Adapt your energy level to the user's mood. Be a warm sanctuary when they are exhausted, a strong pillar when they are stuck, and an enthusiastic cheerleader when they succeed. Use warm emojis (🌟, 💪, 🌱, ✨, 🚀) to enhance the vibe. Never judge or criticize.

        [Integrated Tool Strategy]
        Combine your tools to provide a seamless, rich coaching experience:
        - When a user uploads or references goals (via File Search), cross-reference it with active productivity trends or studies (via Web Search) to ground your advice in their personal context.
        - Combine text advice with tailored visual aids (via Image Generation) to build an immersive emotional connection.

        [Tools Guidance]
        1. Web Search Tool (Proactive & Seamless):
            - Trigger: Search when a user shares a challenge, habit, career dream, or productivity roadblock.
            - Search Target: Psychological findings, modern productivity frameworks, and inspiring real-world success stories.
            - Integration: Embed findings naturally without stating "According to my search..." or "Here are search results." Synthesize it as your own structured coaching wisdom.
        
        2. File Search Tool (Contextual Alignment & Goal Priority):
            - Goal Priority: When the user asks about their goals, you MUST prioritize searching the uploaded files using this tool first to find relevant details.
            - Fallback Behavior: If there is no uploaded file, or if no specific goals are found in the search results, politely ask the user to define their goals or upload a document containing their goals.
            - Trigger: Read files when the user uploads or references past logs, plans, or goals.
            - Goal: Align all advice to their documented goals, keeping them accountable to their own written vision.
        
        3. Image Generation Tool (Visual Catalyst):
            - Trigger: Proactively generate or suggest generating high-quality visual aids:
                a) Goal-based Vision Board: Visual collage of their dream (e.g., "A modern workspace filled with sunlight and plants, symbolizing a successful freelance designer career, warm lighting, highly detailed").
                b) Motivational Poster: Minimalist, clean aesthetic poster with a powerful customized quote overlay (e.g., "A serene mountain peak at dawn with the words 'Every step counts' in elegant, clean modern typography, inspiring, photographic").
                c) Progress Metaphor: A graphic representation of their journey (e.g., "A young green sprout growing through a crack in a paved path, reaching towards a bright light, visual metaphor of resilience and growth, warm and hopeful").
            - Quality: Always craft precise, visually rich image generation prompts in English, specifying mood, style, and lighting. Always reference the generated image in your coaching response to anchor the visualization.
        
        4. Code Interpreter Tool (Structured Planning & Data Analysis):
            - Purpose: Use this tool to help users structure their plans, break down goals into actionable steps, or analyze data.
            - Integration: Combine your text advice with tailored Python code blocks to provide concrete, executable plans or analysis.
            - Quality: Always craft precise, Python code blocks. Always reference the generated code in your coaching response to anchor the visualization.
            - Trigger: Use this tool when the user needs help with planning, organizing, or analyzing data. For example, if the user wants to create a plan, break down a goal into actionable steps, or analyze data.
        """,

        tools=[WebSearchTool(), 
        FileSearchTool(vector_store_ids=[VECTOR_STORE_ID], max_num_results=3), 
        ImageGenerationTool(
            tool_config={
                "type": "image_generation",
                "quality":"high",
                "output_format":"jpeg",
                "moderation":"low",
                "partial_images":1, #이미지가 최종 결과물을 받기 전에 흐리게 시작해서 점차적으로 결과를 받아오는 기능
            }
        ),
        CodeInterpreterTool(
            tool_config={
                "type": "code_interpreter",
                "container":{"type":"auto"}
            }
        ),
        ]
    )

agent = st.session_state["agent"]

class SafeSQLiteSession(SQLiteSession):
    async def get_items(self, limit=None):
        items = await super().get_items(limit)
        allowed_types = {"message", "tool_call", "tool_call_output", "compaction"}
        cleaned_items = []
        for item in items:
            if isinstance(item, dict):
                item_type = item.get("type")
                if item_type and item_type not in allowed_types:
                    continue
            cleaned_items.append(item)
        return cleaned_items

if "session" not in st.session_state:
    st.session_state["session"] = SafeSQLiteSession("chat-history", "life-coach-memory.db",)

session = st.session_state["session"]


async def paint_history():
    messages = await session.get_items()

    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] =="message":
                        st.write(message["content"][0]["text"])
        if "type" in message:
            message_type = message["type"]
            if message_type == "web_search_call":
                with st.chat_message("ai"):
                    st.write("Searching the web...")
            elif message_type == "file_search_call":
                with st.chat_message("ai"):
                    st.write("Searching the file...")
            elif message_type == "image_generation_call":
                image = base64.b64decode(message["result"])
                with st.chat_message("ai"):
                    st.image(image)


def update_status(status_container, event):
    status_messages={
        "response.web_search_call.complted" : ("Search completed", "complete"),
        "response.web_search_call.in_progress" : ("Starting Web search", "running"),
        "response.web_search_call.searching" : ("Executing web search", "running"),        
        "response.completed" : ("Done", "complete"),
        "response.file_search_call.complted" : ("File search completed", "complete"),
        "response.file_search_call.in_progress" : ("Starting File search", "running"),
        "response.file_search_call.searching" : ("Executing File search", "running"), 
        "response.image_generation_call.in_progress" : ("Starting Image generation", "running"),
        "response.image_generation_call.generating" : ("Generating image", "running"),
        "response.image_generation_call.completed" : ("Image generation completed", "complete"),
        "response.code_interpreter_call.in_progress" : ("Starting Code execution", "running"),
        "response.code_interpreter_call.executing" : ("Executing code", "running"),
        "response.code_interpreter_call.completed" : ("Ran code blocks", "complete"),
        "response.code_interpreter_call.done" : ("Ran code blocks", "complete"),
        }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)
        

asyncio.run(paint_history())


async def run_agent(message):

    with st.chat_message("ai"):
        status_container = st.status("Thinking...", expanded=False)
        code_placeholder = st.empty()
        text_placeholder = st.empty()
        image_placeholder = st.empty()
        response = ""
        code_response = ""

        st.session_state["code_placeholder"] = code_placeholder
        st.session_state["text_placeholder"] = text_placeholder
        st.session_state["image_placeholder"] = image_placeholder

        stream = Runner.run_streamed(
            agent,
            message,
            session=session
        )
        async for event in stream.stream_events():
            if event.type == "raw_response_event":
                update_status(status_container, event.data.type)

                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response)

                if event.data.type == "response.code_interpreter_call.delta":
                    code_response += event.data.delta
                    code_placeholder.code(code_response)

                elif event.data.type == "response.image_generation_call.partial_image":
                    image = base64.b64decode(event.data.partial_image_b64)
                    image_placeholder.image(image)

        
prompt = st.chat_input("Write a message for your assistant", accept_file=True, file_type=["txt", "pdf", "jpg", "jpeg", "png"])

if prompt:
    if "code_placeholder" in st.session_state:
        st.session_state["code_placeholder"].empty()
    if "text_placeholder" in st.session_state:
        st.session_state["text_placeholder"].empty()
    if "image_placeholder" in st.session_state:
        st.session_state["image_placeholder"].empty()

    # 사용자가 먼저 파일을 올리고 채팅을 하는 경우를 고려해서 업로드 부분이 앞에
    for file in prompt.files:
        if file.type.startswith("text/"):
            with st.chat_message("ai"):
                with st.status("Uploading file...") as status:
                    uploaded_file = client.files.create(
                        file=(file.name, file.getvalue()),
                        purpose="user_data"
                    )
                    status.update(label=f"Attaching {file.name} to vector store...")
                    client.vector_stores.files.create(
                        vector_store_id=VECTOR_STORE_ID,
                        file_id=uploaded_file.id
                    )
                    st.write(f"Uploading {file.name} is completed!")
        elif file.type.startswith("image/"):
            with st.status("⏳ Uploading image...") as status:
                file_bytes = file.getvalue()
                base64_data = base64.b64encode(file_bytes).decode("utf-8")
                data_uri = f"data:{file.type};base64,{base64_data}"
                asyncio.run(
                    session.add_items(
                        [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_image",
                                        "detail": "auto",
                                        "image_url": data_uri,
                                    }
                                ],
                            }
                        ]
                    )
                )
                status.update(label="✅ Image uploaded", state="complete")
            with st.chat_message("human"):
                st.image(data_uri)

    if prompt.text:
        with st.chat_message("user"):
            st.write(prompt.text)
        asyncio.run(run_agent(prompt.text))


with st.sidebar:
    reset = st.button("Reset Memory")
    if reset:
        asyncio.run(session.clear_session())
        st.rerun()
    st.write(asyncio.run(session.get_items()))
