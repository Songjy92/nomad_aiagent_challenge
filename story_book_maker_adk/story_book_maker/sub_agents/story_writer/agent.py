from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from .prompt import STORY_WRITER_DESCRIPTION, STORY_WRITER_PROMPT
from pydantic import BaseModel, Field
from typing import List


class PageOutput(BaseModel):
    id: int = Field(description="Page number")
    story_text: str = Field(description="Story text shown on this page")
    visual_description: str = Field(
        description="Detailed description of the illustration for this page"
    )
    embedded_text: str = Field(
        description="Optional text overlay on the illustration (e.g., sound effect). Empty string if not needed."
    )
    embedded_text_location: str = Field(
        description="Position of the text overlay on the image (e.g., 'top center', 'bottom left'). Empty string if no embedded text."
    )


class StoryBookOutput(BaseModel):
    title: str = Field(description="The title of the storybook")
    theme: str = Field(description="The theme or moral of the story")
    target_age: str = Field(description="Target age group for the readers (e.g., '3–5 years')")
    total_pages: int = Field(description="Total number of pages in the storybook")
    pages: List[PageOutput] = Field(
        description="List of pages in the storybook"
    )


MODEL = LiteLlm(model="openai/gpt-4o")

story_writer_agent = Agent(
    name="StoryWriterAgent",
    description=STORY_WRITER_DESCRIPTION,
    instruction=STORY_WRITER_PROMPT,
    model=MODEL,
    output_schema=StoryBookOutput,
    output_key="story_writer_output",
)