# -*- coding: utf-8 -*-

import io

from nose.tools import assert_equal, assert_in, assert_not_in, \
    assert_true, assert_false

from submitter.asset import Asset, AssetSet
from submitter.envelope import Envelope, EnvelopeSet

class TestEnvelope():

    def test_construct(self):
        data = io.StringIO('''{
            "title": "aaa",
            "body": "<p>This is an envelope</p>"
        }''')
        e = Envelope('https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Fpage.json', data)

        assert_equal(e.encoded_content_id(), 'https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Fpage')
        assert_equal(e.content_id(), 'https://github.com/org/repo/page')
        assert_equal(e.document, {
            'title': 'aaa',
            'body': '<p>This is an envelope</p>'
        })

    def test_apply_offsets(self):
        a0 = Asset('local/one.jpg', io.BytesIO())
        a1 = Asset('local/two.gif', io.BytesIO())
        a2 = Asset('local/three.png', io.BytesIO())
        asset_set = AssetSet()
        asset_set.append(a0)
        asset_set.append(a1)
        asset_set.append(a2)

        asset_set.accept_urls({
            'local/one.jpg': 'https://assets.horse/one-111.jpg',
            'local/two.gif': 'https://assets.horse/two-222.gif',
            'local/three.png': 'https://assets.horse/three-333.png'
        })

        data = io.StringIO('''{
            "title": "envelope with asset references",
            "body": "<p>Hey everyone here X are X some assets X</p>",
            "asset_offsets": {
                "local/one.jpg": [21, 41],
                "local/three.png": [27]
            }
        }''')
        e = Envelope('https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Fpage.json', data)

        e.apply_asset_offsets(asset_set)

        assert_not_in('asset_offsets', e.document)
        assert_equal(e.document['body'], '<p>Hey everyone here ' \
            'https://assets.horse/one-111.jpg are ' \
            'https://assets.horse/three-333.png some ' \
            'assets https://assets.horse/one-111.jpg</p>')

    def test_fingerprint(self):
        a = Asset('local/one.jpg', io.BytesIO())
        asset_set = AssetSet()
        asset_set.append(a)
        asset_set.accept_urls({
            'local/one.jpg': 'https://assets.horse/one-111.jpg'
        })

        data = io.StringIO('''{
            "title": "another asset envelope",
            "body": "<p>The asset URL is X</p>",
            "asset_offsets": { "local/one.jpg": [20] }
        }''')
        e = Envelope('https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Fpage.json', data)

        e.apply_asset_offsets(asset_set)

        # echo -n '{"body":"<p>The asset URL is https://assets.horse/one-111.jpg</p>","title":"another asset envelope"}' | shasum -a 256
        assert_equal(e.fingerprint(), 'a0e0c4043590530b1d911432c04fc4d238c614b60eeaa9b68632d0791ba96aec')

    def test_accept_presence(self):
        data = io.StringIO('{"title": "a", "body":"a"}')
        e = Envelope('https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Fpage.json', data)
        assert_true(e.needs_upload())

        e.accept_presence({ 'https://github.com/org/repo/page': False })
        assert_true(e.needs_upload())

        e.accept_presence({ 'https://github.com/org/repo/page': True })
        assert_false(e.needs_upload())


class TestEnvelopeSet():

    def setup(self):
        self.envelope_set = EnvelopeSet()
        self.e0 = Envelope('https%3A%2F%2Fg.com%2Fa%2Fb%2Fone.json', io.StringIO(
            '{"title": "one", "body": "one"}'
        ))
        self.e1 = Envelope('https%3A%2F%2Fg.com%2Fa%2Fb%2Ftwo.json', io.StringIO(
            '{"title": "two", "body": "two"}'
        ))

        self.envelope_set.append(self.e0)
        self.envelope_set.append(self.e1)

    def test_append(self):
        self.envelope_set = EnvelopeSet()

        self.envelope_set.append(self.e0)
        assert_equal(len(self.envelope_set), 1)

        self.envelope_set.append(self.e1)
        assert_equal(len(self.envelope_set), 2)

    def test_fingerprint_query(self):
        assert_equal(self.envelope_set.fingerprint_query(), {
            'https://g.com/a/b/one': '842d36ad29589a39fc4be06157c5c204a360f98981fc905c0b2a114662172bd8',
            'https://g.com/a/b/two': 'b00e03c4da0d9ce6b65ae32a384c4cbb893bc13e2c05817b411128f8e118fe0b'
        })

    def test_accept_presence(self):
        self.envelope_set.accept_presence({
            'https://g.com/a/b/one': True,
            'https://g.com/a/b/two': False
        })

        assert_false(self.e0.needs_upload())
        assert_true(self.e1.needs_upload())

    def test_to_upload(self):
        self.envelope_set.accept_presence({
            'https://g.com/a/b/one': True,
            'https://g.com/a/b/two': False
        })

        to_upload = [e for e in self.envelope_set.to_upload()]
        assert_not_in(self.e0, to_upload)
        assert_in(self.e1, to_upload)

    def test_to_keep(self):
        self.envelope_set.accept_presence({
            'https://g.com/a/b/one': True,
            'https://g.com/a/b/two': False
        })

        to_keep = [e for e in self.envelope_set.to_keep()]
        assert_in(self.e0, to_keep)
        assert_not_in(self.e1, to_keep)
