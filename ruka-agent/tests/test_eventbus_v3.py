# -*- coding: utf-8 -*-
"""Unit tests for EventBus V3 (Milestone B.1)."""
from __future__ import annotations

import time
import pytest

from src.gateway.events import EventBus, Event, OrganNamespace, ChannelBuffer


class TestChannelBuffer:
    def test_drop_oldest_policy(self) -> None:
        buf = ChannelBuffer(capacity=3)
        assert len(buf) == 0

        e1 = Event("e1", "src1")
        e2 = Event("e2", "src2")
        e3 = Event("e3", "src3")
        e4 = Event("e4", "src4")

        buf.push(e1)
        buf.push(e2)
        buf.push(e3)
        assert len(buf) == 3
        assert buf.dropped_count == 0

        # Push e4 must drop e1
        buf.push(e4)
        assert len(buf) == 3
        assert buf.dropped_count == 1

        # Pop should yield e2, e3, e4
        assert buf.pop() == e2
        assert buf.pop() == e3
        assert buf.pop() == e4
        assert buf.pop() is None


class TestEventBusV3:
    def test_namespace_automatic_extraction(self) -> None:
        e = Event(event_type="heart.pulse", source="supervisor")
        assert e.namespace == OrganNamespace.HEART.value

        e_custom = Event(event_type="custom_type", source="src", namespace="ear")
        assert e_custom.namespace == OrganNamespace.EAR.value

    def test_single_writer_discipline(self) -> None:
        bus = EventBus()
        # Claim writer for presence
        assert bus.claim_writer("presence", "presence_engine_1")
        # Second claim from different writer fails
        assert not bus.claim_writer("presence", "presence_engine_2")

        # Publish from authorized writer succeeds
        e1 = Event(event_type="presence.state", source="presence_engine_1", namespace="presence")
        assert bus.publish(e1, writer_id="presence_engine_1")

        # Publish from unauthorized writer rejected
        e2 = Event(event_type="presence.state", source="imposter", namespace="presence")
        assert not bus.publish(e2, writer_id="imposter")

        # Release writer allows new claim
        assert bus.release_writer("presence", "presence_engine_1")
        assert bus.claim_writer("presence", "presence_engine_2")

    def test_pub_sub_and_wildcards(self) -> None:
        bus = EventBus()
        received = []

        sub_id = bus.subscribe("heart.*", lambda e: received.append(e.event_type))
        bus.publish(Event(event_type="heart.pulse", source="sup"))
        bus.publish(Event(event_type="heart.beat", source="sup"))
        bus.publish(Event(event_type="memory.saved", source="palace"))

        assert received == ["heart.pulse", "heart.beat"]
        assert bus.unsubscribe(sub_id)

    def test_channel_queue_retrieval(self) -> None:
        bus = EventBus()
        e = Event(event_type="ear.vad_onset", source="blood_hearing", namespace="ear")
        bus.publish(e)

        q = bus.channel_queue("ear")
        assert len(q) == 1
        popped = q.pop()
        assert popped is not None
        assert popped.event_type == "ear.vad_onset"

    def test_history_audit(self) -> None:
        bus = EventBus()
        bus.publish(Event(event_type="hands.move", source="shadow_hands", namespace="hands"))
        bus.publish(Event(event_type="voice.stream", source="eternal_voice", namespace="voice"))

        h_hands = bus.history(namespace="hands")
        assert len(h_hands) == 1
        assert h_hands[0].event_type == "hands.move"

        h_all = bus.history()
        assert len(h_all) == 2
