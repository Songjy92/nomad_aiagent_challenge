import base64
import logging
from google.genai import types
from openai import OpenAI, BadRequestError
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)
client = OpenAI()


async def generate_images(tool_context: ToolContext):

    prompt_builder_output = tool_context.state.get("prompt_builder_output")
    optimized_prompts = prompt_builder_output.get("optimized_prompts")

    existing_artifacts = await tool_context.list_artifacts()

    generated_images = []
    failed_images = []

    for prompt in optimized_prompts:
        scene_id = prompt.get("scene_id")
        enhanced_prompt = prompt.get("enhanced_prompt")
        filename = f"scene_{scene_id}_image.jpeg"

        if filename in existing_artifacts:
            generated_images.append(
                {
                    "scene_id": scene_id,
                    "prompt": enhanced_prompt[:100],
                    "filename": filename,
                    "status": "cached",
                }
            )
            continue

        try:
            image = client.images.generate(
                model="gpt-image-1",
                prompt=enhanced_prompt,
                n=1,
                quality="low",
                moderation="low",
                output_format="jpeg",
                background="opaque",
                size="1024x1536",
            )

            image_bytes = base64.b64decode(image.data[0].b64_json)

            artifact = types.Part(
                inline_data=types.Blob(
                    mime_type="image/jpeg",
                    data=image_bytes,
                )
            )

            await tool_context.save_artifact(
                filename=filename,
                artifact=artifact,
            )

            generated_images.append(
                {
                    "scene_id": scene_id,
                    "prompt": enhanced_prompt[:100],
                    "filename": filename,
                    "status": "generated",
                }
            )

        except BadRequestError as e:
            error_code = getattr(e, "code", None) or (
                e.body.get("error", {}).get("code") if hasattr(e, "body") and e.body else None
            )
            logger.warning(
                "Page %s image generation blocked by moderation (code=%s). Skipping.",
                scene_id,
                error_code,
            )
            failed_images.append(
                {
                    "scene_id": scene_id,
                    "status": "moderation_blocked",
                    "error_code": error_code,
                }
            )

    return {
        "total_images": len(generated_images),
        "generated_images": generated_images,
        "failed_images": failed_images,
        "status": "complete",
    }