from agents import Agent, RunContextWrapper, Runner, GuardrailFunctionOutput, input_guardrail
from models import UserAccountContext, InputGuardRailOutput

input_guardrail_agent = Agent(
    name="Input Guardrail Agent",
    instructions="""
    You are an input guardrail agent. Your job is to classify if the user's request is off-topic.
    
    A request is ON-TOPIC if it is related to:
    - Restaurant Menu inquiries (dishes, ingredients, prices, allergies, etc.)
    - Food/Drink Orders (placing, checking status, cancelling, etc.)
    - Table Reservations (booking, checking availability, cancellation, etc.)
    - Customer Complaints (issues, registering negative feedback, complaint status, etc.)
    - Small talk / greeting at the beginning of the conversation (e.g. "hello", "hi", "how are you").

    A request is OFF-TOPIC if it is anything else (e.g. general knowledge, writing code, translations, requests about other subjects).

    Set `is_off_topic` to True if the user's request is OFF-TOPIC. Otherwise, set it to False.
    If `is_off_topic` is True, provide a clear reason why in the `reason` field.
    """,
    output_type=InputGuardRailOutput,
)

@input_guardrail(run_in_parallel=False)
async def off_topic_guardrail(
    wrapper: RunContextWrapper[UserAccountContext],
    agent: Agent[UserAccountContext],
    input: str):

    result = await Runner.run(input_guardrail_agent, input, context=wrapper.context)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_off_topic,
    )
