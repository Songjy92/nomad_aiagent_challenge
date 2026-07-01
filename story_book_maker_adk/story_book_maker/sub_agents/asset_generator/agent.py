from google.adk.agents import ParallelAgent
from .prompt import ASSET_GENERATOR_DESCRIPTION
from .image_generator_agent.agent import image_generator_agent

asset_generator_agent = ParallelAgent(
    name="AssetGeneratorAgent",
    sub_agents=[
        image_generator_agent
    ],
    description=ASSET_GENERATOR_DESCRIPTION,
)