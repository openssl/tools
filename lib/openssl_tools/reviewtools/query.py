# Copyright 2026 The OpenSSL Project Authors. All Rights Reserved.
#
# Licensed under the Apache License 2.0 (the "License").  You may not use
# this file except in compliance with the License.  You can obtain a copy
# in the file LICENSE in the source distribution or at
# https://www.openssl.org/source/license.html
"""A client for the OpenSSL committer and CLA database at api.openssl.org.

The Perl equivalent is the OpenSSL-Query distribution: OpenSSL::Query with
its PersonREST and ClaREST backends, plus a registration and priority system
for plugging in alternative backends.  Only the REST backend was ever used
here, and the API it speaks has seven endpoints, so this is a plain client.

    GET /0/People                              every known person
    GET /0/Person/<id>                         one person's record
    GET /0/Person/<id>/ValueOfTag/<tag>        e.g. the 'rev' reviewer tag
    GET /0/Person/<id>/IsMemberOf/<group>      e.g. the 'commit' group
    GET /0/Group/<group>/Members               a group's members
    GET /0/HasCLA/<email>                      200 if a CLA is on file
    GET /0/CLAs                                whether CLAs are listable

Status handling follows the Perl: a 5xx is an error worth reporting, while
any other non-200 means "no such thing" and yields an empty result.  That
distinction matters -- a 404 for an unknown reviewer is a normal answer, and
must not be confused with the database being unreachable.

Standard http_proxy / https_proxy / no_proxy variables are honoured, because
urllib's default opener reads them, as LWP's env_proxy did.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any

from .errors import QueryError

DEFAULT_BASE_URL = "https://api.openssl.org"
DEFAULT_TIMEOUT = 30


def encode_id(identity: str | Mapping[str, str]) -> str:
    """Render a person identifier for use in a URL path.

    A plain string is used as-is.  A single-entry mapping is rendered as
    'tag:value', which is how the API disambiguates e.g. a GitHub handle from
    an email address.
    """
    if isinstance(identity, str):
        return identity
    if len(identity) != 1:
        raise ReviewMalformedID("Malformed input ID")
    ((tag, value),) = identity.items()
    return f"{tag}:{value}"


class ReviewMalformedID(QueryError):
    """The caller passed an identifier this API cannot express."""


class Query:
    """Read-only access to the person and CLA databases."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        scheme = urllib.parse.urlsplit(base_url).scheme
        if scheme not in ("http", "https"):
            raise QueryError(f"Unsupported scheme in base URL: {base_url!r}")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._opener = opener or urllib.request.build_opener()
        # find_person_tag and has_cla get asked about the same handful of
        # people repeatedly within one run, and --list asks three questions
        # per person.  Caching keeps that to one request each.
        self._cache: dict[str, tuple[int, str]] = {}

    # -- transport ----------------------------------------------------------

    def _get(self, *path_segments: str) -> tuple[int, str]:
        """GET a path, returning (status, body).  Raises only on 5xx."""
        quoted = "/".join(urllib.parse.quote(segment, safe="") for segment in path_segments)
        url = f"{self.base_url}/{quoted}"

        if url in self._cache:
            return self._cache[url]

        # The scheme is validated in __init__, so this can only ever be
        # http or https -- never file: or anything else unexpected.
        request = urllib.request.Request(  # noqa: S310
            url, headers={"Accept": "application/json"}
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                result = (response.status, response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            # The body is only used for context in the message; failing to
            # read it must not mask the status we came here for.
            try:
                body = error.read().decode("utf-8", errors="replace")
            except OSError:  # pragma: no cover - the body is best-effort
                body = ""
            if error.code >= 500:
                raise QueryError(f"Server error: {error.reason}") from error
            result = (error.code, body)
        except urllib.error.URLError as error:
            raise QueryError(f"Could not reach {self.base_url}: {error.reason}") from error

        self._cache[url] = result
        return result

    def _get_json(self, *path_segments: str) -> Any:
        status, body = self._get(*path_segments)
        if status != 200:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError as error:
            raise QueryError(f"Malformed JSON from {self.base_url}: {error}") from error

    # -- people -------------------------------------------------------------

    def list_people(self) -> list:
        """Every known person, each as a list of their identities."""
        return self._get_json("0", "People") or []

    def find_person(self, identity: str | Mapping[str, str]) -> dict:
        """One person's full record, or an empty dict if not found."""
        return self._get_json("0", "Person", encode_id(identity)) or {}

    def find_person_tag(self, identity: str | Mapping[str, str], tag: str) -> str | None:
        """The value of `tag` for a person, e.g. their 'rev' reviewer name."""
        decoded = self._get_json("0", "Person", encode_id(identity), "ValueOfTag", tag)
        if not decoded:
            return None
        return decoded[0]

    def is_member_of(self, identity: str | Mapping[str, str], group: str) -> bool:
        """Whether a person belongs to `group`, e.g. 'commit'."""
        decoded = self._get_json("0", "Person", encode_id(identity), "IsMemberOf", group)
        if not decoded:
            return False
        return bool(decoded[0])

    def members_of(self, group: str) -> list:
        return self._get_json("0", "Group", group, "Members") or []

    # -- CLAs ---------------------------------------------------------------

    def has_cla(self, identity: str) -> bool:
        """Whether a CLA is on file for an email address.

        Accepts a bare address or one wrapped in angle brackets, as it may
        arrive from a git author line.
        """
        address = extract_email(identity)
        status, _ = self._get("0", "HasCLA", address)
        return status == 200

    def list_clas(self) -> bool:
        status, _ = self._get("0", "CLAs")
        return status == 200


def extract_email(identity: str) -> str:
    """Pull an email address out of `identity`, validating its shape."""
    start = identity.find("<")
    end = identity.find(">", start + 1)
    if start != -1 and end != -1:
        inner = identity[start + 1 : end]
        if "@" in inner and " " not in inner:
            return inner
    if "@" not in identity or " " in identity or identity.startswith("@"):
        raise ReviewMalformedID(f"Malformed input ID: {identity!r}")
    return identity
