import os
from dotenv import load_dotenv
load_dotenv()

OPENROUTER_CONFIG = {
    'default': os.getenv("gai_providers.openrouter.free_token"),
    'free': os.getenv("gai_providers.openrouter.free_token"),
    'budget': os.getenv("gai_providers.openrouter.budget_token"),
    'infinite': os.getenv("gai_providers.openrouter.infinite_token"),
}
