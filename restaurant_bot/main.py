import sys
import asyncio
import uuid

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import aiosqlite
import dotenv

dotenv.load_dotenv()
from openai import OpenAI
import streamlit as st
from agents import Runner, SQLiteSession, InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from models import UserAccountContext
from my_agents.triage_agent import triage_agent

client = OpenAI()

DB_PATH = "customer-support-memory.db"


@st.cache_resource
def get_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def run_async(coro):
    return get_event_loop().run_until_complete(coro)


async def load_user_name(session_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT,
                key TEXT,
                value TEXT NOT NULL,
                PRIMARY KEY (session_id, key)
            )
            """
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT value FROM user_sessions WHERE session_id = ? AND key = ?",
            (session_id, "user_name"),
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def save_user_name(session_id: str, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT,
                key TEXT,
                value TEXT NOT NULL,
                PRIMARY KEY (session_id, key)
            )
            """
        )
        await db.execute(
            "INSERT OR REPLACE INTO user_sessions (session_id, key, value) VALUES (?, ?, ?)",
            (session_id, "user_name", name),
        )
        await db.commit()


# ── 사용자 고유 세션 ID (브라우저 탭마다 독립적으로 생성) ──────────────────────
if "user_session_id" not in st.session_state:
    st.session_state["user_session_id"] = str(uuid.uuid4())

user_session_id = st.session_state["user_session_id"]

if "user_name" not in st.session_state:
    st.session_state["user_name"] = run_async(load_user_name(user_session_id))

if st.session_state["user_name"] is None:
    st.title("어서오세요, 노마드 돼지집입니다!🐖")
    name_input = st.text_input("이름을 입력해주시면 대화를 시작하겠습니다:")
    if name_input.strip():
        st.session_state["user_name"] = name_input.strip()
        run_async(save_user_name(user_session_id, name_input.strip()))
        st.rerun()
    st.stop()


user_account_ctx = UserAccountContext(
    customer_id=1,
    name=st.session_state["user_name"],
    tier="basic",
)


if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        user_session_id,          # 사용자별 고유 세션 ID로 채팅 히스토리 분리
        "customer-support-memory.db",
    )
session = st.session_state["session"]

if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent


async def paint_history():
    messages = await session.get_items()
    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"])


run_async(paint_history())


async def run_agent(message):

    with st.chat_message("ai"):
        st.caption(f"🤖 **{st.session_state['agent'].name}**")
        text_placeholder = st.empty()
        response = ""

        st.session_state["text_placeholder"] = text_placeholder

        try:

            stream = Runner.run_streamed(
                st.session_state["agent"],
                message,
                session=session,
                context=user_account_ctx,
            )

            async for event in stream.stream_events():
                if event.type == "raw_response_event":

                    if event.data.type == "response.output_text.delta":
                        response += event.data.delta
                        text_placeholder.write(response)

                elif event.type == "agent_updated_stream_event":

                    if st.session_state["agent"].name != event.new_agent.name:
                        
                        st.write(f"🤖 {st.session_state["agent"].name} -> {event.new_agent.name}")

                        st.session_state["agent"] = event.new_agent
                        st.caption(f"🤖 **{st.session_state['agent'].name}**")

                        text_placeholder = st.empty()

                        st.session_state["text_placeholder"] = text_placeholder
                        response = ""

        except InputGuardrailTripwireTriggered:
            st.warning("⚠️ 죄송합니다. 해당 내용은 저희 서비스 범위를 벗어나는 요청이에요. 메뉴, 주문, 예약, 불만 접수 관련 질문을 도와드릴게요! 😊")

        except OutputGuardrailTripwireTriggered:
            st.warning("⚠️ 죄송합니다. 해당 답변은 제공해 드리기 어렵습니다. 다른 방식으로 질문해 주시면 최선을 다해 도와드릴게요! 🙏")
            st.session_state["text_placeholder"].empty()


message = st.chat_input(
    "무엇을 도와드릴까요? 메뉴 안내, 주문, 예약, 불만 접수 모두 가능합니다 🐖",
)

if message:

    if message:
        with st.chat_message("human"):
            st.write(message)
        run_async(run_agent(message))


async def reset_all():
    await session.clear_session()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_sessions WHERE session_id = ?",
            (user_session_id,),
        )
        await db.commit()


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        run_async(reset_all())
        st.session_state["user_name"] = None
        st.session_state["agent"] = triage_agent
        st.session_state.pop("orders_store", None)
        st.session_state.pop("reservations_store", None)
        st.session_state.pop("complaints_store", None)
        st.rerun()
    st.write(run_async(session.get_items()))