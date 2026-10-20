"""Explicit local bridge to the Momentum integrated engine.

A separate versioned route prevents legacy Best inputs from being reinterpreted.
No GitHub worker or operational schedule is used by this bridge.
"""
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse


def integrated_router(base_url, authorize):
    parsed = urlparse(base_url)
    if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'', '/'}:
        raise ValueError('Integrated engine URL must be a loopback HTTP origin')
    router = APIRouter(prefix='/v2/momentum-integrated', dependencies=[Depends(authorize)])

    async def forward(method, suffix='', body=None):
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False) as client:
                response = await client.request(method, base_url.rstrip('/') + '/api/integrated/runs' + suffix, json=body)
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return JSONResponse(status_code=503, content={'error': 'Local integrated engine unavailable'})
        if response.is_redirect:
            return JSONResponse(status_code=502, content={'error': 'Unexpected engine redirect'})
        def rewrite(row):
            if isinstance(row, dict) and row.get('resultUrl', '').startswith('/api/integrated/runs/'):
                row['resultUrl'] = '/v2/momentum-integrated/runs/' + row['resultUrl'].split('/api/integrated/runs/', 1)[1]
        rewrite(data)
        for row in data.get('runs', []) if isinstance(data, dict) else []:
            rewrite(row)
        return JSONResponse(status_code=response.status_code, content=data)

    @router.get('/capabilities')
    async def capabilities():
        return {'projectId': 'momentum', 'inputSchemaVersion': 'momentum-integrated/v1',
                'resultSchemaVersion': 'integrated-factor/v1', 'execution': 'local',
                'runsUrl': '/v2/momentum-integrated/runs', 'legacyBestInputsAccepted': False}

    @router.get('/runs')
    async def runs():
        return await forward('GET')

    @router.post('/runs')
    async def create(request: Request):
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse(status_code=400, content={'error': 'Invalid JSON'})
        if not isinstance(body, dict) or set(body) - {'settings', 'comparisonFactors', 'commonUniverse', 'hypothesis', 'experimentDefinition'}:
            return JSONResponse(status_code=400, content={'error': 'Expected integrated input contract'})
        return await forward('POST', body=body)

    @router.get('/runs/{run_id}')
    async def status(run_id: str):
        if len(run_id) != 32 or any(c not in '0123456789abcdef' for c in run_id):
            return JSONResponse(status_code=404, content={'error': 'Unknown run'})
        return await forward('GET', '/' + run_id)

    @router.get('/runs/{run_id}/result')
    async def result(run_id: str):
        if len(run_id) != 32 or any(c not in '0123456789abcdef' for c in run_id):
            return JSONResponse(status_code=404, content={'error': 'Unknown run'})
        return await forward('GET', '/' + run_id + '/result')

    return router
