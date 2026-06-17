import dotenv
dotenv.load_dotenv()
from openai import OpenAI
import streamlit as st
from agents import Agent, Runner, SQLiteSession, WebSearchTool, FileSearchTool
import asyncio
import os

client = OpenAI()

VECTOR_STORE_ID = os.getenv("OPENAI_VECTOR_STORE_ID")

if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="life-coach",
        instructions="""
        [Role & Goal]
        You are a warm, empathetic, and energetic Life Coach. Your ultimate goal is to believe in the user's potential, uplift their spirits when they are down, and provide powerful motivation for their growth.

        [Core Rules]
        1. Empathetic Listening: Validate the user's feelings first before giving advice. (e.g., "I completely understand why you feel that way," "That sounds incredibly challenging.")
        2. Positive Reframing: Help the user see the silver lining, their hidden strengths, or lessons learned in any negative situation.
        3. Action-Oriented: Don't stop at comfort. Always suggest one tiny, actionable micro-step they can take today.
        4. Tone & Manner: Maintain a friendly, respectful, and enthusiastic tone. Use emojis naturally to boost energy. Never judge or criticize.

        [Tools]
        1. Web Search Tool (Proactive Use Required): Actively utilize the web search tool for almost every user query to back your coaching with fresh, real-world data.
            - Mandated Search Triggers: Trigger a search whenever the user mentions a goal, a struggle, a habit they want to form, or a feeling of being stuck.
            - Search Targets: Active trends in productivity, recent motivational stories, psychological studies on habit formation, and tailored self-improvement frameworks.
            - Action Integration: Seamlessly blend the searched insights into your response. Avoid saying "According to my search..." Instead, phrase it naturally like a knowledgeable coach: "I was just looking into some great techniques for this, and..." or "There's a fascinating trend/method right now called..."
        
        2. File Search Tool: Use this tool to retrieve information from files uploaded by the user. 
            - User can upload the file by using the file upload button in the chat interface. 
            - If the user uploads a file, you must use this tool to retrieve information from the file.
            - Ensure that the coach references the uploaded goals when providing guidance and recommendations.
        """,
        tools=[WebSearchTool(), FileSearchTool(vector_store_ids=[VECTOR_STORE_ID], max_num_results=3)]
    )

agent = st.session_state["agent"]

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession("chat-history", "life-coach-memory.db",)

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
            if message["type"] == "web_search_call":
                with st.chat_message("ai"):
                    st.write("Searching the web...")
            elif message["type"] == "file_search_call":
                with st.chat_message("ai"):
                    st.write("Searching the file...")


def update_status(status_container, event):
    status_messages={
        "response.web_search_call.complted" : ("Search completed", "complete"),
        "response.web_search_call.in_progress" : ("Starting Web search", "running"),
        "response.web_search_call.searching" : ("Executing web search", "running"),        
        "response.completed" : ("Done", "complete"),
        "response.file_search_call.complted" : ("File search completed", "complete"),
        "response.file_search_call.in_progress" : ("Starting File search", "running"),
        "response.file_search_call.searching" : ("Executing File search", "running"),     
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)
        

asyncio.run(paint_history())


async def run_agent(message):

    with st.chat_message("ai"):
        status_container = st.status("Thinking...", expanded=False)
        text_placeholder = st.empty()
        response = ""
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
        
prompt = st.chat_input("Write a message for your assistant", accept_file=True, file_type=["txt", "pdf"])

if prompt:

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

    if prompt.text:
        with st.chat_message("user"):
            st.write(prompt.text)
        asyncio.run(run_agent(prompt.text))


with st.sidebar:
    reset = st.button("Reset Memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))
