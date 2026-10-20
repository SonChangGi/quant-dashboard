import pytest
from fastapi.testclient import TestClient

from quant_control_api.app import create_app
from quant_control_api.settings import Settings


def test_integrated_contract_is_explicit_and_legacy_inputs_rejected():
    with TestClient(create_app(settings=Settings(environment='test', integrated_engine_url='http://127.0.0.1:8766'))) as client:
        capability = client.get('/v2/momentum-integrated/capabilities')
        assert capability.status_code == 200
        assert capability.json()['legacyBestInputsAccepted'] is False
        response = client.post('/v2/momentum-integrated/runs', json={'inputs': {'bestFactor': 'old'}})
        assert response.status_code == 400


@pytest.mark.parametrize('url', ['https://example.com', 'http://127.0.0.1.evil.com', 'http://user:pass@localhost', 'http://localhost/private'])
def test_bridge_cannot_target_external_or_credential_url(url):
    with pytest.raises(ValueError):
        create_app(settings=Settings(environment='test', integrated_engine_url=url))


def test_bridge_cannot_be_enabled_in_production():
    with pytest.raises(ValueError):
        Settings(environment='production', integrated_engine_url='http://localhost:8766').validate()


def test_default_control_api_has_no_integration_execution_route():
    with TestClient(create_app(settings=Settings(environment='test'))) as client:
        assert client.get('/v2/momentum-integrated/capabilities').status_code == 404


def test_local_integration_retires_best_execution_without_reinterpreting_inputs():
    with TestClient(create_app(settings=Settings(environment='test', integrated_engine_url='http://127.0.0.1:8766'))) as client:
        assert client.get('/v1/projects/best-factor/capabilities').status_code == 410
        response = client.post('/v1/projects/best-factor/runs', headers={'Idempotency-Key': 'retired-best'}, json={'inputSchemaVersion': 'best-factor/v1', 'inputs': {}})
        assert response.status_code == 410
