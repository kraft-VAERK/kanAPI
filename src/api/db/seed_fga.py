"""Bootstrap script to create an OpenFGA store and write the kanAPI authorization model.

Run once after starting the OpenFGA server:
    . venv/bin/activate && python src/api/db/seed_fga.py

The script prints the FGA_STORE_ID and FGA_MODEL_ID env vars to export.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import set_key
from openfga_sdk.client import ClientConfiguration, OpenFgaClient
from openfga_sdk.models.create_store_request import CreateStoreRequest

_ENV_PATH = Path(__file__).resolve().parents[3] / '.env'

# Authorization model: user, company (member/admin), case (creator/assignee/viewer/editor/deleter)
CASE_AUTH_MODEL = {
    'schema_version': '1.1',
    'type_definitions': [
        {'type': 'user'},
        {
            'type': 'company',
            'relations': {
                'member': {'this': {}},
                'admin': {'this': {}},
            },
            'metadata': {
                'relations': {
                    'member': {'directly_related_user_types': [{'type': 'user'}]},
                    'admin': {'directly_related_user_types': [{'type': 'user'}]},
                },
            },
        },
        {
            'type': 'case',
            'relations': {
                'company': {'this': {}},
                'creator': {'this': {}},
                'assignee': {'this': {}},
                'viewer': {
                    'union': {
                        'child': [
                            {'this': {}},
                            {'computedUserset': {'relation': 'editor'}},
                            {'computedUserset': {'relation': 'creator'}},
                            {'computedUserset': {'relation': 'assignee'}},
                            {
                                'tupleToUserset': {
                                    'tupleset': {'relation': 'company'},
                                    'computedUserset': {'relation': 'admin'},
                                },
                            },
                            {
                                'tupleToUserset': {
                                    'tupleset': {'relation': 'company'},
                                    'computedUserset': {'relation': 'member'},
                                },
                            },
                        ],
                    },
                },
                'editor': {
                    'union': {
                        'child': [
                            {'this': {}},
                            {'computedUserset': {'relation': 'assignee'}},
                            {
                                'tupleToUserset': {
                                    'tupleset': {'relation': 'company'},
                                    'computedUserset': {'relation': 'admin'},
                                },
                            },
                        ],
                    },
                },
                'deleter': {
                    'union': {
                        'child': [
                            {'this': {}},
                            {'computedUserset': {'relation': 'creator'}},
                            {
                                'tupleToUserset': {
                                    'tupleset': {'relation': 'company'},
                                    'computedUserset': {'relation': 'admin'},
                                },
                            },
                        ],
                    },
                },
            },
            'metadata': {
                'relations': {
                    'company': {'directly_related_user_types': [{'type': 'company'}]},
                    'creator': {'directly_related_user_types': [{'type': 'user'}]},
                    'assignee': {'directly_related_user_types': [{'type': 'user'}]},
                    'viewer': {
                        'directly_related_user_types': [
                            {'type': 'user'},
                            {'type': 'company', 'relation': 'member'},
                            {'type': 'company', 'relation': 'admin'},
                        ],
                    },
                    'editor': {
                        'directly_related_user_types': [
                            {'type': 'user'},
                            {'type': 'company', 'relation': 'member'},
                            {'type': 'company', 'relation': 'admin'},
                        ],
                    },
                    'deleter': {
                        'directly_related_user_types': [
                            {'type': 'user'},
                            {'type': 'company', 'relation': 'admin'},
                        ],
                    },
                },
            },
        },
    ],
}


async def bootstrap() -> None:
    """Create the OpenFGA store and write the authorization model."""
    api_url = os.environ.get('FGA_API_URL', 'http://localhost:8080')
    config = ClientConfiguration(api_url=api_url)

    async with OpenFgaClient(config) as client:
        # 1. Create store
        store = await client.create_store(CreateStoreRequest(name='kanAPI'))
        store_id = store.id
        print(f'Store created: {store_id}')

        # 2. Write authorization model
        client.set_store_id(store_id)
        model_response = await client.write_authorization_model(CASE_AUTH_MODEL)
        model_id = model_response.authorization_model_id
        print(f'Authorization model written: {model_id}')

        # Write the IDs into .env so the app picks them up automatically
        _ENV_PATH.touch(exist_ok=True)
        set_key(str(_ENV_PATH), 'FGA_API_URL', api_url)
        set_key(str(_ENV_PATH), 'FGA_STORE_ID', store_id)
        set_key(str(_ENV_PATH), 'FGA_MODEL_ID', model_id)
        print(f'Written to {_ENV_PATH}')

        print()
        print('Or export manually:')
        print(f'  export FGA_API_URL={api_url}')
        print(f'  export FGA_STORE_ID={store_id}')
        print(f'  export FGA_MODEL_ID={model_id}')


if __name__ == '__main__':
    asyncio.run(bootstrap())
