import dotenv
dotenv.load_dotenv()
import streamlit as st
from agents import Agent, Runner, SQLiteSession, WebSearchTool
import asyncio

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
        """,
        tools=[WebSearchTool()]
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
        if "type" in message and message["type"] == "web_search_call":
            with st.chat_message("ai"):
                st.write("Searching the web...")


def update_status(status_container, event):
    status_messages={
        "response.web_search_call.complted" : ("Search completed", "complete"),
        "response.web_search_call.in_progress" : ("Starting Web search", "running"),
        "response.web_search_call.searching" : ("Executing web search", "running"),        
        "response.completed" : ("Done", "complete"),
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
        
prompt = st.chat_input("Write a message for your assistant")

if prompt:
    with st.chat_message("user"):
        st.write(prompt)
    asyncio.run(run_agent(prompt))


with st.sidebar:
    reset = st.button("Reset Memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))
