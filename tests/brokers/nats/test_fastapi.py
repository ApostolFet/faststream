import asyncio
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from faststream.nats import JStream, NatsBroker, NatsRouter, PullSub, TestNatsBroker
from faststream.nats.fastapi import NatsRouter as StreamRouter
from tests.brokers.base.fastapi import FastAPILocalTestcase, FastAPITestcase


@pytest.mark.nats
class TestRouter(FastAPITestcase):
    router_class = StreamRouter
    broker_router_class = NatsRouter

    async def test_path(
        self,
        queue: str,
        event: asyncio.Event,
        mock: MagicMock,
    ):
        router = self.router_class()

        @router.subscriber(queue + ".{name}")
        def subscriber(msg: str, name: str):
            mock(msg=msg, name=name)
            event.set()

        async with router.broker:
            await router.broker.start()
            await asyncio.wait(
                (
                    asyncio.create_task(
                        router.broker.publish("hello", f"{queue}.john"),
                    ),
                    asyncio.create_task(event.wait()),
                ),
                timeout=3,
            )

        assert event.is_set()
        mock.assert_called_once_with(msg="hello", name="john")

    async def test_consume_batch(
        self,
        queue: str,
        stream: JStream,
        event: asyncio.Event,
        mock: MagicMock,
    ):
        router = self.router_class()

        @router.subscriber(
            queue,
            stream=stream,
            pull_sub=PullSub(1, batch=True),
        )
        def subscriber(m: List[str]):
            mock(m)
            event.set()

        async with router.broker:
            await router.broker.start()
            await asyncio.wait(
                (
                    asyncio.create_task(router.broker.publish(b"hello", queue)),
                    asyncio.create_task(event.wait()),
                ),
                timeout=3,
            )

        assert event.is_set()
        mock.assert_called_once_with(["hello"])


class TestRouterLocal(FastAPILocalTestcase):
    router_class = StreamRouter
    broker_router_class = NatsRouter

    def patch_broker(self, broker: NatsBroker, **kwargs: Any) -> NatsBroker:
        return TestNatsBroker(broker, **kwargs)

    async def test_consume_batch(
        self,
        queue: str,
        stream: JStream,
        event: asyncio.Event,
        mock: MagicMock,
    ):
        router = self.router_class()

        @router.subscriber(
            queue,
            stream=stream,
            pull_sub=PullSub(1, batch=True),
        )
        def subscriber(m: List[str]):
            mock(m)
            event.set()

        async with self.patch_broker(router.broker) as br:
            await asyncio.wait(
                (
                    asyncio.create_task(br.publish(b"hello", queue)),
                    asyncio.create_task(event.wait()),
                ),
                timeout=3,
            )

        assert event.is_set()
        mock.assert_called_once_with(["hello"])

    async def test_path(self, queue: str):
        router = self.router_class()

        @router.subscriber(queue + ".{name}")
        async def hello(name):
            return name

        async with self.patch_broker(router.broker) as br:
            r = await br.request(
                "hi",
                f"{queue}.john",
                timeout=0.5,
            )
            assert await r.decode() == "john"
