"""Public-key API smoke checks; historical frozen-key scores are not tested here."""
from __future__ import annotations

from io import BytesIO
import os
import subprocess

import pytest
from fastapi.testclient import TestClient

from course_release.online.app import app, _blocks

client = TestClient(app)


def test_info_and_mode_layout():
    r = client.get('/api/v1/info')
    assert r.status_code == 200
    assert r.json()['reference_assisted'] is True
    assert r.json()['sample_available'] is True
    assert _blocks('12345678', 'c2-long-id') == [0x12,0x34,0x56,0x78]*3
    assert len(_blocks('D42DEE6FA235F3C07531FD862283452DCB56FF6A8F621E41', 'c3-192')) == 12


def test_reject_bad_message_and_key():
    assert client.post('/api/v1/embed', data={'mode':'c3-16','message':'ZZZZ','key':'valid-test-key','source':'sample'}).status_code == 422
    assert client.post('/api/v1/embed', data={'mode':'c2-8','message':'A7','key':'a','source':'sample'}).status_code == 422


@pytest.mark.parametrize('mode,message', [('c2-8', 'A7'), ('c3-16', 'A7C3')])
def test_embed_and_detect_real_sample(mode, message):
    key='course-demo-public-v1'
    r = client.post('/api/v1/embed', data={'mode':mode,'message':message,'key':key,'source':'sample'})
    assert r.status_code == 200, r.text[:300]
    assert r.headers['content-type'].startswith('audio/wav')
    assert len(r.content)>500_000
    d = client.post('/api/v1/detect', data={'mode':mode,'key':key,'source':'sample'}, files={
        'received':('marked.wav', BytesIO(r.content), 'audio/wav')
    })
    assert d.status_code==200, d.text[:300]
    report=d.json()
    assert report['reference_assisted'] is True
    assert report['recovered_payload'] == message
    assert report['status']=='IDENTIFIED'
    assert report['accepted_blocks']==1


def test_real_mp3_processing_roundtrip():
    if subprocess.run(['which','ffmpeg'],capture_output=True).returncode:
        pytest.skip('FFmpeg not present')
    key='course-demo-public-v1'
    r=client.post('/api/v1/embed', data={'mode':'c3-16','message':'A7C3','key':key,'source':'sample'})
    assert r.status_code==200
    p=client.post('/api/v1/process',data={'channel':'mp3','seconds':'6'},files={
        'audio':('marked.wav', BytesIO(r.content), 'audio/wav')
    })
    assert p.status_code==200, p.text[:200]
    assert p.headers['content-type'].startswith('audio/mpeg')
    d=client.post('/api/v1/detect',data={'mode':'c3-16','key':key,'source':'sample'},files={
        'received':('marked.mp3', BytesIO(p.content), 'audio/mpeg')
    })
    assert d.status_code==200, d.text[:200]
    assert d.json()['recovered_payload']=='A7C3'


def test_reject_oversized_request_without_parsing_file():
    r=client.post('/api/v1/embed',headers={'Content-Length':str(70*1024*1024)},data={})
    assert r.status_code==413
