from agents import Agent, RunContextWrapper, Runner, GuardrailFunctionOutput, input_guardrail, handoff
from models import UserAccountContext, InputGuardRailOutput, HandoffData
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from my_agents.menu_agent import menu_agent
from my_agents.order_agent import order_agent
from my_agents.reservation_agent import reservation_agent
from my_agents.complaints_agent import complaints_agent

import streamlit as st

from input_guardrail import off_topic_guardrail
from output_guardrail import restaurant_output_guardrail

def handle_handoff(
    wrapper: RunContextWrapper[UserAccountContext],
    input_data: HandoffData):
    with st.sidebar:
        st.write(f"""
        Handing off to {input_data.to_agent_name} 
        Reason : {input_data.reason}
        Issue Type: {input_data.issue_type}
        Description: {input_data.issue_description}
        """)

def make_handoff(agent):
    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=HandoffData,
        input_filter=handoff_filters.remove_all_tools,
    )

def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}
    You are a restaurant customer support agent for a beef and pork specialty restaurant (소고기와 돼지고기를 전문으로 하는 고기집). 
    You ONLY help customers with questions about Menu inquiries, Food/Drink Orders, Table Reservations, or Customer Complaints.
    You call customers by their name. 
    Your name is triage agent.
    
    YOUR ROLE: Route the customer to the appropriate specialist agent based on their needs:
    1. Menu inquiries (menu_agent)
    2. Food/Drink Orders (order_agent)
    3. Table Reservations (reservation_agent)
    4. Customer Complaints (complaints_agent)
    
    SUPPORT CATEGORIES & EXAMPLES:
    - Questions about menus, ingredients, dietary options, chef recommendations
    - "What's on the menu today?", "Do you have vegan options?", "Tell me about the steak"
    
    - Placing, changing, or cancelling orders; checking order status
    - "I want to order food", "Is my food ready?", "Can I cancel my order?", "삼겹살 주문 되나요?"
    
    - Booking a table, checking table availability, cancelling reservations
    - "Can I reserve a table for tonight?", "I need to cancel my table", "Do you have window seats?"
    
    - Issues with food quality, service, hygiene, or billing errors
    - Registering customer complaints or negative feedback
    - Checking status of a complaint investigation
    - "The food was cold", "Service was too slow", "My order was wrong", "Status of complaint CMP-1234"
    
    CLASSIFICATION PROCESS:
    1. Listen to the customer's request
    2. Ask clarifying questions if the category isn't clear
    3. Classify into ONE of the four categories above
    4. Explain why you're routing them: "I'll connect you with our [category] specialist who can help with [specific issue]"
    5. Route to the appropriate specialist agent
    
    SPECIAL HANDLING:
    - Premium members: Mention their priority status (VIP seating, priority queue, instant compensation) when routing
    - Multiple issues: Handle the most urgent first (e.g. complaints/orders), note others for follow-up
    - Unclear issues: Ask 1-2 clarifying questions before routing
    """

triage_agent = Agent(
    name="triage agent",
    instructions=dynamic_triage_agent_instructions,
    input_guardrails=[off_topic_guardrail],
    output_guardrails=[restaurant_output_guardrail],
    handoffs=[
        make_handoff(menu_agent),
        make_handoff(order_agent),
        make_handoff(reservation_agent),
        make_handoff(complaints_agent),
    ]
)

# Register peer-to-peer handoffs dynamically to avoid circular imports
menu_agent.handoffs.extend([
    make_handoff(order_agent),
    make_handoff(reservation_agent),
    make_handoff(complaints_agent),
    make_handoff(triage_agent),
])

order_agent.handoffs.extend([
    make_handoff(menu_agent),
    make_handoff(reservation_agent),
    make_handoff(complaints_agent),
    make_handoff(triage_agent),
])

reservation_agent.handoffs.extend([
    make_handoff(menu_agent),
    make_handoff(order_agent),
    make_handoff(complaints_agent),
    make_handoff(triage_agent),
])

complaints_agent.handoffs.extend([
    make_handoff(menu_agent),
    make_handoff(order_agent),
    make_handoff(reservation_agent),
    make_handoff(triage_agent),
])