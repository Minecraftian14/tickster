import os
from typing import Union, Literal

from dotenv import load_dotenv

from openrouter import OpenRouter, operations

load_dotenv()

OPENROUTER_CONFIG = {
    'default': os.getenv("gai_providers.openrouter.free_token"),
    'free': os.getenv("gai_providers.openrouter.free_token"),
    'budget': os.getenv("gai_providers.openrouter.budget_token"),
    'infinite': os.getenv("gai_providers.openrouter.infinite_token"),
}


def _or_ctx():
    return OpenRouter(
        x_open_router_title="gai",
        x_open_router_categories="cli-agent",
        api_key=OPENROUTER_CONFIG['default'],
    )


def find_model(
        category: Union[operations.GetModelsCategory, Literal['programming', 'finance', 'academia', 'legal']] = None,
        sort: Union[operations.GetModelsSort, Literal['pricing-low-to-high', 'context-high-to-low', 'latency-low-to-high', 'throughput-high-to-low']] = None,
        budget: Union[str, Literal['free', 'budget', 'infinite']] = None,
        name: str = None,
):
    match budget:
        case 'free':
            budget = 0
        case 'budget':
            budget = 5
        case 'infinite':
            budget = 1000000000
    with _or_ctx() as open_router:
        model_list = open_router.models.list(
            category=category,
            output_modalities="text",
            input_modalities="text",
            sort=sort,
            max_price=budget,
            # offset=None,
            # limit=None,
            q=name,
        )
        if model_list is not None: model_list = model_list.data
        if model_list is None or len(model_list) == 0:
            raise ValueError("No model found")
        return model_list[0].id
