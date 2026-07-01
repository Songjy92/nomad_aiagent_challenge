from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm
from .sub_agents.story_writer.agent import story_writer_agent
from .sub_agents.asset_generator.agent import asset_generator_agent
from .prompt import STORY_BOOK_MAKER_DESCRIPTION, STORY_BOOK_MAKER_PROMPT

MODEL = LiteLlm(model="openai/gpt-4o")

story_book_maker_agent = Agent(
    name="StoryBookMakerAgent",
    model=MODEL,
    description=STORY_BOOK_MAKER_DESCRIPTION,
    instruction=STORY_BOOK_MAKER_PROMPT,
    tools=[
        AgentTool(agent=story_writer_agent),
        AgentTool(agent=asset_generator_agent),
    ],
)

root_agent = story_book_maker_agent