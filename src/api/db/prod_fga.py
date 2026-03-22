"""Production-safe OpenFGA bootstrap.

Idempotent: safe to run on every deploy / restart.

Behavior:
  1. If FGA_STORE_ID is set and the store exists → reuse it.
  2. Otherwise → create a new store and persist the ID.
  3. If the store already has the latest model → skip.
  4. If the model is missing or outdated → write a new model version.

Existing tuples are never touched — OpenFGA keeps all model versions and
tuples survive model upgrades.

Run via:  make fga-prod
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv, set_key
from openfga_sdk.client import ClientConfiguration, OpenFgaClient
from openfga_sdk.credentials import CredentialConfiguration, Credentials
from openfga_sdk.models.create_store_request import CreateStoreRequest

from src.api.db.seed_fga import CASE_AUTH_MODEL

_ENV_PATH = Path(__file__).resolve().parents[3] / '.env'

# Stable hash of the model dict so we can detect changes without
# comparing the full structure on every boot.
_MODEL_HASH = hash(json.dumps(CASE_AUTH_MODEL, sort_keys=True))


def _log(msg: str) -> None:
    print(f'[fga-prod] {msg}')


async def _store_exists(client: OpenFgaClient, store_id: str) -> bool:
    """Check whether a store ID is still valid."""
    try:
        store = await client.get_store()
        return store is not None and store.id == store_id
    except Exception:
        return False


async def _get_latest_model(client: OpenFgaClient) -> dict | None:
    """Return the latest authorization model, or None if the store is empty."""
    try:
        resp = await client.read_latest_authorization_model()
        if resp and resp.authorization_model:
            return resp.authorization_model
    except Exception:
        pass
    return None


def _models_match(remote_model: object | None, local_model: dict) -> bool:
    """Compare remote model type_definitions against local model.

    We compare the sorted JSON of type_definitions since that's the
    meaningful part (schema_version rarely changes independently).
    """
    if remote_model is None:
        return False
    try:
        remote_types = remote_model.type_definitions
        local_types = local_model.get('type_definitions', [])
        # Convert remote SDK objects to dicts for comparison
        remote_json = json.dumps(
            [t.to_dict() if hasattr(t, 'to_dict') else t for t in remote_types],
            sort_keys=True,
        )
        local_json = json.dumps(local_types, sort_keys=True)
        return remote_json == local_json
    except Exception:
        return False


async def bootstrap() -> None:
    """Idempotent FGA setup: create store if needed, write model if changed."""
    load_dotenv(_ENV_PATH)

    api_url = os.environ.get('FGA_API_URL', 'http://localhost:8080')
    store_id = os.environ.get('FGA_STORE_ID', '')
    preshared_key = os.environ.get('FGA_PRESHARED_KEY', '')

    # ── 1. Resolve or create store ──────────────────────────────────────
    credentials = None
    if preshared_key:
        credentials = Credentials(
            method='api_token',
            configuration=CredentialConfiguration(api_token=preshared_key),
        )
    config = ClientConfiguration(api_url=api_url, credentials=credentials)
    if store_id:
        config.store_id = store_id

    async with OpenFgaClient(config) as client:
        # Try to connect to existing store
        if store_id and await _store_exists(client, store_id):
            _log(f'Using existing store: {store_id}')
        else:
            if store_id:
                _log(f'Store {store_id} not found — creating new store')
            else:
                _log('No FGA_STORE_ID configured — creating new store')

            store = await client.create_store(CreateStoreRequest(name='kanAPI'))
            store_id = store.id
            client.set_store_id(store_id)

            _ENV_PATH.touch(exist_ok=True)
            set_key(str(_ENV_PATH), 'FGA_API_URL', api_url)
            set_key(str(_ENV_PATH), 'FGA_STORE_ID', store_id)
            _log(f'Store created: {store_id}')

        # ── 2. Check if model needs writing ─────────────────────────────
        client.set_store_id(store_id)
        existing_model = await _get_latest_model(client)

        if _models_match(existing_model, CASE_AUTH_MODEL):
            model_id = existing_model.id
            _log(f'Model up to date: {model_id}')
        else:
            if existing_model is None:
                _log('No model found — writing initial model')
            else:
                _log('Model changed — writing new version (old version preserved)')

            resp = await client.write_authorization_model(CASE_AUTH_MODEL)
            model_id = resp.authorization_model_id
            _log(f'Model written: {model_id}')

        # ── 3. Persist model ID ─────────────────────────────────────────
        _ENV_PATH.touch(exist_ok=True)
        set_key(str(_ENV_PATH), 'FGA_MODEL_ID', model_id)
        _log(f'FGA_MODEL_ID → {model_id}')

    _log('Done.')


if __name__ == '__main__':
    asyncio.run(bootstrap())
