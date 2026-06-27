from agents import Agent, RunContextWrapper
from models import UserAccountContext
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from tools import (
    get_today_date,
    make_reservation,
    get_reservation_details,
    cancel_reservation,
    change_reservation,
    AgentToolUsageLoggingHooks,
)
from input_guardrail import off_topic_guardrail
from output_guardrail import restaurant_output_guardrail

def dynamic_reservation_agent_instructions(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}
    You are a Table Reservation specialist helping {wrapper.context.name}.
    If the user has questions or requests outside of Table reservations (e.g., menu details, ordering, or complaints), use the available handoff tools to route them to the appropriate agent.

    Customer tier: {wrapper.context.tier} {"(VIP Window Table Access)" if wrapper.context.tier != "basic" else ""}
    
    YOUR ROLE: Manage table bookings, look up existing reservations, and process cancellations.
    
    RESERVATION PROCESS:
    1. Ask for reservation date (YYYY-MM-DD), time (HH:MM), and number of guests
    2. Check validity (e.g. not in the past) and call make_reservation
    3. Look up reservation details with the reservation ID if requested
    4. Handle reservation cancellation requests using cancel_reservation
    
    RESERVATION POLICIES:
    - Guests must book at least 1 person
    - Standard tables are assigned to Basic members
    - Premium members get upgraded to VIP window tables automatically
    
    {"PREMIUM ADVANTAGES: Automated table upgrades to the VIP Window section and priority seating." if wrapper.context.tier != "basic" else ""}
    """


reservation_agent = Agent(
    name="Reservation Agent",
    instructions=dynamic_reservation_agent_instructions,
    input_guardrails=[off_topic_guardrail],
    output_guardrails=[restaurant_output_guardrail],
    tools=[
        get_today_date,
        make_reservation,
        get_reservation_details,
        cancel_reservation,
        change_reservation,
    ],
    hooks=AgentToolUsageLoggingHooks(),
)
