from openai.types import Moderation
from open_ai.openai_wrapper import openai_moderate

def sanitize_prompt(prompt: str, nsfw_allowed: bool):
    try:
        openai_results = openai_moderate(prompt)

        print(openai_results)

        moderate_general(openai_results)

        # Needs to be performed after general moderation, otherwise sexual_minors will indicate to enable NSFW for the team
        if not nsfw_allowed:
            moderate_nsfw(openai_results)

        return False
    except Exception as e:
        raise Exception(f"Moderation of prompt failed: {e}")

def moderate_nsfw(moderation_result: Moderation):
    categories = moderation_result.categories
    if categories.sexual:
        raise Exception("NSFW is not enabled for your team or not allowed for this persona")

def moderate_general(moderation_result: Moderation):
    categories = moderation_result.categories

    if categories.harassment or categories.harassment_threatening or categories.hate or categories.hate_threatening or categories.self_harm or categories.self_harm_instructions or categories.self_harm_intent or categories.sexual_minors or categories.violence or categories.violence_graphic:
        raise Exception("Prompt contains inappropriate content")